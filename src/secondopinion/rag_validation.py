from __future__ import annotations

import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .concern_calibration import normalized_calibration_record
from .model_config import DEFAULT_CHEAP_MODEL
from .retrieval import token_list
from .text import clean_text


CONCERN_RAG_VALIDATION_VERSION = "concern-rag-validation-v0.1"
DEFAULT_RAG_VALIDATION_MODEL = DEFAULT_CHEAP_MODEL
MATCH_LABELS = ("survived", "partial", "not_found", "unsure")
QUALITY_LABELS = ("high", "medium", "low", "unsure")


def validate_concern_rag(
    records: list[dict[str, Any]],
    memory_records: list[dict[str, Any]],
    *,
    top_ks: tuple[int, ...] = (1, 3, 5),
    exclude_same_paper: bool = False,
) -> dict[str, Any]:
    records = [normalized_calibration_record(record) for record in records]
    memory_records = [normalize_memory_record(record) for record in memory_records]
    top_ks = tuple(sorted(set(k for k in top_ks if k > 0))) or (1, 3, 5)
    max_k = max(top_ks)

    rows = []
    for record in records:
        candidates = [
            item
            for item in memory_records
            if item.get("source_task_id") != record.get("task_id")
            and (not exclude_same_paper or item.get("paper_id") != record.get("paper_id"))
        ]
        retrieved = retrieve_concern_cases(record, candidates, top_k=max_k)
        rows.append(evaluate_retrieval_row(record, retrieved, top_ks=top_ks, candidate_count=len(candidates)))

    return build_rag_validation_report(
        rows,
        records=records,
        memory_records=memory_records,
        top_ks=top_ks,
        exclude_same_paper=exclude_same_paper,
    )


def retrieve_concern_cases(
    query_record: dict[str, Any],
    memory_records: list[dict[str, Any]],
    *,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    query_terms = token_list(query_text(query_record))
    if not query_terms:
        return []
    doc_terms = [token_list(memory_text(record)) for record in memory_records]
    doc_lengths = [len(terms) for terms in doc_terms]
    avg_doc_length = sum(doc_lengths) / max(len(doc_lengths), 1)
    document_frequency = Counter(term for terms in doc_terms for term in set(terms))
    query_unique = sorted(set(query_terms))

    scored = []
    for record, terms, length in zip(memory_records, doc_terms, doc_lengths):
        counts = Counter(terms)
        matched = [term for term in query_unique if counts.get(term, 0)]
        if not matched:
            continue
        raw_score = bm25_score(matched, counts, length, avg_doc_length, document_frequency, len(memory_records))
        type_bonus = 0.18 if claim_type(record) == claim_type(query_record) and claim_type(record) else 0.0
        score = raw_score + type_bonus
        scored.append((score, matched, record))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            **record,
            "retrieval_score": round(score, 4),
            "matched_terms": matched[:12],
        }
        for score, matched, record in scored[:top_k]
    ]


def evaluate_retrieval_row(
    record: dict[str, Any],
    retrieved: list[dict[str, Any]],
    *,
    top_ks: tuple[int, ...],
    candidate_count: int,
) -> dict[str, Any]:
    gold_match = meta_review_match(record)
    gold_quality = concern_quality(record)
    gold_type = claim_type(record)
    row = {
        "task_id": record.get("task_id", ""),
        "paper_id": record.get("paper_id", ""),
        "claim_type": gold_type,
        "gold_meta_review_match": gold_match,
        "gold_concern_quality": gold_quality,
        "candidate_count": candidate_count,
        "retrieved": [
            {
                "source_task_id": item.get("source_task_id", ""),
                "paper_id": item.get("paper_id", ""),
                "claim_type": claim_type(item),
                "meta_review_match": memory_match(item),
                "concern_quality": memory_quality(item),
                "retrieval_score": item.get("retrieval_score", 0.0),
                "matched_terms": item.get("matched_terms", []),
            }
            for item in retrieved
        ],
    }
    for k in top_ks:
        top = retrieved[:k]
        row[f"match_hit@{k}"] = any(memory_match(item) == gold_match for item in top)
        row[f"quality_hit@{k}"] = any(memory_quality(item) == gold_quality for item in top)
        row[f"type_hit@{k}"] = any(claim_type(item) == gold_type and gold_type for item in top)
        row[f"match_knn@{k}"] = majority_label([memory_match(item) for item in top])
        row[f"quality_knn@{k}"] = majority_label([memory_quality(item) for item in top])
        row[f"match_knn_correct@{k}"] = row[f"match_knn@{k}"] == gold_match
        row[f"quality_knn_correct@{k}"] = row[f"quality_knn@{k}"] == gold_quality
    row["match_rr"] = reciprocal_rank(retrieved, gold_match, label_fn=memory_match)
    row["quality_rr"] = reciprocal_rank(retrieved, gold_quality, label_fn=memory_quality)
    return row


