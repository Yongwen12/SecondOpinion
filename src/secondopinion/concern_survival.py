from __future__ import annotations

import math
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .claim_extraction import DEFAULT_CLAIM_MODEL, StructuredLLMClient, extract_claims
from .data_inventory import classify_reply
from .normalize import get_replies, normalize_review
from .snapshot import load_snapshot_notes, read_json
from .text import clean_text, text_from_content


CONCERN_SURVIVAL_VERSION = "concern-survival-meta-review-v0.1"
CONCERN_SURVIVAL_CALIBRATION_VERSION = "concern-survival-calibration-v0.1"
SURVIVED_THRESHOLD = 0.34
PARTIAL_THRESHOLD = 0.2

SURVIVAL_LABELS = ("survived", "partial", "not_found")
SURVIVAL_CALIBRATION_LABELS = (*SURVIVAL_LABELS, "unsure")

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
    "how",
    "in",
    "is",
    "it",
    "its",
    "may",
    "might",
    "of",
    "on",
    "or",
    "paper",
    "review",
    "reviewer",
    "submission",
    "that",
    "the",
    "their",
    "there",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "whether",
    "which",
    "with",
    "would",
}

TOKEN_SYNONYMS = {
    "ablations": "ablation",
    "baselines": "baseline",
    "benchmarks": "benchmark",
    "clarify": "clear",
    "clarity": "clear",
    "comparison": "compare",
    "comparisons": "compare",
    "contribution": "contribute",
    "contributions": "contribute",
    "datasets": "dataset",
    "demonstrates": "demonstrate",
    "evaluation": "evaluate",
    "evaluations": "evaluate",
    "experiments": "experiment",
    "generality": "generalize",
    "generalization": "generalize",
    "limitations": "limitation",
    "limited": "limitation",
    "methodological": "method",
    "methodology": "method",
    "methods": "method",
    "missing": "lack",
    "novel": "novelty",
    "original": "novelty",
    "originality": "novelty",
    "results": "result",
    "unclear": "clear",
}


def validate_concern_survival_for_snapshot(
    snapshot_dir: str | Path,
    *,
    llm_client: StructuredLLMClient,
    model: str = DEFAULT_CLAIM_MODEL,
    paper_limit: int | None = None,
    review_limit: int | None = None,
    max_claims: int = 8,
    survived_threshold: float = SURVIVED_THRESHOLD,
    partial_threshold: float = PARTIAL_THRESHOLD,
) -> dict[str, Any]:
    snapshot_dir = Path(snapshot_dir)
    manifest = read_json(snapshot_dir / "manifest.json")
    notes = load_snapshot_notes(snapshot_dir)
    if paper_limit is not None:
        notes = notes[: max(0, paper_limit)]

    papers = []
    claim_counter = 0
    review_counter = 0
    for note in notes:
        paper = validate_paper_concern_survival(
            note,
            llm_client=llm_client,
            model=model,
            max_claims=max_claims,
            review_limit=None if review_limit is None else max(0, review_limit - review_counter),
            survived_threshold=survived_threshold,
            partial_threshold=partial_threshold,
        )
        review_counter += paper["review_count_evaluated"]
        claim_counter += paper["claim_count"]
        papers.append(paper)
        if review_limit is not None and review_counter >= review_limit:
            break

    return build_concern_survival_report(
        papers,
        snapshot={
            "snapshot_dir": str(snapshot_dir),
            "snapshot_id": manifest.get("snapshot_id", ""),
            "source": manifest.get("source", ""),
            "venue": manifest.get("venue", ""),
            "year": manifest.get("year"),
        },
        model=model,
        thresholds={
            "survived": survived_threshold,
            "partial": partial_threshold,
        },
    )


