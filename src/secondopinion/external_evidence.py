from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from typing import Any, Protocol

from .claim_extraction import DEFAULT_CLAIM_MODEL, extract_claims
from .external_providers.openalex import OpenAlexClient, OpenAlexError, works_to_external_records
from .external_providers.venue_guidelines import collect_venue_guidelines
from .model_config import DEFAULT_CHEAP_MODEL
from .text import STOPWORDS, clean_text


EXTERNAL_EVIDENCE_VERSION = "external-evidence-v0.1"
DEFAULT_COLLECTOR_MODEL = DEFAULT_CHEAP_MODEL
DEFAULT_EXTERNAL_PROVIDERS = ("venue_guidelines", "openalex")
EXTERNAL_SOURCE_TYPES = ("venue_guideline", "external_reference", "field_consensus")
EXTERNAL_CLAIM_TYPES = {"ablation", "baseline", "experiment", "methodology", "novelty", "theory"}
EXTERNAL_CLAIM_KEYWORDS = (
    "novel",
    "novelty",
    "related work",
    "prior work",
    "baseline",
    "comparison",
    "compare",
    "ablation",
    "experiment",
    "evaluation",
    "benchmark",
    "sota",
    "state of the art",
    "standard",
    "field",
)


class StructuredLLMClient(Protocol):
    def complete_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        ...


