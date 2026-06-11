from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any


LIFECYCLE_ABLATION_VERSION = "lifecycle-proxy-ablation-v0.1"

WEIGHTS = {
    "grounding": 0.15,
    "specificity": 0.15,
    "consensus": 0.18,
    "rebuttal_robustness": 0.25,
    "discussion_followup": 0.07,
    "meta_review_uptake": 0.20,
}


def build_lifecycle_ablation_report(calibration_report: dict[str, Any]) -> dict[str, Any]:
    claims = list(iter_claim_records(calibration_report))
    mode_rows = {
        "proxy_only": score_records(claims, mode="proxy_only"),
        "hybrid": score_records(claims, mode="hybrid"),
        "llm_calibrated_only": score_records(claims, mode="llm_calibrated_only"),
        "strict_both_llm": score_records(claims, mode="strict_both_llm"),
    }
    return {
        "schema_version": LIFECYCLE_ABLATION_VERSION,
        "source": {
            "calibration_version": calibration_report.get("calibration_version", ""),
            "source": calibration_report.get("source", {}),
        },
        "summary": {
            "claim_count": len(claims),
            "llm_rebuttal_claim_count": sum(1 for item in claims if has_llm_rebuttal(item["claim"])),
            "llm_consensus_claim_count": sum(1 for item in claims if has_llm_consensus(item["claim"])),
            "any_llm_claim_count": sum(1 for item in claims if has_any_llm(item["claim"])),
            "both_llm_claim_count": sum(1 for item in claims if has_llm_rebuttal(item["claim"]) and has_llm_consensus(item["claim"])),
        },
        "modes": {mode: summarize_rows(rows) for mode, rows in mode_rows.items()},
        "comparisons": {
            "hybrid_vs_proxy_all_claims": compare_rows(mode_rows["proxy_only"], mode_rows["hybrid"]),
            "llm_subset_hybrid_vs_proxy": compare_rows(
                [row for row in mode_rows["proxy_only"] if row["has_any_llm"]],
                mode_rows["llm_calibrated_only"],
            ),
            "strict_both_llm_hybrid_vs_proxy": compare_rows(
                [row for row in mode_rows["proxy_only"] if row["has_llm_rebuttal"] and row["has_llm_consensus"]],
                mode_rows["strict_both_llm"],
            ),
        },
        "lexical_proxy_diagnostics": build_lexical_proxy_diagnostics(claims),
        "notes": [
            "`proxy_only` uses deterministic lexical-overlap labels for consensus, rebuttal, and meta-review uptake.",
            "`hybrid` mirrors the current lifecycle logic: LLM labels are used for rebuttal/consensus when available, with proxy fallback otherwise.",
            "`llm_calibrated_only` restricts analysis to claims with at least one LLM rebuttal or consensus label; uncalibrated components still use proxy fallback to keep the lifecycle formula comparable.",
            "`strict_both_llm` is the small high-precision subset where both rebuttal and consensus have LLM labels. Meta-review uptake is still proxy-based in all modes.",
        ],
    }


def iter_claim_records(calibration_report: dict[str, Any]):
    for paper in calibration_report.get("papers", []):
        for review in paper.get("reviews", []):
            for index, claim in enumerate(review.get("claims", [])):
                yield {
                    "paper_id": paper.get("paper_id", ""),
                    "review_id": review.get("review_id", ""),
                    "claim_index": index,
                    "claim": claim,
                }


