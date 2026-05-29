from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from .models import Evidence
from .text import STOPWORDS, clean_text


RETRIEVAL_VERSION = "section-aware-bm25-v0.2"

CLAIM_TYPE_HINTS = {
    "ablation": {"ablation", "component", "module", "table", "appendix", "experiment"},
    "baseline": {"baseline", "compare", "comparison", "sota", "experiment", "result"},
    "experiment": {"experiment", "evaluation", "result", "metric", "dataset", "table"},
    "methodology": {"method", "model", "algorithm", "architecture", "approach"},
    "theory": {"theorem", "proof", "lemma", "assumption"},
    "clarity": {"clarity", "explain", "definition", "notation", "presentation"},
    "writing": {"writing", "readability", "typo", "presentation"},
    "ethics": {"ethic", "privacy", "safety", "harm"},
}

QUERY_EXPANSIONS = {
    "ablation": {"ablation", "component", "module"},
    "baseline": {"baseline", "compare", "comparison"},
    "compare": {"compare", "comparison", "baseline"},
    "comparison": {"comparison", "compare", "baseline"},
    "evaluation": {"evaluation", "experiment", "result"},
    "experiment": {"experiment", "evaluation", "result"},
    "metric": {"metric", "score", "result"},
    "dataset": {"dataset", "data", "benchmark"},
}


def normalize_token(token: str) -> str:
    token = token.lower()
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def token_list(text: str) -> list[str]:
    return [
        normalize_token(token)
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        if token not in STOPWORDS
    ]


def expand_query_terms(claim_text: str, claim_type: str) -> list[str]:
    terms = set(token_list(claim_text))
    terms.update(CLAIM_TYPE_HINTS.get(claim_type, set()))
    for term in list(terms):
        terms.update(QUERY_EXPANSIONS.get(term, set()))
    return sorted(terms)


def build_evidence_sources(paper: dict[str, Any], *, include_rebuttals: bool = False) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []

    def add(
        source_type: str,
        section: str,
        text: Any,
        page: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        cleaned = clean_text(text)
        if not cleaned:
            return
        sources.append(
            {
                "source_type": source_type,
                "section": section,
                "page": page,
                "text": cleaned,
                "metadata": metadata or {},
            }
        )

    add("paper", "title", paper.get("title"))
    add("paper", "abstract", paper.get("abstract"))
    if include_rebuttals:
        for idx, rebuttal in enumerate(paper.get("rebuttals", []), start=1):
            add("rebuttal", f"author_response_{idx}", rebuttal.get("text"))
    for idx, section in enumerate(paper.get("paper_sections", []), start=1):
        add(
            section.get("source_type", "paper"),
            section.get("section") or f"section_{idx}",
            section.get("text"),
            section.get("page"),
            section.get("metadata") if isinstance(section.get("metadata"), dict) else {},
        )
    return sources


def section_weight(source: dict[str, Any], claim_type: str) -> float:
    section = str(source.get("section", "")).lower()
    source_type = str(source.get("source_type", "")).lower()
    weight = 1.0
    if section == "title":
        weight *= 0.6
    if source_type == "rebuttal":
        weight *= 1.08
    if source_type in {"venue_guideline", "field_consensus"}:
        weight *= 1.05
    if source_type == "external_reference":
        weight *= 1.02
    if source_type == "appendix" or "appendix" in section:
        weight *= 1.12

    hints = CLAIM_TYPE_HINTS.get(claim_type, set())
    if hints and any(hint in section for hint in hints):
        weight *= 1.25
    if claim_type in {"ablation", "baseline", "experiment"} and any(
        hint in section for hint in ("experiment", "result", "evaluation", "table", "appendix")
    ):
        weight *= 1.2
    if claim_type == "methodology" and any(hint in section for hint in ("method", "model", "approach", "algorithm")):
        weight *= 1.2
    return weight


def make_snippet(text: str, query_terms: list[str], max_chars: int = 700) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    lowered = text.lower()
    positions = [lowered.find(term) for term in query_terms if len(term) >= 4 and lowered.find(term) >= 0]
    start = min(positions) if positions else 0
    start = max(0, start - max_chars // 3)
    end = min(len(text), start + max_chars)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."
    return snippet


def retrieve_evidence(
    claim_id: str,
    claim_text: str,
    paper: dict[str, Any],
    *,
    claim_type: str = "general",
    top_k: int = 3,
    include_rebuttals: bool = False,
) -> list[Evidence]:
    query_terms = expand_query_terms(claim_text, claim_type)
    if not query_terms:
        return []

    sources = build_evidence_sources(paper, include_rebuttals=include_rebuttals)
    if not sources:
        return []

    doc_terms = [token_list(f"{source.get('section', '')} {source.get('section', '')} {source.get('text', '')}") for source in sources]
    doc_lengths = [len(terms) for terms in doc_terms]
    avg_doc_length = sum(doc_lengths) / max(len(doc_lengths), 1)
    document_frequency = Counter(term for terms in doc_terms for term in set(terms))
    query_unique_terms = sorted(set(query_terms))

    scored: list[tuple[float, float, list[str], dict[str, Any]]] = []
    for source, terms, length in zip(sources, doc_terms, doc_lengths):
        counts = Counter(terms)
        matched = [term for term in query_unique_terms if counts.get(term, 0)]
        if not matched:
            continue
        raw_score = bm25_score(matched, counts, length, avg_doc_length, document_frequency, len(sources))
        coverage = len(matched) / max(len(query_unique_terms), 1)
        weighted_score = raw_score * section_weight(source, claim_type) * (0.75 + 0.25 * coverage)
        score = weighted_score / (weighted_score + 3.0)
        scored.append((score, raw_score, matched, source))

    scored.sort(key=lambda item: item[0], reverse=True)

    evidence_items: list[Evidence] = []
    for idx, (score, raw_score, matched, source) in enumerate(scored[:top_k], start=1):
        evidence_items.append(
            Evidence(
                evidence_id=f"{claim_id}_ev{idx}",
                claim_id=claim_id,
                source_type=source["source_type"],
                section=source["section"],
                page=source.get("page"),
                text=make_snippet(source["text"], matched),
                verdict="supporting_candidate" if score >= 0.45 else "partial_candidate",
                confidence="medium" if score >= 0.45 else "low",
                score=round(score, 3),
                raw_score=round(raw_score, 3),
                matched_terms=matched[:12],
                metadata=source.get("metadata", {}),
            )
        )
    return evidence_items


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
