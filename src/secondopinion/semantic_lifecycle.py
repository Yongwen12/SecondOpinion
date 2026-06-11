from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

from .concern_calibration import normalized_calibration_record
from .lifecycle_ablation import (
    WEIGHTS,
    bounded_float,
    discussion_score,
    has_llm_consensus,
    has_llm_rebuttal,
    lifecycle_label,
    llm_consensus_score,
    llm_rebuttal_robustness_score,
    proxy_consensus_score,
    proxy_rebuttal_robustness_score,
)


SEMANTIC_LIFECYCLE_VERSION = "semantic-meta-lifecycle-v0.1"
SEMANTIC_META_LABELS = ("survived", "partial", "not_found")


def build_semantic_lifecycle_report(
    calibration_report: dict[str, Any],
    semantic_meta_records: list[dict[str, Any]],
) -> dict[str, Any]:
    semantic_by_key = index_semantic_meta_records(semantic_meta_records)
    records = list(iter_claim_records(calibration_report, semantic_by_key))
    current_rows = [score_record(record, semantic_meta_mode="proxy") for record in records]
    semantic_hybrid_rows = [score_record(record, semantic_meta_mode="hybrid") for record in records]
    semantic_labeled_rows = [
        score_record(record, semantic_meta_mode="semantic_only")
        for record in records
        if record.get("semantic_meta_label") in SEMANTIC_META_LABELS
    ]
    high_conf_rows = [
        score_record(record, semantic_meta_mode="semantic_only")
        for record in records
        if record.get("semantic_meta_label") in SEMANTIC_META_LABELS and record.get("semantic_high_confidence")
    ]
    return {
        "schema_version": SEMANTIC_LIFECYCLE_VERSION,
        "source": {
            "calibration_version": calibration_report.get("calibration_version", ""),
            "semantic_meta_record_count": len(semantic_meta_records),
        },
        "summary": {
            "claim_count": len(records),
            "semantic_meta_matched_count": sum(1 for record in records if record.get("semantic_meta_record")),
            "semantic_meta_decisive_count": sum(1 for record in records if record.get("semantic_meta_label") in SEMANTIC_META_LABELS),
            "semantic_meta_high_confidence_count": sum(
                1
                for record in records
                if record.get("semantic_meta_label") in SEMANTIC_META_LABELS and record.get("semantic_high_confidence")
            ),
            "semantic_meta_label_counts": dict(Counter(record.get("semantic_meta_label", "") for record in records if record.get("semantic_meta_record"))),
            "proxy_meta_label_counts_on_semantic_records": dict(
                Counter(record.get("proxy_meta_label", "") for record in records if record.get("semantic_meta_record"))
            ),
            "semantic_proxy_agreement_rate": semantic_proxy_agreement_rate(records),
        },
        "modes": {
            "current_proxy_meta": summarize_rows(current_rows),
            "semantic_hybrid_meta": summarize_rows(semantic_hybrid_rows),
            "semantic_labeled_only": summarize_rows(semantic_labeled_rows),
            "semantic_high_confidence_only": summarize_rows(high_conf_rows),
        },
        "comparisons": {
            "semantic_hybrid_vs_current_all_claims": compare_rows(current_rows, semantic_hybrid_rows),
            "semantic_labeled_vs_current_subset": compare_rows(
                [row for row in current_rows if row["semantic_meta_label"] in SEMANTIC_META_LABELS],
                semantic_labeled_rows,
            ),
            "semantic_high_confidence_vs_current_subset": compare_rows(
                [row for row in current_rows if row["semantic_meta_label"] in SEMANTIC_META_LABELS and row["semantic_high_confidence"]],
                high_conf_rows,
            ),
        },
        "semantic_meta_diagnostics": semantic_meta_diagnostics(records),
        "notes": [
            "`current_proxy_meta` keeps the existing lexical meta-review uptake signal.",
            "`semantic_hybrid_meta` replaces meta-review uptake with LLM semantic labels when decisive; missing/unsure labels fall back to proxy.",
            "`semantic_labeled_only` reports only claims with decisive semantic meta-review labels.",
            "`semantic_high_confidence_only` is the strictest subset: decisive semantic labels marked high-confidence training candidates.",
            "Rebuttal and consensus still use the current hybrid LLM/proxy logic; this report isolates the meta-review uptake leg.",
        ],
    }