def validate_paper_concern_survival(
    note: dict[str, Any],
    *,
    llm_client: StructuredLLMClient,
    model: str,
    max_claims: int,
    review_limit: int | None,
    survived_threshold: float,
    partial_threshold: float,
) -> dict[str, Any]:
    paper_id = str(note.get("id") or note.get("forum") or "")
    content = note.get("content") or {}
    replies = get_replies(note)
    classified = [classify_reply(reply) for reply in replies]
    meta_text = "\n\n".join(item["text"] for item in classified if item["type"] == "meta_review" and item["text"])
    decision = first_non_empty(item["decision"] for item in classified if item["type"] == "decision")
    review_replies = [
        reply
        for reply in replies
        if any(item["id"] == str(reply.get("id") or "") and item["type"] == "official_review" for item in classified)
    ]
    if review_limit is not None:
        review_replies = review_replies[:review_limit]

    meta_segments = split_meta_review_segments(meta_text)
    decision_label = classify_decision(decision)
    if not meta_text or not review_replies:
        return {
            "paper_id": paper_id,
            "forum_id": str(note.get("forum") or paper_id),
            "title": text_from_content(content, ["title"]),
            "decision": decision or "Unknown",
            "decision_label": decision_label,
            "has_meta_review": bool(meta_text),
            "meta_review_text": meta_text,
            "meta_review_segments": meta_segments,
            "review_count_available": len(review_replies),
            "review_count_evaluated": 0,
            "claim_count": 0,
            "extraction_error_count": 0,
            "survival_counts": {},
            "strict_survival_rate": 0.0,
            "loose_survival_rate": 0.0,
            "reviews": [],
        }

    review_results = []
    extraction_error_count = 0
    for reply in review_replies:
        review = normalize_review(reply, paper_id, snapshot_time="")
        try:
            extracted_claims = extract_claims(review, llm_client=llm_client, model=model, max_claims=max_claims)
        except Exception as exc:  # noqa: BLE001 - report extraction failures without aborting the run.
            extraction_error_count += 1
            review_results.append(
                {
                    "review_id": str(reply.get("id") or ""),
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "claims": [],
                }
            )
            continue

        claims = [claim for claim in extracted_claims if is_concern_claim(claim)]
        claim_results = []
        for claim in claims:
            claim_results.append(
                score_claim_survival(
                    claim,
                    meta_segments,
                    survived_threshold=survived_threshold,
                    partial_threshold=partial_threshold,
                )
            )
        review_results.append(
            {
                "review_id": review["review_id"],
                "status": "ok",
                "rating_raw": review.get("rating_raw", ""),
                "rating_normalized": review.get("rating_normalized"),
                "confidence_raw": review.get("confidence_raw", ""),
                "confidence_normalized": review.get("confidence_normalized"),
                "extracted_claim_count": len(extracted_claims),
                "dropped_non_concern_claim_count": len(extracted_claims) - len(claims),
                "claim_count": len(claim_results),
                "claims": claim_results,
            }
        )

    claim_count = sum(len(review.get("claims", [])) for review in review_results)
    dropped_non_concern_claim_count = sum(review.get("dropped_non_concern_claim_count", 0) for review in review_results)
    label_counts = Counter(
        claim["survival_label"]
        for review in review_results
        for claim in review.get("claims", [])
    )
    return {
        "paper_id": paper_id,
        "forum_id": str(note.get("forum") or paper_id),
        "title": text_from_content(content, ["title"]),
        "decision": decision or "Unknown",
        "decision_label": decision_label,
        "has_meta_review": bool(meta_text),
        "meta_review_text": meta_text,
        "meta_review_segments": meta_segments,
        "review_count_available": len(review_replies),
        "review_count_evaluated": len(review_results),
        "claim_count": claim_count,
        "dropped_non_concern_claim_count": dropped_non_concern_claim_count,
        "extraction_error_count": extraction_error_count,
        "survival_counts": dict(label_counts),
        "strict_survival_rate": safe_rate(label_counts.get("survived", 0), claim_count),
        "loose_survival_rate": safe_rate(label_counts.get("survived", 0) + label_counts.get("partial", 0), claim_count),
        "reviews": review_results,
    }


def score_claim_survival(
    claim: dict[str, Any],
    meta_segments: list[str],
    *,
    survived_threshold: float,
    partial_threshold: float,
) -> dict[str, Any]:
    best = best_meta_match(claim, meta_segments)
    label = survival_label(best["score"], survived_threshold=survived_threshold, partial_threshold=partial_threshold)
    return {
        "claim_text": claim.get("claim_text", ""),
        "claim_type": claim.get("claim_type", ""),
        "importance": claim.get("importance", ""),
        "source_field": claim.get("source_field", ""),
        "source_sentence": claim.get("source_sentence", ""),
        "source_locator": claim.get("source_locator", {}),
        "survival_label": label,
        "survival_score": round(best["score"], 4),
        "matched_meta_segment": best["segment"],
        "matched_terms": best["matched_terms"],
        "match_basis": best["basis"],
    }


def is_concern_claim(claim: dict[str, Any]) -> bool:
    source_field = clean_text(claim.get("source_field")).lower()
    if source_field in {"weaknesses", "questions"}:
        return True
    if source_field == "review_text":
        text = clean_text(f"{claim.get('claim_text', '')} {claim.get('source_sentence', '')}").lower()
        return has_concern_cue(text)
    return False