def build_rag_validation_report(
    rows: list[dict[str, Any]],
    *,
    records: list[dict[str, Any]],
    memory_records: list[dict[str, Any]],
    top_ks: tuple[int, ...],
    exclude_same_paper: bool,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "query_count": len(rows),
        "memory_count": len(memory_records),
        "exclude_same_paper": exclude_same_paper,
        "gold_meta_review_match_counts": dict(Counter(meta_review_match(record) for record in records)),
        "gold_concern_quality_counts": dict(Counter(concern_quality(record) for record in records)),
        "memory_match_counts": dict(Counter(memory_match(record) for record in memory_records)),
        "memory_quality_counts": dict(Counter(memory_quality(record) for record in memory_records)),
        "match_mrr": safe_mean(row["match_rr"] for row in rows),
        "quality_mrr": safe_mean(row["quality_rr"] for row in rows),
    }
    random_baselines = random_baseline_rates(records, memory_records, top_ks=top_ks, exclude_same_paper=exclude_same_paper)
    for k in top_ks:
        summary[f"match_hit@{k}"] = rate(rows, f"match_hit@{k}")
        summary[f"quality_hit@{k}"] = rate(rows, f"quality_hit@{k}")
        summary[f"type_hit@{k}"] = rate(rows, f"type_hit@{k}")
        summary[f"match_knn_accuracy@{k}"] = rate(rows, f"match_knn_correct@{k}")
        summary[f"quality_knn_accuracy@{k}"] = rate(rows, f"quality_knn_correct@{k}")
        summary[f"random_match_hit@{k}"] = random_baselines[f"match_hit@{k}"]
        summary[f"random_quality_hit@{k}"] = random_baselines[f"quality_hit@{k}"]

    by_match = {}
    for label, group in group_rows(rows, "gold_meta_review_match").items():
        by_match[label] = {
            "count": len(group),
            **{f"match_hit@{k}": rate(group, f"match_hit@{k}") for k in top_ks},
            **{f"match_knn_accuracy@{k}": rate(group, f"match_knn_correct@{k}") for k in top_ks},
        }

    return {
        "schema_version": "0.1",
        "validation_version": CONCERN_RAG_VALIDATION_VERSION,
        "summary": summary,
        "by_meta_review_match": by_match,
        "examples": {
            "match_hits": [row for row in rows if row.get(f"match_hit@{max(top_ks)}")][:10],
            "match_misses": [row for row in rows if not row.get(f"match_hit@{max(top_ks)}")][:10],
        },
        "rows": rows,
    }


def random_baseline_rates(
    records: list[dict[str, Any]],
    memory_records: list[dict[str, Any]],
    *,
    top_ks: tuple[int, ...],
    exclude_same_paper: bool,
) -> dict[str, float]:
    totals: dict[str, list[float]] = defaultdict(list)
    for record in records:
        candidates = [
            item
            for item in memory_records
            if item.get("source_task_id") != record.get("task_id")
            and (not exclude_same_paper or item.get("paper_id") != record.get("paper_id"))
        ]
        for k in top_ks:
            totals[f"match_hit@{k}"].append(random_hit_probability(candidates, meta_review_match(record), k, memory_match))
            totals[f"quality_hit@{k}"].append(random_hit_probability(candidates, concern_quality(record), k, memory_quality))
    return {key: round(sum(values) / max(len(values), 1), 4) for key, values in totals.items()}


def random_hit_probability(candidates: list[dict[str, Any]], label: str, k: int, label_fn: Any) -> float:
    n = len(candidates)
    if n <= 0 or k <= 0:
        return 0.0
    positives = sum(1 for item in candidates if label_fn(item) == label)
    if positives <= 0:
        return 0.0
    k = min(k, n)
    misses = n - positives
    return 1.0 - combination_ratio(misses, k, n)


def combination_ratio(success_population: int, draws: int, total_population: int) -> float:
    if draws > success_population:
        return 0.0
    if draws > total_population:
        return 0.0
    return math.comb(success_population, draws) / max(math.comb(total_population, draws), 1)