def apply_semantic_meta_to_calibration(
    calibration_report: dict[str, Any],
    semantic_meta_records: list[dict[str, Any]],
) -> dict[str, Any]:
    semantic_by_key = index_semantic_meta_records(semantic_meta_records)
    copied = copy.deepcopy(calibration_report)
    for paper in copied.get("papers", []):
        for review in paper.get("reviews", []):
            for claim_index, claim in enumerate(review.get("claims", [])):
                key = claim_key(paper.get("paper_id", ""), review.get("review_id", ""), claim_index)
                semantic = semantic_by_key.get(key)
                if not semantic:
                    continue
                label = semantic.get("llm_meta_review_match", "")
                if label not in (*SEMANTIC_META_LABELS, "unsure"):
                    continue
                claim.setdefault("meta_review_uptake", {})
                claim["meta_review_uptake"]["llm_calibration"] = {
                    "label_id": semantic.get("llm_label_id", ""),
                    "meta_review_match": label,
                    "ac_treatment": semantic.get("llm_ac_treatment", ""),
                    "concern_quality": semantic.get("llm_concern_quality", ""),
                    "confidence": semantic.get("llm_confidence", ""),
                    "label_evidence_strength": semantic.get("llm_label_evidence_strength", ""),
                    "training_use": semantic.get("llm_training_use", ""),
                    "rationale": semantic.get("llm_rationale", ""),
                    "high_confidence_training_candidate": bool(semantic.get("high_confidence_training_candidate")),
                }
                if label in SEMANTIC_META_LABELS:
                    claim["meta_review_uptake"]["proxy_label"] = claim["meta_review_uptake"].get("label", "")
                    claim["meta_review_uptake"]["proxy_score"] = claim["meta_review_uptake"].get("score", 0.0)
                    claim["meta_review_uptake"]["label"] = label
                    claim["meta_review_uptake"]["score"] = semantic_meta_score(label)
                    claim["lifecycle_robustness_semantic_meta"] = lifecycle_payload(claim, semantic_meta_label=label)
    copied["semantic_meta_lifecycle_version"] = SEMANTIC_LIFECYCLE_VERSION
    copied["semantic_meta_source"] = {
        "record_count": len(semantic_meta_records),
        "decisive_record_count": sum(
            1 for record in semantic_meta_records if normalized_calibration_record(record).get("llm_meta_review_match") in SEMANTIC_META_LABELS
        ),
    }
    return copied


def iter_claim_records(calibration_report: dict[str, Any], semantic_by_key: dict[str, dict[str, Any]]):
    for paper in calibration_report.get("papers", []):
        for review in paper.get("reviews", []):
            for claim_index, claim in enumerate(review.get("claims", [])):
                key = claim_key(paper.get("paper_id", ""), review.get("review_id", ""), claim_index)
                semantic = semantic_by_key.get(key)
                normalized = normalized_calibration_record(semantic) if semantic else {}
                yield {
                    "key": key,
                    "paper_id": paper.get("paper_id", ""),
                    "review_id": review.get("review_id", ""),
                    "claim_index": claim_index,
                    "claim": claim,
                    "proxy_meta_label": claim.get("meta_review_uptake", {}).get("label", ""),
                    "proxy_meta_score": claim.get("meta_review_uptake", {}).get("score", 0.0),
                    "semantic_meta_record": normalized,
                    "semantic_meta_label": normalized.get("llm_meta_review_match", ""),
                    "semantic_high_confidence": bool(normalized.get("high_confidence_training_candidate")),
                }


def score_record(record: dict[str, Any], *, semantic_meta_mode: str) -> dict[str, Any]:
    claim = record["claim"]
    consensus = llm_consensus_score(claim)
    if consensus is None:
        consensus = proxy_consensus_score(claim)
    rebuttal = llm_rebuttal_robustness_score(claim)
    if rebuttal is None:
        rebuttal = proxy_rebuttal_robustness_score(claim)

    meta = meta_score_for_record(record, semantic_meta_mode=semantic_meta_mode)
    signals = {
        "grounding": 1.0 if claim.get("grounded") else 0.0,
        "specificity": bounded_float(claim.get("specificity_score", 0.0)),
        "consensus": bounded_float(consensus),
        "rebuttal_robustness": bounded_float(rebuttal),
        "discussion_followup": discussion_score(claim),
        "meta_review_uptake": bounded_float(meta),
    }
    score = round(sum(WEIGHTS[key] * value for key, value in signals.items()), 4)
    return {
        "key": record["key"],
        "paper_id": record["paper_id"],
        "review_id": record["review_id"],
        "claim_index": record["claim_index"],
        "claim_text": claim.get("claim_text", ""),
        "proxy_meta_label": record.get("proxy_meta_label", ""),
        "semantic_meta_label": record.get("semantic_meta_label", ""),
        "semantic_high_confidence": record.get("semantic_high_confidence", False),
        "has_llm_rebuttal": has_llm_rebuttal(claim),
        "has_llm_consensus": has_llm_consensus(claim),
        "score": score,
        "label": lifecycle_label(score),
        "signals": {key: round(value, 4) for key, value in signals.items()},
    }