def has_concern_cue(text: str) -> bool:
    cues = (
        "?",
        "concern",
        "lack",
        "missing",
        "unclear",
        "weak",
        "limited",
        "limitation",
        "insufficient",
        "not clear",
        "not enough",
        "does not",
        "do not",
        "cannot",
        "should",
        "need",
        "needs",
        "recommend",
        "suggest",
        "improve",
        "clarify",
        "question",
    )
    return any(cue in text for cue in cues)


def best_meta_match(claim: dict[str, Any], meta_segments: list[str]) -> dict[str, Any]:
    if not meta_segments:
        return {"score": 0.0, "segment": "", "matched_terms": [], "basis": "no_meta_review"}

    queries = [
        ("claim_text", clean_text(claim.get("claim_text"))),
        ("source_sentence", clean_text(claim.get("source_sentence"))),
        ("claim_plus_type", f"{claim.get('claim_text', '')} {claim.get('claim_type', '')}"),
    ]
    best = {"score": 0.0, "segment": "", "matched_terms": [], "basis": ""}
    for basis, query in queries:
        query_tokens = concern_tokens(query)
        if not query_tokens:
            continue
        for segment in meta_segments:
            segment_tokens = concern_tokens(segment)
            score, matched_terms = overlap_score(query_tokens, segment_tokens)
            if score > best["score"]:
                best = {
                    "score": score,
                    "segment": segment,
                    "matched_terms": sorted(matched_terms),
                    "basis": basis,
                }
    return best


def overlap_score(query_tokens: set[str], segment_tokens: set[str]) -> tuple[float, set[str]]:
    if not query_tokens or not segment_tokens:
        return 0.0, set()
    matched = query_tokens & segment_tokens
    if not matched:
        return 0.0, set()
    coverage = len(matched) / len(query_tokens)
    cosine = len(matched) / math.sqrt(len(query_tokens) * len(segment_tokens))
    anchor_bonus = 0.08 if matched & anchor_terms() else 0.0
    return min(1.0, 0.68 * coverage + 0.32 * cosine + anchor_bonus), matched


def survival_label(score: float, *, survived_threshold: float, partial_threshold: float) -> str:
    if score >= survived_threshold:
        return "survived"
    if score >= partial_threshold:
        return "partial"
    return "not_found"