def parse_providers(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_EXTERNAL_PROVIDERS
    if isinstance(value, str):
        raw = value.split(",")
    else:
        raw = list(value)
    providers = []
    for item in raw:
        provider = clean_text(item).lower().replace("-", "_")
        if provider:
            providers.append(provider)
    return tuple(providers) or DEFAULT_EXTERNAL_PROVIDERS


def collect_external_evidence_for_claims(
    paper: dict[str, Any],
    claims: list[dict[str, Any]],
    *,
    review: dict[str, Any] | None = None,
    providers: str | list[str] | tuple[str, ...] | None = None,
    llm_client: StructuredLLMClient | None = None,
    model: str = DEFAULT_COLLECTOR_MODEL,
    openalex_client: OpenAlexClient | None = None,
    max_external_claims: int = 5,
    max_queries_per_claim: int = 2,
    max_openalex_results_per_query: int = 5,
    max_evidence_per_claim: int = 3,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    provider_names = parse_providers(providers)
    planned = plan_external_evidence(
        paper,
        claims,
        review=review,
        llm_client=llm_client,
        model=model,
        max_external_claims=max_external_claims,
        max_queries_per_claim=max_queries_per_claim,
    )
    selected = [item for item in planned if item["needs_external_evidence"]][:max_external_claims]
    claim_types = {clean_text(item.get("claim_type")).lower() for item in selected}
    records: list[dict[str, Any]] = []
    provider_counts: Counter[str] = Counter()
    errors: list[str] = []

    if "venue_guidelines" in provider_names and selected:
        guideline_records = collect_venue_guidelines(
            venue=paper.get("venue"),
            year=paper.get("year"),
            claim_types=claim_types,
        )
        for record in guideline_records:
            record["metadata"]["external_evidence_version"] = EXTERNAL_EVIDENCE_VERSION
        records.extend(guideline_records)
        provider_counts["venue_guidelines"] += len(guideline_records)

    if "openalex" in provider_names and selected:
        openalex_client = openalex_client or OpenAlexClient()
        for plan in selected:
            claim_records: list[dict[str, Any]] = []
            for query in plan["queries"][:max_queries_per_claim]:
                try:
                    works = openalex_client.search_works(
                        query,
                        per_page=max_openalex_results_per_query,
                        year_lte=safe_int(paper.get("year")),
                    )
                except OpenAlexError as exc:
                    errors.append(str(exc))
                    continue
                claim_records.extend(
                    works_to_external_records(
                        works,
                        claim_id=plan["claim_id"],
                        query=query,
                        max_items=max_evidence_per_claim,
                    )
                )
            claim_records = grade_and_filter_records(
                claim_records,
                paper=paper,
                claim_plan=plan,
                llm_client=llm_client,
                model=model,
                max_items=max_evidence_per_claim,
            )
            for record in claim_records:
                record["metadata"]["external_evidence_version"] = EXTERNAL_EVIDENCE_VERSION
            records.extend(claim_records)
            provider_counts["openalex"] += len(claim_records)

    deduped = dedupe_records(records)
    manifest = {
        "external_evidence_version": EXTERNAL_EVIDENCE_VERSION,
        "providers": list(provider_names),
        "planned_claim_count": len(planned),
        "external_claim_count": len(selected),
        "record_count": len(deduped),
        "provider_counts": dict(provider_counts),
        "errors": errors[:5],
    }
    if openalex_client is not None:
        manifest["openalex_stats"] = openalex_client.stats_dict()
    return deduped, manifest


def plan_external_evidence(
    paper: dict[str, Any],
    claims: list[dict[str, Any]],
    *,
    review: dict[str, Any] | None = None,
    llm_client: StructuredLLMClient | None = None,
    model: str = DEFAULT_COLLECTOR_MODEL,
    max_external_claims: int = 5,
    max_queries_per_claim: int = 2,
) -> list[dict[str, Any]]:
    fallback = deterministic_plan(
        paper,
        claims,
        review=review,
        max_external_claims=max_external_claims,
        max_queries_per_claim=max_queries_per_claim,
    )
    if llm_client is None or not claims:
        return fallback
    try:
        payload = llm_client.complete_json(
            model=model,
            messages=external_plan_messages(paper, claims, review=review, max_queries_per_claim=max_queries_per_claim),
            schema_name="external_evidence_plan",
            schema=external_plan_schema(),
        )
    except Exception:
        return fallback
    planned = validate_external_plan(payload, claims, paper, review=review, max_queries_per_claim=max_queries_per_claim)
    return planned or fallback


def deterministic_plan(
    paper: dict[str, Any],
    claims: list[dict[str, Any]],
    *,
    review: dict[str, Any] | None = None,
    max_external_claims: int = 5,
    max_queries_per_claim: int = 2,
) -> list[dict[str, Any]]:
    planned = []
    external_count = 0
    for index, claim in enumerate(claims):
        claim_text = clean_text(claim.get("claim_text"))
        claim_type = clean_text(claim.get("claim_type")).lower() or "general"
        needs_external = claim_needs_external(claim_text, claim_type)
        if needs_external and external_count >= max_external_claims:
            needs_external = False
        if needs_external:
            external_count += 1
        planned.append(
            {
                "claim_index": index,
                "claim_id": external_claim_id(review, index, claim_text),
                "claim_text": claim_text,
                "claim_type": claim_type,
                "importance": clean_text(claim.get("importance")),
                "needs_external_evidence": needs_external,
                "reason": deterministic_external_reason(claim_text, claim_type, needs_external),
                "queries": build_queries(paper, claim_text, claim_type, max_queries=max_queries_per_claim),
            }
        )
    return planned


def claim_needs_external(claim_text: str, claim_type: str) -> bool:
    lowered = claim_text.lower()
    return claim_type in EXTERNAL_CLAIM_TYPES or any(keyword in lowered for keyword in EXTERNAL_CLAIM_KEYWORDS)


def deterministic_external_reason(claim_text: str, claim_type: str, needs_external: bool) -> str:
    if needs_external:
        return f"{claim_type or 'general'} review point may depend on venue norms, related work, or benchmark conventions."
    return "Review point can usually be assessed with manuscript evidence first."


def build_queries(paper: dict[str, Any], claim_text: str, claim_type: str, *, max_queries: int) -> list[str]:
    title = clean_text(paper.get("title"))
    abstract = clean_text(paper.get("abstract"))
    title_terms = important_terms(title, limit=6)
    claim_terms = important_terms(claim_text, limit=8)
    abstract_terms = important_terms(abstract, limit=6)
    queries = []
    if claim_terms:
        queries.append(" ".join(claim_terms[:8]))
    if title and claim_terms:
        queries.append(" ".join([title, *claim_terms[:4]]))
    if claim_type in {"baseline", "ablation", "experiment"}:
        queries.append(" ".join([*abstract_terms[:5], "baseline comparison benchmark evaluation"]))
    elif claim_type == "novelty":
        queries.append(" ".join([*title_terms[:5], "related work novelty"]))
    elif claim_type == "theory":
        queries.append(" ".join([*title_terms[:5], "theory proof assumption"]))
    elif claim_terms:
        queries.append(" ".join([*title_terms[:4], *claim_terms[:4]]))
    if not queries and title:
        queries.append(title)
    return dedupe_strings(queries)[:max_queries]


def important_terms(text: str, *, limit: int) -> list[str]:
    ignored = {
        "paper",
        "authors",
        "author",
        "method",
        "approach",
        "against",
        "standard",
        "standards",
        "study",
        "using",
        "use",
        "show",
        "shows",
        "provide",
        "provides",
        "should",
        "could",
        "would",
        "lack",
        "lacks",
        "missing",
        "result",
        "results",
    }
    terms = [
        term.lower()
        for term in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text)
        if len(term) > 3 and term.lower() not in STOPWORDS and term.lower() not in ignored
    ]
    counts = Counter(terms)
    return [term for term, _ in counts.most_common(limit)]


def grade_and_filter_records(
    records: list[dict[str, Any]],
    *,
    paper: dict[str, Any],
    claim_plan: dict[str, Any],
    llm_client: StructuredLLMClient | None = None,
    model: str = DEFAULT_COLLECTOR_MODEL,
    max_items: int = 3,
) -> list[dict[str, Any]]:
    records = dedupe_records(records)
    if not records:
        return []
    fallback = deterministic_grade_records(records, claim_plan=claim_plan, max_items=max_items)
    if llm_client is None:
        return fallback
    try:
        payload = llm_client.complete_json(
            model=model,
            messages=external_grade_messages(paper, claim_plan, records),
            schema_name="external_evidence_grades",
            schema=external_grade_schema(),
        )
    except Exception:
        return fallback
    grades = payload.get("grades")
    if not isinstance(grades, list):
        return fallback
    by_id = {candidate_id(index): record for index, record in enumerate(records)}
    selected = []
    for raw in grades:
        if not isinstance(raw, dict) or not raw.get("relevant"):
            continue
        record = by_id.get(clean_text(raw.get("candidate_id")))
        if record is None:
            continue
        metadata = record.setdefault("metadata", {})
        metadata["llm_relevance_score"] = bounded_int(raw.get("relevance_score"), 0, 100)
        metadata["evidence_role"] = clean_text(raw.get("evidence_role")) or "field_context"
        metadata["relevance_reason"] = clean_text(raw.get("reason"))
        selected.append(record)
    selected.sort(key=lambda item: item.get("metadata", {}).get("llm_relevance_score", 0), reverse=True)
    return selected[:max_items] or fallback


def deterministic_grade_records(
    records: list[dict[str, Any]],
    *,
    claim_plan: dict[str, Any],
    max_items: int,
) -> list[dict[str, Any]]:
    query_terms = set(important_terms(f"{claim_plan.get('claim_text', '')} {claim_plan.get('claim_type', '')}", limit=12))
    scored = []
    for record in records:
        text_terms = set(important_terms(f"{record.get('section', '')} {record.get('text', '')}", limit=80))
        overlap = len(query_terms.intersection(text_terms))
        metadata = record.setdefault("metadata", {})
        cited_by = safe_int(metadata.get("cited_by_count")) or 0
        score = overlap * 10 + min(cited_by, 50) / 10
        metadata["deterministic_relevance_score"] = round(score, 2)
        metadata["evidence_role"] = "field_context"
        if overlap:
            scored.append((score, record))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [record for _, record in scored[:max_items]]


def attach_external_evidence_to_paper(paper: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return paper
    updated = copy.deepcopy(paper)
    sections = list(updated.get("paper_sections") or [])
    existing_keys = {record_key(section) for section in sections if isinstance(section, dict)}
    for record in records:
        key = record_key(record)
        if key in existing_keys:
            continue
        sections.append(record)
        existing_keys.add(key)
    updated["paper_sections"] = sections
    return updated


def enrich_dataset_with_external_evidence(
    dataset: dict[str, Any],
    *,
    claim_llm_client: StructuredLLMClient,
    claim_model: str = DEFAULT_CLAIM_MODEL,
    collector_llm_client: StructuredLLMClient | None = None,
    collector_model: str = DEFAULT_COLLECTOR_MODEL,
    providers: str | list[str] | tuple[str, ...] | None = None,
    openalex_client: OpenAlexClient | None = None,
    max_external_claims_per_review: int = 5,
    max_queries_per_claim: int = 2,
    max_openalex_results_per_query: int = 5,
    max_evidence_per_claim: int = 3,
) -> tuple[dict[str, Any], dict[str, Any]]:
    enriched = copy.deepcopy(dataset)
    provider_counts: Counter[str] = Counter()
    paper_count = 0
    review_count = 0
    record_count = 0
    errors: list[str] = []
    openalex_stats: Counter[str] = Counter()
    for paper in enriched.get("papers", []):
        paper_records = []
        for review in paper.get("reviews", []):
            review_count += 1
            claims = extract_claims(review, llm_client=claim_llm_client, model=claim_model)
            records, manifest = collect_external_evidence_for_claims(
                paper,
                claims,
                review=review,
                providers=providers,
                llm_client=collector_llm_client,
                model=collector_model,
                openalex_client=openalex_client,
                max_external_claims=max_external_claims_per_review,
                max_queries_per_claim=max_queries_per_claim,
                max_openalex_results_per_query=max_openalex_results_per_query,
                max_evidence_per_claim=max_evidence_per_claim,
            )
            paper_records.extend(records)
            provider_counts.update(manifest.get("provider_counts", {}))
            errors.extend(manifest.get("errors", []))
            openalex_stats.update(manifest.get("openalex_stats", {}))
        if paper_records:
            paper_count += 1
            merged = attach_external_evidence_to_paper(paper, dedupe_records(paper_records))
            paper["paper_sections"] = merged.get("paper_sections", [])
            record_count += len(dedupe_records(paper_records))
    manifest = {
        "external_evidence_version": EXTERNAL_EVIDENCE_VERSION,
        "providers": list(parse_providers(providers)),
        "paper_count": paper_count,
        "review_count": review_count,
        "record_count": record_count,
        "provider_counts": dict(provider_counts),
        "openalex_stats": dict(openalex_stats),
        "errors": errors[:10],
    }
    enriched["external_evidence"] = manifest
    return enriched, manifest


def external_plan_messages(
    paper: dict[str, Any],
    claims: list[dict[str, Any]],
    *,
    review: dict[str, Any] | None,
    max_queries_per_claim: int,
) -> list[dict[str, str]]:
    claim_payload = [
        {
            "claim_index": index,
            "claim_text": clean_text(claim.get("claim_text")),
            "claim_type": clean_text(claim.get("claim_type")),
            "importance": clean_text(claim.get("importance")),
            "source_sentence": clean_text(claim.get("source_sentence")),
        }
        for index, claim in enumerate(claims)
    ]
    payload = {
        "paper": {
            "title": clean_text(paper.get("title")),
            "abstract": clean_text(paper.get("abstract")),
            "venue": clean_text(paper.get("venue")),
            "year": paper.get("year"),
        },
        "review": {
            "review_id": clean_text((review or {}).get("review_id")),
            "rating_raw": clean_text((review or {}).get("rating_raw")),
        },
        "claims": claim_payload,
        "max_queries_per_claim": max_queries_per_claim,
    }
    return [
        {
            "role": "system",
            "content": (
                "You plan low-cost external evidence collection for peer-review audit. "
                "Select only claims that need field context, related work, baselines, experiments, method validity, "
                "theory, or venue norms. Do not select clarity, wording, or tone claims unless they mention field norms. "
                "Return compact scholarly search queries. Do not judge the reviewer point."
            ),
        },
        {"role": "user", "content": f"External evidence planning input JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"},
    ]


def external_plan_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "claim_index": {"type": "integer"},
                        "needs_external_evidence": {"type": "boolean"},
                        "reason": {"type": "string"},
                        "queries": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["claim_index", "needs_external_evidence", "reason", "queries"],
                },
            }
        },
        "required": ["claims"],
    }