def meta_score_for_record(record: dict[str, Any], *, semantic_meta_mode: str) -> float:
    semantic_label = record.get("semantic_meta_label", "")
    if semantic_meta_mode in {"hybrid", "semantic_only"} and semantic_label in SEMANTIC_META_LABELS:
        return semantic_meta_score(semantic_label)
    return semantic_meta_score(record.get("proxy_meta_label", ""))


def lifecycle_payload(claim: dict[str, Any], *, semantic_meta_label: str) -> dict[str, Any]:
    consensus = llm_consensus_score(claim)
    if consensus is None:
        consensus = proxy_consensus_score(claim)
    rebuttal = llm_rebuttal_robustness_score(claim)
    if rebuttal is None:
        rebuttal = proxy_rebuttal_robustness_score(claim)
    signals = {
        "grounding": 1.0 if claim.get("grounded") else 0.0,
        "specificity": bounded_float(claim.get("specificity_score", 0.0)),
        "consensus": bounded_float(consensus),
        "rebuttal_robustness": bounded_float(rebuttal),
        "discussion_followup": discussion_score(claim),
        "meta_review_uptake": semantic_meta_score(semantic_meta_label),
    }
    score = round(sum(WEIGHTS[key] * value for key, value in signals.items()), 4)
    return {
        "score": score,
        "label": lifecycle_label(score),
        "signal_scores": {key: round(value, 4) for key, value in signals.items()},
        "source": "semantic_meta_review_uptake_when_available",
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row["score"] for row in rows]
    return {
        "claim_count": len(rows),
        "paper_count": len({row["paper_id"] for row in rows}),
        "review_count": len({(row["paper_id"], row["review_id"]) for row in rows}),
        "mean_lifecycle_robustness": round(mean(scores), 4),
        "median_lifecycle_robustness": round(median(scores), 4) if scores else 0.0,
        "label_counts": dict(Counter(row["label"] for row in rows)),
        "mean_meta_review_uptake": round(mean(row["signals"]["meta_review_uptake"] for row in rows), 4),
    }


def compare_rows(left_rows: list[dict[str, Any]], right_rows: list[dict[str, Any]]) -> dict[str, Any]:
    left_by_key = {row["key"]: row for row in left_rows}
    right_by_key = {row["key"]: row for row in right_rows}
    keys = sorted(set(left_by_key) & set(right_by_key))
    deltas = [right_by_key[key]["score"] - left_by_key[key]["score"] for key in keys]
    label_changes = Counter(
        f"{left_by_key[key]['label']}->{right_by_key[key]['label']}"
        for key in keys
        if left_by_key[key]["label"] != right_by_key[key]["label"]
    )
    return {
        "claim_count": len(keys),
        "mean_score_delta": round(mean(deltas), 4),
        "median_score_delta": round(median(deltas), 4) if deltas else 0.0,
        "mean_abs_score_delta": round(mean(abs(delta) for delta in deltas), 4),
        "mean_meta_review_uptake_delta": round(
            mean(right_by_key[key]["signals"]["meta_review_uptake"] - left_by_key[key]["signals"]["meta_review_uptake"] for key in keys),
            4,
        ),
        "label_change_count": sum(label_changes.values()),
        "label_change_rate": round(sum(label_changes.values()) / len(keys), 4) if keys else 0.0,
        "label_changes": dict(label_changes),
        "largest_drops": example_deltas(left_by_key, right_by_key, keys, reverse=False),
        "largest_gains": example_deltas(left_by_key, right_by_key, keys, reverse=True),
    }


