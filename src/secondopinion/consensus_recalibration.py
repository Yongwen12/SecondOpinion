from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

from .lifecycle_ablation import (
    WEIGHTS,
    bounded_float,
    compare_rows,
    discussion_score,
    has_llm_consensus,
    lifecycle_label,
    llm_consensus_label,
    llm_consensus_score,
    llm_rebuttal_robustness_score,
    meta_review_score,
    proxy_consensus_score,
    proxy_rebuttal_robustness_score,
)


CONSENSUS_RECALIBRATION_VERSION = "consensus-recalibration-v0.1"


def build_consensus_recalibration_report(calibration_report: dict[str, Any]) -> dict[str, Any]:
    records = list(iter_claim_records(calibration_report))
    modes = {
        "current_hybrid": score_records(records, consensus_mode="current_hybrid"),
        "strict_same_only_hybrid": score_records(records, consensus_mode="strict_same_only_hybrid"),
        "current_labeled_only": score_records(records, consensus_mode="current_labeled_only"),
        "strict_same_only_labeled": score_records(records, consensus_mode="strict_same_only_labeled"),
    }
    return {
        "schema_version": CONSENSUS_RECALIBRATION_VERSION,
        "source": {
            "calibration_version": calibration_report.get("calibration_version", ""),
            "source": calibration_report.get("source", {}),
        },
        "summary": {
            "claim_count": len(records),
            "llm_consensus_claim_count": sum(1 for record in records if has_llm_consensus(record["claim"])),
        },
        "modes": {name: summarize_rows(rows) for name, rows in modes.items()},
        "comparisons": {
            "strict_hybrid_vs_current_all_claims": compare_rows(modes["current_hybrid"], modes["strict_same_only_hybrid"]),
            "strict_labeled_vs_current_labeled": compare_rows(
                modes["current_labeled_only"],
                modes["strict_same_only_labeled"],
            ),
        },
        "diagnostics": build_consensus_diagnostics(records),
        "examples": build_examples(records),
        "notes": [
            "`current_hybrid` mirrors the current lifecycle consensus score: same_concern=1.0, related_but_different=0.55, proxy fallback when no LLM label exists.",
            "`strict_same_only_hybrid` only treats LLM same_concern as inter-reviewer support; related_but_different, not_same_concern, and unsure all score 0.0.",
            "This report isolates the consensus leg. Rebuttal, discussion, grounding, specificity, and meta-review uptake use the current lifecycle-ablation scoring logic.",
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


def score_records(records: list[dict[str, Any]], *, consensus_mode: str) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        if consensus_mode in {"current_labeled_only", "strict_same_only_labeled"} and not has_llm_consensus(record["claim"]):
            continue
        rows.append(score_record(record, consensus_mode=consensus_mode))
    return rows


def score_record(record: dict[str, Any], *, consensus_mode: str) -> dict[str, Any]:
    claim = record["claim"]
    signals = {
        "grounding": 1.0 if claim.get("grounded") else 0.0,
        "specificity": bounded_float(claim.get("specificity_score", 0.0)),
        "consensus": bounded_float(consensus_score(claim, mode=consensus_mode)),
        "rebuttal_robustness": bounded_float(rebuttal_score(claim)),
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
        "proxy_consensus_label": claim.get("consensus", {}).get("label", ""),
        "llm_consensus_label": llm_consensus_label(claim),
        "score": score,
        "label": lifecycle_label(score),
        "signals": {key: round(value, 4) for key, value in signals.items()},
    }


def consensus_score(claim: dict[str, Any], *, mode: str) -> float:
    if mode.startswith("current"):
        llm_score = llm_consensus_score(claim)
        return proxy_consensus_score(claim) if llm_score is None else llm_score
    label = llm_consensus_label(claim)
    if label:
        return 1.0 if label == "same_concern" else 0.0
    return proxy_consensus_score(claim)


def rebuttal_score(claim: dict[str, Any]) -> float:
    llm_score = llm_rebuttal_robustness_score(claim)
    return proxy_rebuttal_robustness_score(claim) if llm_score is None else llm_score


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row["score"] for row in rows]
    return {
        "claim_count": len(rows),
        "paper_count": len({row["paper_id"] for row in rows}),
        "review_count": len({(row["paper_id"], row["review_id"]) for row in rows}),
        "mean_lifecycle_robustness": round(mean(scores), 4),
        "median_lifecycle_robustness": round(median(scores), 4) if scores else 0.0,
        "label_counts": dict(Counter(row["label"] for row in rows)),
        "mean_consensus_score": round(mean(row["signals"]["consensus"] for row in rows), 4),
    }


def build_consensus_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    claims = [record["claim"] for record in records]
    labeled = [claim for claim in claims if has_llm_consensus(claim)]
    proxy_positive = [claim for claim in labeled if claim.get("consensus", {}).get("label", "") in {"partial", "strong"}]
    related = [claim for claim in labeled if llm_consensus_label(claim) == "related_but_different"]
    same = [claim for claim in labeled if llm_consensus_label(claim) == "same_concern"]
    not_same = [claim for claim in labeled if llm_consensus_label(claim) == "not_same_concern"]
    return {
        "llm_labeled_claim_count": len(labeled),
        "proxy_label_counts_on_labeled": dict(Counter(claim.get("consensus", {}).get("label", "") for claim in labeled)),
        "llm_consensus_label_counts": dict(Counter(llm_consensus_label(claim) for claim in labeled)),
        "proxy_partial_or_strong_rate": rate(len(proxy_positive), len(labeled)),
        "current_related_or_same_support_rate": rate(len(related) + len(same), len(labeled)),
        "strict_same_support_rate": rate(len(same), len(labeled)),
        "related_demotion_count": len(related),
        "related_demotion_rate": rate(len(related), len(labeled)),
        "not_same_claim_count": len(not_same),
        "proxy_positive_not_same_count": sum(1 for claim in proxy_positive if llm_consensus_label(claim) == "not_same_concern"),
        "proxy_positive_related_but_different_count": sum(
            1 for claim in proxy_positive if llm_consensus_label(claim) == "related_but_different"
        ),
    }


def build_examples(records: list[dict[str, Any]], *, limit: int = 12) -> dict[str, list[dict[str, Any]]]:
    related = []
    same = []
    for record in records:
        claim = record["claim"]
        label = llm_consensus_label(claim)
        if label not in {"related_but_different", "same_concern"}:
            continue
        item = {
            "key": record_key(record),
            "paper_id": record["paper_id"],
            "review_id": record["review_id"],
            "claim_text": claim.get("claim_text", ""),
            "matched_review_id": claim.get("consensus", {}).get("matched_review_id", ""),
            "matched_claim_text": claim.get("consensus", {}).get("matched_claim_text", ""),
            "proxy_consensus_label": claim.get("consensus", {}).get("label", ""),
            "llm_consensus_label": label,
        }
        if label == "related_but_different":
            related.append(item)
        else:
            same.append(item)
    return {
        "related_but_different_demotions": related[:limit],
        "same_concern_support": same[:limit],
    }


def record_key(record: dict[str, Any]) -> str:
    return f"{record.get('paper_id', '')}:{record.get('review_id', '')}:{record.get('claim_index', 0)}"


def render_consensus_recalibration_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Consensus Recalibration",
        "",
        "## Scope",
        "",
        f"- Claims: {summary.get('claim_count', 0)}",
        f"- Claims with LLM consensus labels: {summary.get('llm_consensus_claim_count', 0)}",
        "",
        "## Mode Summary",
        "",
        "| Mode | Claims | Mean lifecycle | Median lifecycle | Mean consensus | High | Medium | Low |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode, item in report.get("modes", {}).items():
        counts = item.get("label_counts", {})
        lines.append(
            f"| `{mode}` | {item.get('claim_count', 0)} | {item.get('mean_lifecycle_robustness', 0.0):.1%} | "
            f"{item.get('median_lifecycle_robustness', 0.0):.1%} | {item.get('mean_consensus_score', 0.0):.1%} | "
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
                f"- Label changes: {comparison.get('label_change_count', 0)} ({comparison.get('label_change_rate', 0.0):.1%})",
                f"- Label-change counts: `{json.dumps(comparison.get('label_changes', {}), sort_keys=True)}`",
                f"- Mean signal deltas: `{json.dumps(comparison.get('mean_signal_deltas', {}), sort_keys=True)}`",
                "",
            ]
        )
    diagnostics = report.get("diagnostics", {})
    lines.extend(
        [
            "## Diagnostics",
            "",
            f"- LLM-labeled claims: {diagnostics.get('llm_labeled_claim_count', 0)}",
            f"- Proxy says partial/strong: {diagnostics.get('proxy_partial_or_strong_rate', 0.0):.1%}",
            f"- Current related/same support rate: {diagnostics.get('current_related_or_same_support_rate', 0.0):.1%}",
            f"- Strict same-concern support rate: {diagnostics.get('strict_same_support_rate', 0.0):.1%}",
            f"- Related-but-different demotions: {diagnostics.get('related_demotion_count', 0)} ({diagnostics.get('related_demotion_rate', 0.0):.1%})",
            f"- Proxy-positive but not-same claims: {diagnostics.get('proxy_positive_not_same_count', 0)}",
            f"- Proxy-positive but related-different claims: {diagnostics.get('proxy_positive_related_but_different_count', 0)}",
            f"- Proxy labels: `{json.dumps(diagnostics.get('proxy_label_counts_on_labeled', {}), sort_keys=True)}`",
            f"- LLM labels: `{json.dumps(diagnostics.get('llm_consensus_label_counts', {}), sort_keys=True)}`",
            "",
            "## Example Demotions",
            "",
        ]
    )
    for item in report.get("examples", {}).get("related_but_different_demotions", [])[:8]:
        lines.append(f"- `{item['key']}` proxy=`{item['proxy_consensus_label']}`: {item['claim_text'][:220]}")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in report.get("notes", []))
    return "\n".join(lines) + "\n"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_consensus_recalibration_markdown(report), encoding="utf-8")


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def mean(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(float(value) for value in items) / len(items)


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Recalibrate lifecycle consensus with a strict same-concern definition.")
    parser.add_argument("--reviewer-calibration", required=True)
    parser.add_argument("--out", default="data/validation/consensus_recalibration_v0.1.json")
    parser.add_argument("--markdown", default="reports/validation/consensus_recalibration_v0.1.md")
    args = parser.parse_args(argv)

    calibration = read_json(args.reviewer_calibration)
    report = build_consensus_recalibration_report(calibration)
    write_json(args.out, report)
    write_markdown(args.markdown, report)
    print(f"Saved consensus recalibration to {args.out} and {args.markdown}.")


if __name__ == "__main__":
    main()