def score_records(records: list[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        claim = record["claim"]
        if mode == "llm_calibrated_only" and not has_any_llm(claim):
            continue
        if mode == "strict_both_llm" and not (has_llm_rebuttal(claim) and has_llm_consensus(claim)):
            continue
        rows.append(score_record(record, mode=mode))
    return rows


def score_record(record: dict[str, Any], *, mode: str) -> dict[str, Any]:
    claim = record["claim"]
    if mode == "proxy_only":
        consensus = proxy_consensus_score(claim)
        rebuttal = proxy_rebuttal_robustness_score(claim)
    else:
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
        "meta_review_uptake": meta_review_score(claim),
    }
    score = round(sum(WEIGHTS[key] * value for key, value in signals.items()), 4)
    return {
        "key": record_key(record),
        "paper_id": record["paper_id"],
        "review_id": record["review_id"],
        "claim_index": record["claim_index"],
        "claim_text": claim.get("claim_text", ""),
        "has_llm_rebuttal": has_llm_rebuttal(claim),
        "has_llm_consensus": has_llm_consensus(claim),
        "has_any_llm": has_any_llm(claim),
        "score": score,
        "label": lifecycle_label(score),
        "signals": {key: round(value, 4) for key, value in signals.items()},
    }


def record_key(record: dict[str, Any]) -> str:
    return f"{record.get('paper_id', '')}:{record.get('review_id', '')}:{record.get('claim_index', 0)}"


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row["score"] for row in rows]
    signal_keys = list(WEIGHTS)
    return {
        "claim_count": len(rows),
        "paper_count": len({row["paper_id"] for row in rows}),
        "review_count": len({(row["paper_id"], row["review_id"]) for row in rows}),
        "mean_lifecycle_robustness": round(mean(scores), 4),
        "median_lifecycle_robustness": round(median(scores), 4) if scores else 0.0,
        "label_counts": dict(Counter(row["label"] for row in rows)),
        "llm_rebuttal_coverage": round(mean(row["has_llm_rebuttal"] for row in rows), 4),
        "llm_consensus_coverage": round(mean(row["has_llm_consensus"] for row in rows), 4),
        "mean_signals": {
            key: round(mean(row["signals"][key] for row in rows), 4)
            for key in signal_keys
        },
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
    signal_delta = {}
    for signal in WEIGHTS:
        signal_delta[signal] = round(
            mean(right_by_key[key]["signals"][signal] - left_by_key[key]["signals"][signal] for key in keys),
            4,
        )
    return {
        "claim_count": len(keys),
        "mean_score_delta": round(mean(deltas), 4),
        "median_score_delta": round(median(deltas), 4) if deltas else 0.0,
        "mean_abs_score_delta": round(mean(abs(delta) for delta in deltas), 4),
        "label_change_count": sum(label_changes.values()),
        "label_change_rate": round(sum(label_changes.values()) / len(keys), 4) if keys else 0.0,
        "label_changes": dict(label_changes),
        "mean_signal_deltas": signal_delta,
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
                "left_score": left["score"],
                "right_score": right["score"],
                "delta": round(right["score"] - left["score"], 4),
                "left_label": left["label"],
                "right_label": right["label"],
            }
        )
    return examples


def build_lexical_proxy_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    claims = [record["claim"] for record in records]
    rebuttal_claims = [claim for claim in claims if has_llm_rebuttal(claim)]
    consensus_claims = [claim for claim in claims if has_llm_consensus(claim)]
    proxy_rebuttal_addressed = [
        claim
        for claim in rebuttal_claims
        if claim.get("rebuttal_resolution", {}).get("label") in {"addressed_unclear_resolution", "likely_resolved_or_answered"}
    ]
    llm_rebuttal_addressed = [
        claim
        for claim in rebuttal_claims
        if llm_rebuttal_response_label(claim) in {"specifically_addressed", "likely_resolved"}
    ]
    llm_rebuttal_resolved = [
        claim
        for claim in rebuttal_claims
        if llm_rebuttal_effect_label(claim) == "resolved_or_weakened" or llm_rebuttal_response_label(claim) == "likely_resolved"
    ]
    rebuttal_false_positive = [
        claim
        for claim in proxy_rebuttal_addressed
        if llm_rebuttal_response_label(claim) in {"not_addressed", "generic_or_unclear"}
        or llm_rebuttal_effect_label(claim) in {"does_not_address", "unclear"}
    ]

    proxy_consensus_positive = [
        claim
        for claim in consensus_claims
        if claim.get("consensus", {}).get("label") in {"partial", "strong"}
    ]
    llm_consensus_related = [
        claim
        for claim in consensus_claims
        if llm_consensus_label(claim) in {"same_concern", "related_but_different"}
    ]
    llm_consensus_same = [
        claim
        for claim in consensus_claims
        if llm_consensus_label(claim) == "same_concern"
    ]
    consensus_false_positive = [
        claim
        for claim in proxy_consensus_positive
        if llm_consensus_label(claim) == "not_same_concern"
    ]
    return {
        "rebuttal": {
            "llm_labeled_claim_count": len(rebuttal_claims),
            "proxy_label_counts_on_labeled": dict(Counter(claim.get("rebuttal_resolution", {}).get("label", "") for claim in rebuttal_claims)),
            "llm_response_label_counts": dict(Counter(llm_rebuttal_response_label(claim) for claim in rebuttal_claims)),
            "llm_effect_label_counts": dict(Counter(llm_rebuttal_effect_label(claim) for claim in rebuttal_claims)),
            "proxy_addressed_or_resolved_rate": rate(len(proxy_rebuttal_addressed), len(rebuttal_claims)),
            "llm_specifically_addressed_or_resolved_rate": rate(len(llm_rebuttal_addressed), len(rebuttal_claims)),
            "llm_resolved_or_weakened_rate": rate(len(llm_rebuttal_resolved), len(rebuttal_claims)),
            "lexical_false_positive_candidate_count": len(rebuttal_false_positive),
            "lexical_false_positive_candidate_rate": rate(len(rebuttal_false_positive), len(proxy_rebuttal_addressed)),
        },
        "consensus": {
            "llm_labeled_claim_count": len(consensus_claims),
            "proxy_label_counts_on_labeled": dict(Counter(claim.get("consensus", {}).get("label", "") for claim in consensus_claims)),
            "llm_consensus_label_counts": dict(Counter(llm_consensus_label(claim) for claim in consensus_claims)),
            "proxy_partial_or_strong_rate": rate(len(proxy_consensus_positive), len(consensus_claims)),
            "llm_related_or_same_rate": rate(len(llm_consensus_related), len(consensus_claims)),
            "llm_same_concern_rate": rate(len(llm_consensus_same), len(consensus_claims)),
            "lexical_false_positive_candidate_count": len(consensus_false_positive),
            "lexical_false_positive_candidate_rate": rate(len(consensus_false_positive), len(proxy_consensus_positive)),
        },
    }