def example_deltas(
    left_by_key: dict[str, dict[str, Any]],
    right_by_key: dict[str, dict[str, Any]],
    keys: list[str],
    *,
    reverse: bool,
    limit: int = 8,
) -> list[dict[str, Any]]:
    sorted_keys = sorted(
        keys,
        key=lambda key: right_by_key[key]["score"] - left_by_key[key]["score"],
        reverse=reverse,
    )
    examples = []
    for key in sorted_keys[:limit]:
        left = left_by_key[key]
        right = right_by_key[key]
        examples.append(
            {
                "key": key,
                "paper_id": left["paper_id"],
                "review_id": left["review_id"],
                "claim_text": left["claim_text"],
                "proxy_meta_label": left.get("proxy_meta_label", ""),
                "semantic_meta_label": right.get("semantic_meta_label", ""),
                "left_score": left["score"],
                "right_score": right["score"],
                "delta": round(right["score"] - left["score"], 4),
                "left_label": left["label"],
                "right_label": right["label"],
            }
        )
    return examples


def semantic_meta_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [record for record in records if record.get("semantic_meta_record")]
    decisive = [record for record in matched if record.get("semantic_meta_label") in SEMANTIC_META_LABELS]
    proxy_positive = [record for record in decisive if record.get("proxy_meta_label") in {"survived", "partial"}]
    semantic_positive = [record for record in decisive if record.get("semantic_meta_label") in {"survived", "partial"}]
    false_positive = [
        record
        for record in decisive
        if record.get("proxy_meta_label") in {"survived", "partial"} and record.get("semantic_meta_label") == "not_found"
    ]
    false_negative = [
        record
        for record in decisive
        if record.get("proxy_meta_label") == "not_found" and record.get("semantic_meta_label") in {"survived", "partial"}
    ]
    exact_agreement = [
        record
        for record in decisive
        if record.get("proxy_meta_label") == record.get("semantic_meta_label")
    ]
    return {
        "matched_record_count": len(matched),
        "decisive_record_count": len(decisive),
        "proxy_positive_rate": rate(len(proxy_positive), len(decisive)),
        "semantic_positive_rate": rate(len(semantic_positive), len(decisive)),
        "exact_agreement_rate": rate(len(exact_agreement), len(decisive)),
        "proxy_false_positive_count": len(false_positive),
        "proxy_false_positive_rate": rate(len(false_positive), len(proxy_positive)),
        "proxy_false_negative_count": len(false_negative),
        "proxy_false_negative_rate": rate(len(false_negative), len([record for record in decisive if record.get("proxy_meta_label") == "not_found"])),
        "semantic_label_counts": dict(Counter(record.get("semantic_meta_label", "") for record in matched)),
        "proxy_label_counts_on_matched": dict(Counter(record.get("proxy_meta_label", "") for record in matched)),
    }


def semantic_proxy_agreement_rate(records: list[dict[str, Any]]) -> float:
    decisive = [record for record in records if record.get("semantic_meta_label") in SEMANTIC_META_LABELS]
    if not decisive:
        return 0.0
    return round(
        sum(1 for record in decisive if record.get("semantic_meta_label") == record.get("proxy_meta_label")) / len(decisive),
        4,
    )


def index_semantic_meta_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed = {}
    for record in records:
        normalized = normalized_calibration_record(record)
        key = claim_key(normalized.get("paper_id", ""), normalized.get("review_id", ""), normalized.get("claim_index", 0))
        if not key.endswith("::0") and key not in indexed:
            indexed[key] = normalized
    return indexed


def claim_key(paper_id: str, review_id: str, claim_index: Any) -> str:
    try:
        index = int(claim_index)
    except (TypeError, ValueError):
        index = 0
    return f"{paper_id}:{review_id}:{index}"


def semantic_meta_score(label: str) -> float:
    return {"survived": 1.0, "partial": 0.60, "not_found": 0.0}.get(label, 0.0)


def mean(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(float(value) for value in items) / len(items)


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_semantic_lifecycle_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_semantic_lifecycle_markdown(report), encoding="utf-8")