def run_rag_judgment_ablation(
    records: list[dict[str, Any]],
    memory_records: list[dict[str, Any]],
    *,
    llm_client: Any,
    model: str = DEFAULT_RAG_VALIDATION_MODEL,
    limit: int = 24,
    top_k: int = 3,
    exclude_same_paper: bool = False,
    include_current_meta_review: bool = False,
) -> dict[str, Any]:
    records = [normalized_calibration_record(record) for record in records[: max(0, limit)]]
    memory_records = [normalize_memory_record(record) for record in memory_records]
    rows = []
    for record in records:
        retrieved = retrieve_concern_cases(
            record,
            [
                item
                for item in memory_records
                if item.get("source_task_id") != record.get("task_id")
                and (not exclude_same_paper or item.get("paper_id") != record.get("paper_id"))
            ],
            top_k=top_k,
        )
        no_rag = judge_record(
            record,
            retrieved=[],
            llm_client=llm_client,
            model=model,
            include_current_meta_review=include_current_meta_review,
        )
        with_rag = judge_record(
            record,
            retrieved=retrieved,
            llm_client=llm_client,
            model=model,
            include_current_meta_review=include_current_meta_review,
        )
        gold_match = meta_review_match(record)
        gold_quality = concern_quality(record)
        rows.append(
            {
                "task_id": record.get("task_id", ""),
                "gold_meta_review_match": gold_match,
                "gold_concern_quality": gold_quality,
                "no_rag": no_rag,
                "with_rag": with_rag,
                "retrieved": [
                    {
                        "source_task_id": item.get("source_task_id", ""),
                        "match": memory_match(item),
                        "quality": memory_quality(item),
                        "claim": item.get("claim", {}).get("text", ""),
                    }
                    for item in retrieved
                ],
                "no_rag_match_correct": no_rag.get("meta_review_match") == gold_match,
                "with_rag_match_correct": with_rag.get("meta_review_match") == gold_match,
                "no_rag_quality_correct": no_rag.get("concern_quality") == gold_quality,
                "with_rag_quality_correct": with_rag.get("concern_quality") == gold_quality,
            }
        )
    return {
        "schema_version": "0.1",
        "validation_version": CONCERN_RAG_VALIDATION_VERSION,
        "model": model,
        "summary": {
            "query_count": len(rows),
            "top_k": top_k,
            "exclude_same_paper": exclude_same_paper,
            "include_current_meta_review": include_current_meta_review,
            "no_rag_match_accuracy": rate(rows, "no_rag_match_correct"),
            "with_rag_match_accuracy": rate(rows, "with_rag_match_correct"),
            "no_rag_quality_accuracy": rate(rows, "no_rag_quality_correct"),
            "with_rag_quality_accuracy": rate(rows, "with_rag_quality_correct"),
        },
        "rows": rows,
    }


def judge_record(
    record: dict[str, Any],
    *,
    retrieved: list[dict[str, Any]],
    llm_client: Any,
    model: str,
    include_current_meta_review: bool,
) -> dict[str, Any]:
    payload = llm_client.complete_json(
        model=model,
        messages=judgment_messages(record, retrieved, include_current_meta_review=include_current_meta_review),
        schema_name="concern_rag_judgment",
        schema=judgment_schema(),
    )
    return payload


def judgment_messages(
    record: dict[str, Any],
    retrieved: list[dict[str, Any]],
    *,
    include_current_meta_review: bool = False,
) -> list[dict[str, str]]:
    task = {
        "reviewer_claim": record.get("claim_text", ""),
        "claim_type": record.get("claim_type", ""),
        "source_sentence": record.get("source_sentence", ""),
        "retrieved_historical_cases": [
            {
                "claim": item.get("claim", {}).get("text", ""),
                "claim_type": item.get("claim", {}).get("type", ""),
                "meta_review_match": item.get("meta_review", {}).get("match", ""),
                "ac_treatment": item.get("meta_review", {}).get("ac_treatment", ""),
                "concern_quality": item.get("quality", {}).get("concern_quality", ""),
                "rationale": item.get("rationale", ""),
            }
            for item in retrieved
        ],
    }
    if include_current_meta_review:
        task["matched_meta_review_segment"] = record.get("matched_meta_segment", "")
        task["meta_review_text"] = clean_text(record.get("meta_review_text", ""))[:5000]
    return [
        {
            "role": "system",
            "content": (
                "You judge reviewer-claim quality using only the provided pre-decision inputs. "
                "The current paper's meta-review is hidden unless explicitly included in the task JSON. "
                "Historical cases are analogies only; do not copy their labels unless the current evidence supports it. "
                "Return JSON matching the schema."
            ),
        },
        {"role": "user", "content": json.dumps(task, ensure_ascii=False, indent=2)},
    ]


def judgment_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "meta_review_match": {"type": "string", "enum": list(MATCH_LABELS)},
            "ac_treatment": {
                "type": "string",
                "enum": [
                    "endorsed_or_relied_on",
                    "mentioned_neutrally",
                    "mentioned_as_resolved_or_outweighed",
                    "not_mentioned",
                    "unclear",
                ],
            },
            "concern_quality": {"type": "string", "enum": list(QUALITY_LABELS)},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "rationale": {"type": "string"},
        },
        "required": ["meta_review_match", "ac_treatment", "concern_quality", "confidence", "rationale"],
    }


