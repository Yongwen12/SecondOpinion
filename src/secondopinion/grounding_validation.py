from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Any

from .claim_extraction import (
    CLAIM_EXTRACTION_VERSION,
    DEFAULT_CLAIM_MODEL,
    SOURCE_FIELDS,
    StructuredLLMClient,
    build_claim_messages,
    claim_extraction_schema,
    contains_normalized,
    source_locator,
    source_sentence_index,
    validate_claim,
    validate_claim_payload,
)
from .text import clean_text


GROUNDING_VALIDATION_VERSION = "grounding-validation-v0.2"
LOW_CLAIM_SOURCE_OVERLAP_THRESHOLD = 0.18
P0_FINAL_GROUNDING_TARGET = 0.95
SOURCE_FIELD_VALID_TARGET = 0.99

TOKEN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "could",
    "does",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "paper",
    "review",
    "submission",
    "that",
    "the",
    "their",
    "there",
    "this",
    "to",
    "with",
    "would",
}


class RetryingStructuredLLMClient:
    def __init__(
        self,
        client: StructuredLLMClient,
        *,
        retries: int = 2,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.client = client
        self.retries = max(0, retries)
        self.backoff_seconds = max(0.0, backoff_seconds)

    def complete_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                return self.client.complete_json(
                    model=model,
                    messages=messages,
                    schema_name=schema_name,
                    schema=schema,
                )
            except Exception as exc:  # noqa: BLE001 - validation should record transient API failures.
                last_error = exc
                if attempt >= self.retries:
                    break
                time.sleep(self.backoff_seconds * (2**attempt))
        assert last_error is not None
        raise last_error


def validate_grounding_for_dataset(
    dataset: dict[str, Any],
    *,
    llm_client: StructuredLLMClient,
    model: str = DEFAULT_CLAIM_MODEL,
    review_limit: int | None = 200,
    max_claims: int = 8,
) -> dict[str, Any]:
    records = list(iter_review_records(dataset))
    if review_limit is not None:
        records = records[: max(0, review_limit)]

    review_results = []
    raw_failure_examples = []
    final_failure_examples = []
    warning_examples = []
    source_field_counts: Counter[str] = Counter()
    raw_failure_reason_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()

    stats = {
        "requested_review_limit": review_limit,
        "review_count": len(records),
        "review_error_count": 0,
        "review_no_claim_count": 0,
        "raw_candidate_count": 0,
        "raw_grounding_pass_count": 0,
        "raw_grounding_fail_count": 0,
        "raw_single_claim_valid_count": 0,
        "final_claim_count": 0,
        "final_grounding_pass_count": 0,
        "final_grounding_fail_count": 0,
        "source_field_valid_count": 0,
        "source_text_present_count": 0,
        "source_span_found_count": 0,
        "source_paragraph_found_count": 0,
        "source_bullet_found_count": 0,
        "source_sentence_index_found_count": 0,
        "low_claim_source_overlap_count": 0,
        "summary_or_strengths_claim_count": 0,
    }

    for record in records:
        result = validate_review_grounding(
            record,
            llm_client=llm_client,
            model=model,
            max_claims=max_claims,
        )
        review_results.append(result)
        if result.get("error"):
            stats["review_error_count"] += 1
            continue

        raw_candidates = result.get("raw_candidates", [])
        final_claims = result.get("claims", [])
        stats["raw_candidate_count"] += len(raw_candidates)
        stats["final_claim_count"] += len(final_claims)
        if not final_claims:
            stats["review_no_claim_count"] += 1

        for candidate in raw_candidates:
            if candidate.get("grounding_pass"):
                stats["raw_grounding_pass_count"] += 1
            else:
                stats["raw_grounding_fail_count"] += 1
                for reason in candidate.get("failure_reasons", []):
                    raw_failure_reason_counts[reason] += 1
                if len(raw_failure_examples) < 25:
                    raw_failure_examples.append(example_from_record(record, candidate))
            if candidate.get("single_claim_valid"):
                stats["raw_single_claim_valid_count"] += 1

        for claim in final_claims:
            source_field = str(claim.get("source_field") or "unknown")
            source_field_counts[source_field] += 1
            if claim.get("grounding_pass"):
                stats["final_grounding_pass_count"] += 1
            else:
                stats["final_grounding_fail_count"] += 1
                if len(final_failure_examples) < 25:
                    final_failure_examples.append(example_from_record(record, claim))
            if claim.get("source_field_valid"):
                stats["source_field_valid_count"] += 1
            if claim.get("source_text_present"):
                stats["source_text_present_count"] += 1
            if claim.get("source_span_found"):
                stats["source_span_found_count"] += 1
            if claim.get("source_paragraph_index") is not None:
                stats["source_paragraph_found_count"] += 1
            if claim.get("source_bullet_index") is not None:
                stats["source_bullet_found_count"] += 1
            if claim.get("source_sentence_index_found"):
                stats["source_sentence_index_found_count"] += 1
            if claim.get("low_claim_source_overlap"):
                stats["low_claim_source_overlap_count"] += 1
            if source_field in {"summary", "strengths"}:
                stats["summary_or_strengths_claim_count"] += 1
            for warning in claim.get("warnings", []):
                warning_counts[warning] += 1
                if len(warning_examples) < 25:
                    warning_examples.append(example_from_record(record, claim))

    stats.update(rate_stats(stats))
    status = validation_status(stats)
    return {
        "schema_version": "0.1",
        "validation_version": GROUNDING_VALIDATION_VERSION,
        "claim_extraction_version": CLAIM_EXTRACTION_VERSION,
        "model": model,
        "status": status,
        "thresholds": {
            "final_grounding_pass_rate": P0_FINAL_GROUNDING_TARGET,
            "source_field_valid_rate": SOURCE_FIELD_VALID_TARGET,
        },
        "dataset": {
            "name": dataset.get("dataset", ""),
            "paper_count": dataset.get("paper_count", len(dataset.get("papers", []))),
            "review_count": dataset.get("review_count", sum(len(paper.get("reviews", [])) for paper in dataset.get("papers", []))),
        },
        "stats": {
            **stats,
            "source_field_counts": dict(source_field_counts),
            "raw_failure_reason_counts": dict(raw_failure_reason_counts),
            "warning_counts": dict(warning_counts),
        },
        "examples": {
            "raw_grounding_failures": raw_failure_examples,
            "final_grounding_failures": final_failure_examples,
            "warnings": warning_examples,
        },
        "reviews": review_results,
    }


def validate_review_grounding(
    record: dict[str, Any],
    *,
    llm_client: StructuredLLMClient,
    model: str,
    max_claims: int,
) -> dict[str, Any]:
    review = record["review"]
    base = {
        "paper_id": record.get("paper_id", ""),
        "paper_title": record.get("paper_title", ""),
        "review_id": record.get("review_id", ""),
        "paper_index": record.get("paper_index"),
        "review_index": record.get("review_index"),
    }
    try:
        payload = llm_client.complete_json(
            model=model,
            messages=build_claim_messages(review, max_claims=max_claims),
            schema_name="review_claim_extraction",
            schema=claim_extraction_schema(max_claims=max_claims),
        )
    except Exception as exc:  # noqa: BLE001 - report per-review extraction failures.
        return {
            **base,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "raw_candidates": [],
            "claims": [],
        }

    raw_claims = payload.get("claims", [])
    if not isinstance(raw_claims, list):
        raw_claims = []

    raw_candidates = [
        validate_raw_candidate_grounding(review, raw_claim, candidate_index=index)
        for index, raw_claim in enumerate(raw_claims)
    ]
    claims = validate_claim_payload(payload, review, max_claims=max_claims)
    claim_results = []
    for index, claim in enumerate(claims):
        claim["extraction_version"] = CLAIM_EXTRACTION_VERSION
        claim_results.append(validate_final_claim_grounding(review, claim, claim_index=index))

    return {
        **base,
        "status": "ok",
        "raw_candidate_count": len(raw_candidates),
        "claim_count": len(claim_results),
        "raw_candidates": raw_candidates,
        "claims": claim_results,
    }


def validate_raw_candidate_grounding(
    review: dict[str, Any],
    raw_claim: Any,
    *,
    candidate_index: int,
) -> dict[str, Any]:
    if not isinstance(raw_claim, dict):
        return {
            "candidate_index": candidate_index,
            "claim_text": "",
            "source_field": "",
            "source_sentence": "",
            "grounding_pass": False,
            "single_claim_valid": False,
            "failure_reasons": ["non_object_candidate"],
            "warnings": [],
        }

    grounding = base_grounding_checks(review, raw_claim)
    single_claim_valid = validate_claim(raw_claim, review) is not None
    return {
        "candidate_index": candidate_index,
        "claim_text": truncate(clean_text(raw_claim.get("claim_text")), 400),
        "claim_type": clean_text(raw_claim.get("claim_type")),
        "importance": clean_text(raw_claim.get("importance")),
        **grounding,
        "single_claim_valid": single_claim_valid,
    }


def validate_final_claim_grounding(
    review: dict[str, Any],
    claim: dict[str, Any],
    *,
    claim_index: int,
) -> dict[str, Any]:
    grounding = base_grounding_checks(review, claim)
    overlap = claim_source_token_overlap(
        clean_text(claim.get("claim_text")),
        clean_text(claim.get("source_sentence")),
    )
    claim_token_count = len(content_tokens(clean_text(claim.get("claim_text"))))
    warnings = list(grounding["warnings"])
    source_field = grounding["source_field"]
    if source_field in {"summary", "strengths"}:
        warnings.append("summary_or_strengths_source")
    low_overlap = claim_token_count >= 4 and overlap < LOW_CLAIM_SOURCE_OVERLAP_THRESHOLD
    if low_overlap:
        warnings.append("low_claim_source_overlap")

    return {
        "claim_index": claim_index,
        "claim_text": truncate(clean_text(claim.get("claim_text")), 400),
        "claim_type": clean_text(claim.get("claim_type")),
        "importance": clean_text(claim.get("importance")),
        "extraction_reason": truncate(clean_text(claim.get("extraction_reason")), 400),
        "source_sentence_index": claim.get("source_sentence_index"),
        "claim_source_token_overlap": round(overlap, 3),
        "low_claim_source_overlap": low_overlap,
        **grounding,
        "warnings": warnings,
    }


def base_grounding_checks(review: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    source_field = clean_text(claim.get("source_field"))
    source_sentence = clean_text(claim.get("source_sentence"))
    source_field_valid = source_field in SOURCE_FIELDS
    source_text = clean_text(review.get(source_field)) if source_field_valid else ""
    source_text_present = bool(source_text)
    exact_match = bool(source_sentence and source_text and source_sentence in source_text)
    normalized_match = bool(source_sentence and source_text and contains_normalized(source_text, source_sentence))
    sentence_index = (
        source_sentence_index(review, source_field, source_sentence)
        if source_field_valid and source_sentence and source_text_present
        else None
    )
    locator = (
        source_locator(review, source_field, source_sentence)
        if source_field_valid and source_sentence and source_text_present
        else empty_source_locator()
    )
    char_start = locator.get("char_start")
    char_end = locator.get("char_end")
    failure_reasons = []
    if not source_field:
        failure_reasons.append("missing_source_field")
    elif not source_field_valid:
        failure_reasons.append("invalid_source_field")
    if not source_sentence:
        failure_reasons.append("missing_source_sentence")
    elif source_field_valid and not source_text_present:
        failure_reasons.append("missing_source_text")
    elif source_text_present and not normalized_match:
        failure_reasons.append("source_sentence_not_found")

    return {
        "source_field": source_field,
        "source_sentence": truncate(source_sentence, 600),
        "source_excerpt": source_excerpt(source_text, source_sentence),
        "source_field_valid": source_field_valid,
        "source_text_present": source_text_present,
        "exact_match": exact_match,
        "normalized_match": normalized_match,
        "source_locator": locator,
        "source_char_start": char_start,
        "source_char_end": char_end,
        "source_span_found": char_start is not None and char_end is not None,
        "source_paragraph_index": locator.get("paragraph_index"),
        "source_bullet_index": locator.get("bullet_index"),
        "source_line_start": locator.get("line_start"),
        "source_line_end": locator.get("line_end"),
        "source_match_strategy": locator.get("match_strategy"),
        "source_sentence_index_found": sentence_index is not None,
        "computed_source_sentence_index": sentence_index,
        "grounding_pass": source_field_valid and source_text_present and normalized_match,
        "failure_reasons": failure_reasons,
        "warnings": [],
    }


def iter_review_records(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for paper_index, paper in enumerate(dataset.get("papers", [])):
        for review_index, review in enumerate(paper.get("reviews", [])):
            records.append(
                {
                    "paper_id": paper.get("paper_id") or review.get("paper_id") or "",
                    "paper_title": paper.get("title", ""),
                    "venue": paper.get("venue", ""),
                    "year": paper.get("year"),
                    "paper_index": paper_index,
                    "review_index": review_index,
                    "review_id": review.get("review_id") or f"paper-{paper_index}-review-{review_index}",
                    "review": review,
                }
            )
    return records


def empty_source_locator() -> dict[str, Any]:
    return {
        "char_start": None,
        "char_end": None,
        "paragraph_index": None,
        "bullet_index": None,
        "line_start": None,
        "line_end": None,
        "sentence_index": None,
        "match_strategy": "none",
    }


def rate_stats(stats: dict[str, Any]) -> dict[str, float]:
    final_claim_count = stats["final_claim_count"]
    raw_candidate_count = stats["raw_candidate_count"]
    return {
        "raw_grounding_pass_rate": safe_rate(stats["raw_grounding_pass_count"], raw_candidate_count),
        "raw_single_claim_valid_rate": safe_rate(stats["raw_single_claim_valid_count"], raw_candidate_count),
        "final_grounding_pass_rate": safe_rate(stats["final_grounding_pass_count"], final_claim_count),
        "source_field_valid_rate": safe_rate(stats["source_field_valid_count"], final_claim_count),
        "source_text_present_rate": safe_rate(stats["source_text_present_count"], final_claim_count),
        "source_span_found_rate": safe_rate(stats["source_span_found_count"], final_claim_count),
        "source_paragraph_found_rate": safe_rate(stats["source_paragraph_found_count"], final_claim_count),
        "source_bullet_found_rate": safe_rate(stats["source_bullet_found_count"], final_claim_count),
        "source_sentence_index_found_rate": safe_rate(stats["source_sentence_index_found_count"], final_claim_count),
        "review_no_claim_rate": safe_rate(stats["review_no_claim_count"], stats["review_count"]),
        "review_error_rate": safe_rate(stats["review_error_count"], stats["review_count"]),
    }


def validation_status(stats: dict[str, Any]) -> str:
    if stats["review_error_count"]:
        return "needs_attention"
    if stats["final_claim_count"] == 0:
        return "fail"
    if stats["final_grounding_pass_rate"] < P0_FINAL_GROUNDING_TARGET:
        return "fail"
    if stats["source_field_valid_rate"] < SOURCE_FIELD_VALID_TARGET:
        return "fail"
    return "pass"


def write_grounding_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_grounding_markdown(report), encoding="utf-8")


def render_grounding_markdown(report: dict[str, Any]) -> str:
    stats = report["stats"]
    lines = [
        "# Grounding Validation Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Dataset: `{report['dataset'].get('name', '')}`",
        f"- Model: `{report['model']}`",
        f"- Reviews checked: {stats['review_count']}",
        f"- Final claims checked: {stats['final_claim_count']}",
        "",
        "## Core Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Final grounding pass rate | {format_rate(stats['final_grounding_pass_rate'])} |",
        f"| Source field valid rate | {format_rate(stats['source_field_valid_rate'])} |",
        f"| Source text present rate | {format_rate(stats['source_text_present_rate'])} |",
        f"| Source char span found rate | {format_rate(stats['source_span_found_rate'])} |",
        f"| Source paragraph locator found rate | {format_rate(stats['source_paragraph_found_rate'])} |",
        f"| Source bullet locator found rate | {format_rate(stats['source_bullet_found_rate'])} |",
        f"| Legacy source sentence index found rate | {format_rate(stats['source_sentence_index_found_rate'])} |",
        f"| Raw candidate grounding pass rate | {format_rate(stats['raw_grounding_pass_rate'])} |",
        f"| Reviews with no accepted claims | {stats['review_no_claim_count']} ({format_rate(stats['review_no_claim_rate'])}) |",
        f"| Review extraction errors | {stats['review_error_count']} ({format_rate(stats['review_error_rate'])}) |",
        "",
        "## Source Fields",
        "",
        "| Source field | Claims |",
        "| --- | ---: |",
    ]
    for field, count in sorted(stats.get("source_field_counts", {}).items()):
        lines.append(f"| `{field}` | {count} |")

    lines.extend(
        [
            "",
            "## Raw Grounding Failures",
            "",
        ]
    )
    raw_examples = report["examples"].get("raw_grounding_failures", [])
    if raw_examples:
        for example in raw_examples[:10]:
            lines.extend(render_example(example))
    else:
        lines.append("No raw grounding failures in the sampled candidate claims.")

    lines.extend(
        [
            "",
            "## Final Claim Failures",
            "",
        ]
    )
    final_examples = report["examples"].get("final_grounding_failures", [])
    if final_examples:
        for example in final_examples[:10]:
            lines.extend(render_example(example))
    else:
        lines.append("No final accepted claim grounding failures.")

    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    warnings = report["examples"].get("warnings", [])
    if warnings:
        for example in warnings[:10]:
            lines.extend(render_example(example))
    else:
        lines.append("No warning examples in the sampled accepted claims.")
    lines.append("")
    return "\n".join(lines)


def render_example(example: dict[str, Any]) -> list[str]:
    reasons = ", ".join(example.get("failure_reasons") or example.get("warnings") or [])
    locator = example_locator_text(example)
    return [
        f"- `{example.get('review_id', '')}` / `{example.get('paper_id', '')}`"
        + (f" ({reasons})" if reasons else ""),
        f"  - Claim: {example.get('claim_text', '')}",
        f"  - Source: `{example.get('source_field', '')}` - {example.get('source_sentence', '')}",
        f"  - Locator: {locator}",
    ]


def example_locator_text(example: dict[str, Any]) -> str:
    char_start = example.get("source_char_start")
    char_end = example.get("source_char_end")
    paragraph_index = example.get("source_paragraph_index")
    bullet_index = example.get("source_bullet_index")
    parts = []
    if char_start is not None and char_end is not None:
        parts.append(f"chars {char_start}-{char_end}")
    if paragraph_index is not None:
        parts.append(f"paragraph {int(paragraph_index) + 1}")
    if bullet_index is not None:
        parts.append(f"bullet {int(bullet_index) + 1}")
    return ", ".join(parts) if parts else "not located"


def example_from_record(record: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": record.get("paper_id", ""),
        "paper_title": truncate(record.get("paper_title", ""), 180),
        "review_id": record.get("review_id", ""),
        "claim_text": claim.get("claim_text", ""),
        "source_field": claim.get("source_field", ""),
        "source_sentence": claim.get("source_sentence", ""),
        "source_locator": claim.get("source_locator", {}),
        "source_char_start": claim.get("source_char_start"),
        "source_char_end": claim.get("source_char_end"),
        "source_paragraph_index": claim.get("source_paragraph_index"),
        "source_bullet_index": claim.get("source_bullet_index"),
        "failure_reasons": claim.get("failure_reasons", []),
        "warnings": claim.get("warnings", []),
        "grounding_pass": claim.get("grounding_pass"),
    }


def source_excerpt(source_text: str, source_sentence: str, *, limit: int = 360) -> str:
    if not source_text:
        return ""
    locator = source_locator({"source": source_text}, "source", source_sentence)
    char_start = locator.get("char_start")
    char_end = locator.get("char_end")
    if char_start is not None and char_end is not None:
        start = max(0, char_start - 80)
        end = min(len(source_text), char_end + 80)
        return truncate(source_text[start:end], limit)
    return truncate(source_text, limit)


def claim_source_token_overlap(claim_text: str, source_sentence: str) -> float:
    claim_tokens = content_tokens(claim_text)
    if not claim_tokens:
        return 0.0
    source_tokens = content_tokens(source_sentence)
    if not source_tokens:
        return 0.0
    return len(claim_tokens & source_tokens) / len(claim_tokens)


def content_tokens(text: str) -> set[str]:
    tokens = []
    for token in clean_text(text).lower().replace("-", " ").split():
        token = "".join(char for char in token if char.isalnum())
        if len(token) < 3 or token in TOKEN_STOPWORDS:
            continue
        tokens.append(token)
    return set(tokens)


def safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def format_rate(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def truncate(text: Any, limit: int) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