def render_semantic_lifecycle_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Semantic Meta-Review Lifecycle Recalibration",
        "",
        "## Scope",
        "",
        f"- Claims: {summary.get('claim_count', 0)}",
        f"- Claims with semantic meta-review records: {summary.get('semantic_meta_matched_count', 0)}",
        f"- Claims with decisive semantic meta-review labels: {summary.get('semantic_meta_decisive_count', 0)}",
        f"- High-confidence decisive semantic labels: {summary.get('semantic_meta_high_confidence_count', 0)}",
        f"- Semantic/proxy exact agreement: {summary.get('semantic_proxy_agreement_rate', 0.0):.1%}",
        f"- Semantic label counts: `{json.dumps(summary.get('semantic_meta_label_counts', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- Proxy labels on semantic records: `{json.dumps(summary.get('proxy_meta_label_counts_on_semantic_records', {}), ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Mode Summary",
        "",
        "| Mode | Claims | Mean lifecycle | Median lifecycle | Mean meta uptake | High | Medium | Low |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode, item in report.get("modes", {}).items():
        counts = item.get("label_counts", {})
        lines.append(
            f"| `{mode}` | {item.get('claim_count', 0)} | {item.get('mean_lifecycle_robustness', 0.0):.1%} | "
            f"{item.get('median_lifecycle_robustness', 0.0):.1%} | {item.get('mean_meta_review_uptake', 0.0):.1%} | "
            f"{counts.get('high', 0)} | {counts.get('medium', 0)} | {counts.get('low', 0)} |"
        )
    lines.extend(["", "## Comparisons", ""])
    for name, comparison in report.get("comparisons", {}).items():
        lines.extend(
            [
                f"### `{name}`",
                "",
                f"- Claims compared: {comparison.get('claim_count', 0)}",
                f"- Mean score delta: {comparison.get('mean_score_delta', 0.0):+.1%}",
                f"- Mean absolute score delta: {comparison.get('mean_abs_score_delta', 0.0):.1%}",
                f"- Mean meta-review uptake delta: {comparison.get('mean_meta_review_uptake_delta', 0.0):+.1%}",
                f"- Label changes: {comparison.get('label_change_count', 0)} ({comparison.get('label_change_rate', 0.0):.1%})",
                f"- Label-change counts: `{json.dumps(comparison.get('label_changes', {}), sort_keys=True)}`",
                "",
            ]
        )
    diag = report.get("semantic_meta_diagnostics", {})
    lines.extend(
        [
            "## Semantic Meta-Review Diagnostics",
            "",
            f"- Matched records: {diag.get('matched_record_count', 0)}",
            f"- Decisive records: {diag.get('decisive_record_count', 0)}",
            f"- Proxy positive rate: {diag.get('proxy_positive_rate', 0.0):.1%}",
            f"- Semantic positive rate: {diag.get('semantic_positive_rate', 0.0):.1%}",
            f"- Exact agreement rate: {diag.get('exact_agreement_rate', 0.0):.1%}",
            f"- Proxy false-positive candidates: {diag.get('proxy_false_positive_count', 0)} ({diag.get('proxy_false_positive_rate', 0.0):.1%} of proxy positives)",
            f"- Proxy false-negative candidates: {diag.get('proxy_false_negative_count', 0)} ({diag.get('proxy_false_negative_rate', 0.0):.1%} of proxy negatives)",
            f"- Semantic labels: `{json.dumps(diag.get('semantic_label_counts', {}), ensure_ascii=False, sort_keys=True)}`",
            f"- Proxy labels: `{json.dumps(diag.get('proxy_label_counts_on_matched', {}), ensure_ascii=False, sort_keys=True)}`",
            "",
            "## Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in report.get("notes", []))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Recompute lifecycle robustness with semantic meta-review uptake labels.")
    parser.add_argument("--reviewer-calibration", required=True)
    parser.add_argument("--semantic-meta-labels", action="append", required=True)
    parser.add_argument("--out", default="data/validation/semantic_meta_lifecycle_v0.1.json")
    parser.add_argument("--markdown", default="reports/validation/semantic_meta_lifecycle_v0.1.md")
    parser.add_argument("--calibration-out", default="")
    args = parser.parse_args(argv)

    calibration = read_json(args.reviewer_calibration)
    labels = []
    for path in args.semantic_meta_labels:
        labels.extend(read_jsonl(path))
    report = build_semantic_lifecycle_report(calibration, labels)
    write_json(args.out, report)
    write_semantic_lifecycle_markdown(report, args.markdown)
    if args.calibration_out:
        updated = apply_semantic_meta_to_calibration(calibration, labels)
        write_json(args.calibration_out, updated)
    print(f"Saved semantic lifecycle report to {args.out} and {args.markdown}.")


if __name__ == "__main__":
    main()