def split_meta_review_segments(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    rough_segments = []
    for paragraph in re.split(r"\n{2,}", text):
        paragraph = clean_text(paragraph)
        if not paragraph:
            continue
        pieces = re.split(r"(?<=[.!?])\s+|\n+|;\s+", paragraph)
        for piece in pieces:
            piece = clean_text(piece.strip(" -*\t"))
            if len(piece) >= 20:
                rough_segments.append(piece)
    if not rough_segments and text:
        rough_segments.append(text)
    return rough_segments


def concern_tokens(text: str) -> set[str]:
    tokens = set()
    for raw in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", clean_text(text).lower()):
        token = raw.replace("-", "")
        token = stem_token(TOKEN_SYNONYMS.get(token, token))
        token = TOKEN_SYNONYMS.get(token, token)
        if len(token) < 3 or token in TOKEN_STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def stem_token(token: str) -> str:
    if token.endswith("ing") and len(token) > 6:
        return token[:-3]
    if token.endswith("ed") and len(token) > 5:
        return token[:-2]
    if token.endswith("s") and len(token) > 5:
        return token[:-1]
    return token


def anchor_terms() -> set[str]:
    return {
        "ablation",
        "baseline",
        "benchmark",
        "clear",
        "compare",
        "dataset",
        "evaluate",
        "experiment",
        "generalize",
        "lack",
        "limitation",
        "method",
        "novelty",
        "result",
        "theory",
    }


def build_concern_survival_report(
    papers: list[dict[str, Any]],
    *,
    snapshot: dict[str, Any],
    model: str,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    paper_count = len(papers)
    evaluable_papers = [paper for paper in papers if paper.get("has_meta_review") and paper.get("claim_count")]
    label_counts: Counter[str] = Counter()
    claim_type_counts: Counter[str] = Counter()
    claim_type_survived_counts: Counter[str] = Counter()
    importance_counts: Counter[str] = Counter()
    importance_survived_counts: Counter[str] = Counter()
    examples = {label: [] for label in SURVIVAL_LABELS}
    for paper in papers:
        for review in paper.get("reviews", []):
            for claim in review.get("claims", []):
                label = claim["survival_label"]
                label_counts[label] += 1
                claim_type = claim.get("claim_type") or "unknown"
                importance = claim.get("importance") or "unknown"
                claim_type_counts[claim_type] += 1
                importance_counts[importance] += 1
                if label in {"survived", "partial"}:
                    claim_type_survived_counts[claim_type] += 1
                    importance_survived_counts[importance] += 1
                if len(examples[label]) < 12:
                    examples[label].append(example_from_claim(paper, review, claim))

    claim_count = sum(label_counts.values())
    return {
        "schema_version": "0.1",
        "survival_version": CONCERN_SURVIVAL_VERSION,
        "claim_model": model,
        "thresholds": thresholds,
        "snapshot": snapshot,
        "summary": {
            "paper_count": paper_count,
            "paper_with_meta_review_count": sum(1 for paper in papers if paper.get("has_meta_review")),
            "evaluable_paper_count": len(evaluable_papers),
            "review_count_evaluated": sum(paper.get("review_count_evaluated", 0) for paper in papers),
            "claim_count": claim_count,
            "dropped_non_concern_claim_count": sum(paper.get("dropped_non_concern_claim_count", 0) for paper in papers),
            "extraction_error_count": sum(paper.get("extraction_error_count", 0) for paper in papers),
            "survival_counts": {label: label_counts.get(label, 0) for label in SURVIVAL_LABELS},
            "strict_survival_rate": safe_rate(label_counts.get("survived", 0), claim_count),
            "loose_survival_rate": safe_rate(label_counts.get("survived", 0) + label_counts.get("partial", 0), claim_count),
            "by_claim_type": rate_breakdown(claim_type_counts, claim_type_survived_counts),
            "by_importance": rate_breakdown(importance_counts, importance_survived_counts),
            "by_decision": decision_breakdown(papers),
        },
        "examples": examples,
        "papers": papers,
    }


def rate_breakdown(total_counts: Counter[str], survived_counts: Counter[str]) -> dict[str, dict[str, float | int]]:
    return {
        key: {
            "claim_count": total_counts[key],
            "loose_survival_count": survived_counts.get(key, 0),
            "loose_survival_rate": safe_rate(survived_counts.get(key, 0), total_counts[key]),
        }
        for key in sorted(total_counts)
    }


def decision_breakdown(papers: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    total_counts: Counter[str] = Counter()
    survived_counts: Counter[str] = Counter()
    paper_counts: Counter[str] = Counter()
    for paper in papers:
        decision_label = paper.get("decision_label") or classify_decision(paper.get("decision", ""))
        paper_counts[decision_label] += 1
        for review in paper.get("reviews", []):
            for claim in review.get("claims", []):
                total_counts[decision_label] += 1
                if claim.get("survival_label") in {"survived", "partial"}:
                    survived_counts[decision_label] += 1
    return {
        key: {
            "paper_count": paper_counts.get(key, 0),
            "claim_count": total_counts[key],
            "loose_survival_count": survived_counts.get(key, 0),
            "loose_survival_rate": safe_rate(survived_counts.get(key, 0), total_counts[key]),
        }
        for key in sorted(total_counts)
    }


def example_from_claim(paper: dict[str, Any], review: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": paper.get("paper_id", ""),
        "title": truncate(paper.get("title", ""), 160),
        "decision": paper.get("decision", ""),
        "review_id": review.get("review_id", ""),
        "claim_text": claim.get("claim_text", ""),
        "claim_type": claim.get("claim_type", ""),
        "importance": claim.get("importance", ""),
        "survival_label": claim.get("survival_label", ""),
        "survival_score": claim.get("survival_score", 0.0),
        "matched_meta_segment": truncate(claim.get("matched_meta_segment", ""), 500),
        "matched_terms": claim.get("matched_terms", []),
    }


def build_concern_survival_calibration_sample(
    report: dict[str, Any],
    *,
    sample_size: int = 100,
    seed: int = 7,
) -> dict[str, Any]:
    records = list(iter_concern_survival_records(report))
    requested_sample_size = max(0, sample_size)
    bounded_sample_size = min(requested_sample_size, len(records))
    sampled = balanced_sample(records, sample_size=bounded_sample_size, seed=seed)
    return {
        "schema_version": "0.1",
        "calibration_version": CONCERN_SURVIVAL_CALIBRATION_VERSION,
        "source_survival_version": report.get("survival_version", ""),
        "snapshot": report.get("snapshot", {}),
        "sample_size_requested": requested_sample_size,
        "sample_size": len(sampled),
        "seed": seed,
        "sampling_strategy": "balanced_by_auto_survival_label",
        "label_options": {
            "human_survival_label": list(SURVIVAL_CALIBRATION_LABELS),
            "human_concern_quality": ["high", "medium", "low", "unsure"],
        },
        "label_guidance": {
            "survived": "The meta-review substantively repeats, endorses, or relies on this reviewer concern.",
            "partial": "The meta-review discusses the same broad issue but loses important specificity.",
            "not_found": "The meta-review does not mention this concern in a meaningful way.",
            "unsure": "The pair is ambiguous or needs more context before labeling.",
        },
        "summary": {
            "candidate_count": len(records),
            "sample_auto_label_counts": dict(Counter(item["auto_survival_label"] for item in sampled)),
            "sample_decision_counts": dict(Counter(item["decision_label"] for item in sampled)),
        },
        "items": sampled,
    }


def iter_concern_survival_records(report: dict[str, Any]):
    for paper in report.get("papers", []):
        paper_id = paper.get("paper_id", "")
        decision = paper.get("decision", "")
        decision_label = paper.get("decision_label") or classify_decision(decision)
        for review in paper.get("reviews", []):
            review_id = review.get("review_id", "")
            for claim_index, claim in enumerate(review.get("claims", [])):
                yield {
                    "task_id": f"{paper_id}:{review_id}:{claim_index}",
                    "paper_id": paper_id,
                    "forum_id": paper.get("forum_id", paper_id),
                    "title": paper.get("title", ""),
                    "decision": decision,
                    "decision_label": decision_label,
                    "review_id": review_id,
                    "review_rating_raw": review.get("rating_raw", ""),
                    "review_rating_normalized": review.get("rating_normalized"),
                    "review_confidence_raw": review.get("confidence_raw", ""),
                    "review_confidence_normalized": review.get("confidence_normalized"),
                    "claim_index": claim_index,
                    "claim_text": claim.get("claim_text", ""),
                    "claim_type": claim.get("claim_type", ""),
                    "importance": claim.get("importance", ""),
                    "source_field": claim.get("source_field", ""),
                    "source_sentence": claim.get("source_sentence", ""),
                    "source_locator": claim.get("source_locator", {}),
                    "meta_review_text": paper.get("meta_review_text", ""),
                    "matched_meta_segment": claim.get("matched_meta_segment", ""),
                    "matched_terms": claim.get("matched_terms", []),
                    "match_basis": claim.get("match_basis", ""),
                    "auto_survival_label": claim.get("survival_label", ""),
                    "auto_survival_score": claim.get("survival_score", 0.0),
                    "human_survival_label": "",
                    "human_concern_quality": "",
                    "human_notes": "",
                }


def balanced_sample(records: list[dict[str, Any]], *, sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size <= 0 or not records:
        return []
    rng = random.Random(seed)
    grouped: dict[str, list[dict[str, Any]]] = {label: [] for label in SURVIVAL_LABELS}
    extras = []
    for record in records:
        label = record.get("auto_survival_label", "")
        if label in grouped:
            grouped[label].append(record)
        else:
            extras.append(record)

    selected = []
    leftovers = []
    labels = [label for label in SURVIVAL_LABELS if grouped[label]]
    if not labels:
        labels = ["extras"]
        grouped["extras"] = extras
        extras = []

    base = sample_size // len(labels)
    remainder = sample_size % len(labels)
    for index, label in enumerate(labels):
        items = list(grouped[label])
        rng.shuffle(items)
        target = base + (1 if index < remainder else 0)
        selected.extend(items[:target])
        leftovers.extend(items[target:])
    leftovers.extend(extras)
    rng.shuffle(leftovers)
    selected.extend(leftovers[: max(0, sample_size - len(selected))])
    selected = selected[:sample_size]
    rng.shuffle(selected)
    return selected


def write_concern_survival_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_concern_survival_markdown(report), encoding="utf-8")


def write_concern_survival_calibration_jsonl(calibration: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for item in calibration.get("items", []):
            handle.write(json_dumps(item))
            handle.write("\n")


def write_concern_survival_calibration_markdown(calibration: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_concern_survival_calibration_markdown(calibration), encoding="utf-8")


def render_concern_survival_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Concern Survival Via Meta-Review",
        "",
        f"- Snapshot: `{report['snapshot'].get('snapshot_id', '')}`",
        f"- Model: `{report['claim_model']}`",
        f"- Evaluable papers: {summary['evaluable_paper_count']}",
        f"- Reviews evaluated: {summary['review_count_evaluated']}",
        f"- Claims evaluated: {summary['claim_count']}",
        f"- Dropped non-concern claims: {summary['dropped_non_concern_claim_count']}",
        f"- Extraction errors: {summary['extraction_error_count']}",
        "",
        "## Core Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Strict survival rate | {format_rate(summary['strict_survival_rate'])} |",
        f"| Loose survival rate | {format_rate(summary['loose_survival_rate'])} |",
        f"| Survived claims | {summary['survival_counts'].get('survived', 0)} |",
        f"| Partial claims | {summary['survival_counts'].get('partial', 0)} |",
        f"| Not found claims | {summary['survival_counts'].get('not_found', 0)} |",
        "",
        "## By Claim Type",
        "",
        "| Claim type | Claims | Loose survived | Rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for claim_type, item in summary["by_claim_type"].items():
        lines.append(
            f"| `{claim_type}` | {item['claim_count']} | {item['loose_survival_count']} | {format_rate(item['loose_survival_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## By Decision",
            "",
            "| Decision | Papers | Claims | Loose survived | Rate |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for decision, item in summary.get("by_decision", {}).items():
        lines.append(
            f"| `{decision}` | {item['paper_count']} | {item['claim_count']} | "
            f"{item['loose_survival_count']} | {format_rate(item['loose_survival_rate'])} |"
        )

    lines.extend(["", "## Examples", ""])
    for label in SURVIVAL_LABELS:
        lines.append(f"### {label}")
        examples = report["examples"].get(label, [])
        if not examples:
            lines.append("")
            lines.append("No examples.")
            lines.append("")
            continue
        for example in examples[:8]:
            lines.append(
                f"- `{example['paper_id']}` / `{example['review_id']}` "
                f"score={example['survival_score']:.3f} type=`{example['claim_type']}`"
            )
            lines.append(f"  - Claim: {example['claim_text']}")
            lines.append(f"  - Meta-review match: {example['matched_meta_segment'] or 'No match'}")
        lines.append("")
    return "\n".join(lines)


def render_concern_survival_calibration_markdown(calibration: dict[str, Any]) -> str:
    summary = calibration.get("summary", {})
    lines = [
        "# Concern Survival Calibration Sample",
        "",
        f"- Version: `{calibration.get('calibration_version', '')}`",
        f"- Source survival version: `{calibration.get('source_survival_version', '')}`",
        f"- Sample size: {calibration.get('sample_size', 0)}",
        f"- Candidate count: {summary.get('candidate_count', 0)}",
        f"- Seed: {calibration.get('seed', '')}",
        f"- Strategy: `{calibration.get('sampling_strategy', '')}`",
        "",
        "## Label Guidance",
        "",
    ]
    for label, guidance in calibration.get("label_guidance", {}).items():
        lines.append(f"- `{label}`: {guidance}")

    lines.extend(
        [
            "",
            "## Sample Counts",
            "",
            "| Auto label | Items |",
            "| --- | ---: |",
        ]
    )
    for label, count in sorted(summary.get("sample_auto_label_counts", {}).items()):
        lines.append(f"| `{label}` | {count} |")

    lines.extend(["", "## Items", ""])
    for item in calibration.get("items", []):
        lines.append(
            f"### {item['task_id']} auto=`{item['auto_survival_label']}` "
            f"score={item['auto_survival_score']:.3f} decision=`{item['decision_label']}`"
        )
        lines.append(f"- Claim: {item['claim_text']}")
        lines.append(f"- Source: {item['source_sentence']}")
        lines.append(f"- Matched meta-review segment: {item['matched_meta_segment'] or 'No match'}")
        lines.append("- Human survival label: ")
        lines.append("- Human concern quality: ")
        lines.append("- Notes: ")
        lines.append("")
    return "\n".join(lines)


def first_non_empty(values: Any) -> str:
    for value in values:
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return ""


def classify_decision(decision: Any) -> str:
    text = clean_text(decision).lower()
    if not text:
        return "unknown"
    if "reject" in text:
        return "reject"
    if "accept" in text or "spotlight" in text or "oral" in text:
        return "accept"
    return "other"


def safe_rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def format_rate(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def truncate(text: Any, limit: int) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)