def validate_external_plan(
    payload: dict[str, Any],
    claims: list[dict[str, Any]],
    paper: dict[str, Any],
    *,
    review: dict[str, Any] | None,
    max_queries_per_claim: int,
) -> list[dict[str, Any]]:
    fallback = deterministic_plan(
        paper,
        claims,
        review=review,
        max_external_claims=len(claims),
        max_queries_per_claim=max_queries_per_claim,
    )
    by_index = {item["claim_index"]: item for item in fallback}
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list):
        return []
    for raw in raw_claims:
        if not isinstance(raw, dict):
            continue
        index = raw.get("claim_index")
        if not isinstance(index, int) or index not in by_index:
            continue
        plan = by_index[index]
        plan["needs_external_evidence"] = bool(raw.get("needs_external_evidence"))
        plan["reason"] = clean_text(raw.get("reason")) or plan["reason"]
        queries = [clean_text(query) for query in raw.get("queries", []) if clean_text(query)]
        if queries:
            plan["queries"] = dedupe_strings(queries)[:max_queries_per_claim]
    return list(by_index.values())


def external_grade_messages(
    paper: dict[str, Any],
    claim_plan: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[dict[str, str]]:
    candidates = [
        {
            "candidate_id": candidate_id(index),
            "source_type": record.get("source_type"),
            "section": record.get("section"),
            "text": clean_text(record.get("text"))[:1200],
            "metadata": {
                "title": record.get("metadata", {}).get("title"),
                "publication_year": record.get("metadata", {}).get("publication_year"),
                "cited_by_count": record.get("metadata", {}).get("cited_by_count"),
            },
        }
        for index, record in enumerate(records)
    ]
    payload = {
        "paper": {
            "title": clean_text(paper.get("title")),
            "abstract": clean_text(paper.get("abstract"))[:1200],
        },
        "claim": {
            "claim_text": claim_plan.get("claim_text"),
            "claim_type": claim_plan.get("claim_type"),
            "reason_for_external_evidence": claim_plan.get("reason"),
        },
        "candidates": candidates,
    }
    return [
        {
            "role": "system",
            "content": (
                "Grade whether each external evidence candidate is relevant field context for the reviewer point. "
                "Prefer title/abstract matches that clarify related work, baselines, benchmarks, experiments, or venue norms. "
                "Do not infer correctness beyond the candidate text."
            ),
        },
        {"role": "user", "content": f"External evidence grading input JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"},
    ]


def external_grade_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "grades": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "relevant": {"type": "boolean"},
                        "relevance_score": {"type": "integer"},
                        "evidence_role": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["candidate_id", "relevant", "relevance_score", "evidence_role", "reason"],
                },
            }
        },
        "required": ["grades"],
    }


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    seen = set()
    for record in records:
        key = record_key(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def record_key(record: dict[str, Any]) -> str:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    return clean_text(metadata.get("stable_id") or f"{record.get('source_type')}:{record.get('section')}:{record.get('text')[:120]}")


def external_claim_id(review: dict[str, Any] | None, index: int, claim_text: str) -> str:
    review_id = clean_text((review or {}).get("review_id")) or "review"
    digest = hashlib.sha1(f"{review_id}:{index}:{claim_text}".encode("utf-8")).hexdigest()[:10]
    return f"external_claim_{digest}"


def candidate_id(index: int) -> str:
    return f"candidate_{index}"


def dedupe_strings(values: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for value in values:
        cleaned = clean_text(value)
        key = re.sub(r"\s+", " ", cleaned.lower())
        if cleaned and key not in seen:
            seen.add(key)
            deduped.append(cleaned)
    return deduped


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def bounded_int(value: Any, minimum: int, maximum: int) -> int:
    parsed = safe_int(value)
    if parsed is None:
        return minimum
    return max(minimum, min(maximum, parsed))