def write_lifecycle_ablation_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_lifecycle_ablation_markdown(report), encoding="utf-8")


def render_lifecycle_ablation_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Lifecycle Proxy Ablation",
        "",
        "## Scope",
        "",
        f"- Claims: {summary.get('claim_count', 0)}",
        f"- Claims with LLM rebuttal labels: {summary.get('llm_rebuttal_claim_count', 0)}",
        f"- Claims with LLM consensus labels: {summary.get('llm_consensus_claim_count', 0)}",
        f"- Claims with any LLM label: {summary.get('any_llm_claim_count', 0)}",
        f"- Claims with both LLM labels: {summary.get('both_llm_claim_count', 0)}",
        "",
        "## Mode Summary",
        "",
        "| Mode | Claims | Mean lifecycle | Median lifecycle | High | Medium | Low | LLM rebuttal coverage | LLM consensus coverage |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode, item in report.get("modes", {}).items():
        counts = item.get("label_counts", {})
        lines.append(
            f"| `{mode}` | {item.get('claim_count', 0)} | {item.get('mean_lifecycle_robustness', 0.0):.1%} | "
            f"{item.get('median_lifecycle_robustness', 0.0):.1%} | {counts.get('high', 0)} | "
            f"{counts.get('medium', 0)} | {counts.get('low', 0)} | "
            f"{item.get('llm_rebuttal_coverage', 0.0):.1%} | {item.get('llm_consensus_coverage', 0.0):.1%} |"
        )
    lines.extend(["", "## Mean Signal Scores", ""])
    for mode, item in report.get("modes", {}).items():
        signals = item.get("mean_signals", {})
        lines.append(f"### `{mode}`")
        for key in WEIGHTS:
            lines.append(f"- `{key}`: {signals.get(key, 0.0):.1%}")
        lines.append("")
    lines.extend(["## Comparisons", ""])
    for name, comparison in report.get("comparisons", {}).items():
        lines.extend(
            [
                f"### `{name}`",
                "",
                f"- Claims compared: {comparison.get('claim_count', 0)}",
                f"- Mean score delta: {comparison.get('mean_score_delta', 0.0):+.1%}",
                f"- Mean absolute score delta: {comparison.get('mean_abs_score_delta', 0.0):.1%}",
                f"- Label changes: {comparison.get('label_change_count', 0)} ({comparison.get('label_change_rate', 0.0):.1%})",
                f"- Label-change counts: `{json.dumps(comparison.get('label_changes', {}), sort_keys=True)}`",
                f"- Mean signal deltas: `{json.dumps(comparison.get('mean_signal_deltas', {}), sort_keys=True)}`",
                "",
            ]
        )
    diagnostics = report.get("lexical_proxy_diagnostics", {})
    rebuttal = diagnostics.get("rebuttal", {})
    consensus = diagnostics.get("consensus", {})
    lines.extend(
        [
            "## Lexical Proxy Diagnostics",
            "",
            "### Rebuttal Resolution",
            "",
            f"- LLM-labeled claims: {rebuttal.get('llm_labeled_claim_count', 0)}",
            f"- Proxy says addressed/resolved: {rebuttal.get('proxy_addressed_or_resolved_rate', 0.0):.1%}",
            f"- LLM says specifically addressed/resolved: {rebuttal.get('llm_specifically_addressed_or_resolved_rate', 0.0):.1%}",
            f"- LLM says resolved/weakened: {rebuttal.get('llm_resolved_or_weakened_rate', 0.0):.1%}",
            f"- Lexical false-positive candidates among proxy-addressed claims: {rebuttal.get('lexical_false_positive_candidate_count', 0)} ({rebuttal.get('lexical_false_positive_candidate_rate', 0.0):.1%})",
            f"- Proxy labels: `{json.dumps(rebuttal.get('proxy_label_counts_on_labeled', {}), sort_keys=True)}`",
            f"- LLM response labels: `{json.dumps(rebuttal.get('llm_response_label_counts', {}), sort_keys=True)}`",
            f"- LLM effect labels: `{json.dumps(rebuttal.get('llm_effect_label_counts', {}), sort_keys=True)}`",
            "",
            "### Inter-Reviewer Consensus",
            "",
            f"- LLM-labeled claims: {consensus.get('llm_labeled_claim_count', 0)}",
            f"- Proxy says partial/strong: {consensus.get('proxy_partial_or_strong_rate', 0.0):.1%}",
            f"- LLM says related/same: {consensus.get('llm_related_or_same_rate', 0.0):.1%}",
            f"- LLM says same concern: {consensus.get('llm_same_concern_rate', 0.0):.1%}",
            f"- Lexical false-positive candidates among proxy-positive claims: {consensus.get('lexical_false_positive_candidate_count', 0)} ({consensus.get('lexical_false_positive_candidate_rate', 0.0):.1%})",
            f"- Proxy labels: `{json.dumps(consensus.get('proxy_label_counts_on_labeled', {}), sort_keys=True)}`",
            f"- LLM labels: `{json.dumps(consensus.get('llm_consensus_label_counts', {}), sort_keys=True)}`",
            "",
            "## Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in report.get("notes", []))
    return "\n".join(lines) + "\n"


def proxy_consensus_score(claim: dict[str, Any]) -> float:
    label = claim.get("consensus", {}).get("label", "")
    return {"strong": 1.0, "partial": 0.55, "none": 0.0}.get(label, 0.0)


def llm_consensus_score(claim: dict[str, Any]) -> float | None:
    label = llm_consensus_label(claim)
    if not label:
        return None
    return {
        "same_concern": 1.0,
        "related_but_different": 0.55,
        "not_same_concern": 0.0,
        "unsure": 0.25,
    }.get(label, 0.25)


def proxy_rebuttal_robustness_score(claim: dict[str, Any]) -> float:
    label = claim.get("rebuttal_resolution", {}).get("label", "")
    if label == "likely_resolved_or_answered":
        return 0.15
    if label == "addressed_unclear_resolution":
        return 0.55
    if label == "not_addressed":
        return 0.70
    return 0.45


def llm_rebuttal_robustness_score(claim: dict[str, Any]) -> float | None:
    response = llm_rebuttal_response_label(claim)
    effect = llm_rebuttal_effect_label(claim)
    if not response and not effect:
        return None
    if effect == "resolved_or_weakened" or response == "likely_resolved":
        return 0.0
    if response == "specifically_addressed" or effect == "partially_addresses":
        return 0.55
    if response == "generic_or_unclear" or effect == "unclear":
        return 0.75 if response == "generic_or_unclear" else 0.45
    if response == "not_addressed" or effect == "does_not_address":
        return 0.85
    return 0.45


def discussion_score(claim: dict[str, Any]) -> float:
    return 0.70 if claim.get("discussion_followup", {}).get("label") == "followed_up" else 0.0


def meta_review_score(claim: dict[str, Any]) -> float:
    return {
        "survived": 1.0,
        "partial": 0.60,
        "not_found": 0.0,
    }.get(claim.get("meta_review_uptake", {}).get("label", ""), 0.0)


def lifecycle_label(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def has_llm_rebuttal(claim: dict[str, Any]) -> bool:
    return bool(claim.get("rebuttal_resolution", {}).get("llm_calibration"))


def has_llm_consensus(claim: dict[str, Any]) -> bool:
    return bool(claim.get("consensus", {}).get("llm_calibration"))


def has_any_llm(claim: dict[str, Any]) -> bool:
    return has_llm_rebuttal(claim) or has_llm_consensus(claim)


def llm_rebuttal_response_label(claim: dict[str, Any]) -> str:
    return claim.get("rebuttal_resolution", {}).get("llm_calibration", {}).get("rebuttal_response_label", "")


def llm_rebuttal_effect_label(claim: dict[str, Any]) -> str:
    return claim.get("rebuttal_resolution", {}).get("llm_calibration", {}).get("rebuttal_effect_on_claim", "")


def llm_consensus_label(claim: dict[str, Any]) -> str:
    return claim.get("consensus", {}).get("llm_calibration", {}).get("consensus_label", "")


def bounded_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def mean(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(float(value) for value in items) / len(items)


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run lifecycle robustness lexical-proxy ablations.")
    parser.add_argument("--reviewer-calibration", required=True)
    parser.add_argument("--out", default="data/validation/lifecycle_proxy_ablation_v0.1.json")
    parser.add_argument("--markdown", default="reports/validation/lifecycle_proxy_ablation_v0.1.md")
    args = parser.parse_args(argv)

    calibration = read_json(args.reviewer_calibration)
    report = build_lifecycle_ablation_report(calibration)
    write_json(args.out, report)
    write_lifecycle_ablation_markdown(report, args.markdown)
    print(f"Saved lifecycle proxy ablation to {args.out} and {args.markdown}.")


if __name__ == "__main__":
    main()