def normalize_memory_record(record: dict[str, Any]) -> dict[str, Any]:
    if "claim" in record and "meta_review" in record:
        return record
    record = normalized_calibration_record(record)
    return {
        "source_task_id": record.get("task_id", ""),
        "paper_id": record.get("paper_id", ""),
        "review_id": record.get("review_id", ""),
        "title": record.get("title", ""),
        "decision_label": record.get("decision_label", ""),
        "claim": {
            "text": record.get("claim_text", ""),
            "type": record.get("claim_type", ""),
            "importance": record.get("importance", ""),
            "source_sentence": record.get("source_sentence", ""),
        },
        "meta_review": {
            "match": record.get("llm_meta_review_match", ""),
            "ac_treatment": record.get("llm_ac_treatment", ""),
            "matched_segment": record.get("matched_meta_segment", ""),
        },
        "quality": {
            "concern_quality": record.get("llm_concern_quality", ""),
            "label_evidence_strength": record.get("llm_label_evidence_strength", ""),
            "confidence": record.get("llm_confidence", ""),
        },
        "rationale": record.get("llm_rationale", ""),
    }


def write_rag_validation_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_rag_validation_markdown(report), encoding="utf-8")


def render_rag_validation_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    keys = [key for key in summary if "@" in key or key.endswith("_mrr")]
    lines = [
        "# Concern RAG Validation",
        "",
        f"- Queries: {summary.get('query_count', 0)}",
        f"- Memory records: {summary.get('memory_count', 0)}",
        f"- Exclude same paper: {summary.get('exclude_same_paper', False)}",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in sorted(keys):
        lines.append(f"| `{key}` | {format_metric(summary.get(key, 0.0))} |")
    lines.extend(["", "## Label Counts", ""])
    for key in ("gold_meta_review_match_counts", "memory_match_counts", "gold_concern_quality_counts", "memory_quality_counts"):
        lines.append(f"- `{key}`: `{json.dumps(summary.get(key, {}), ensure_ascii=False, sort_keys=True)}`")
    lines.extend(["", "## Miss Examples", ""])
    for row in report.get("examples", {}).get("match_misses", [])[:8]:
        retrieved = row.get("retrieved", [])[:3]
        lines.append(f"- `{row['task_id']}` gold=`{row['gold_meta_review_match']}` retrieved={[item['meta_review_match'] for item in retrieved]}")
    return "\n".join(lines)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query_text(record: dict[str, Any]) -> str:
    return " ".join(
        clean_text(part)
        for part in (
            record.get("claim_text") or record.get("claim", {}).get("text", ""),
            record.get("source_sentence") or record.get("claim", {}).get("source_sentence", ""),
            record.get("claim_type") or record.get("claim", {}).get("type", ""),
        )
        if clean_text(part)
    )


def memory_text(record: dict[str, Any]) -> str:
    claim = record.get("claim", {})
    return " ".join(
        clean_text(part)
        for part in (
            claim.get("text", ""),
            claim.get("source_sentence", ""),
            claim.get("type", ""),
        )
        if clean_text(part)
    )


def meta_review_match(record: dict[str, Any]) -> str:
    return record.get("llm_meta_review_match", record.get("llm_survival_label", ""))


def concern_quality(record: dict[str, Any]) -> str:
    return record.get("llm_concern_quality", "")


def memory_match(record: dict[str, Any]) -> str:
    return record.get("meta_review", {}).get("match", meta_review_match(record))


def memory_quality(record: dict[str, Any]) -> str:
    return record.get("quality", {}).get("concern_quality", concern_quality(record))


def claim_type(record: dict[str, Any]) -> str:
    return record.get("claim_type", record.get("claim", {}).get("type", ""))


def majority_label(labels: list[str]) -> str:
    labels = [label for label in labels if label]
    if not labels:
        return ""
    counts = Counter(labels)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def reciprocal_rank(items: list[dict[str, Any]], gold_label: str, *, label_fn: Any) -> float:
    for rank, item in enumerate(items, start=1):
        if label_fn(item) == gold_label:
            return round(1.0 / rank, 4)
    return 0.0


def rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if row.get(key)) / len(rows), 4)


def safe_mean(values: Any) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def group_rows(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key, ""))].append(row)
    return dict(groups)


def bm25_score(
    terms: list[str],
    counts: Counter[str],
    doc_length: int,
    avg_doc_length: float,
    document_frequency: Counter[str],
    doc_count: int,
) -> float:
    k1 = 1.4
    b = 0.75
    score = 0.0
    for term in terms:
        frequency = counts[term]
        idf = math.log(1 + (doc_count - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
        denominator = frequency + k1 * (1 - b + b * doc_length / max(avg_doc_length, 1))
        score += idf * frequency * (k1 + 1) / denominator
    return score


def format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def parse_top_ks(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def concat_records(*record_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(itertools.chain.from_iterable(record_lists))
