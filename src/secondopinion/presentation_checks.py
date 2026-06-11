from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PRESENTATION_CHECKS_VERSION = "presentation-checks-v0.1"
UNRESOLVED_OR_PARTIAL_EFFECTS = {"does_not_address", "partially_addresses"}


def build_p0_report(
    reviewer_calibration: dict[str, Any],
    *,
    grounding_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    claim_records = list(iter_claim_records(reviewer_calibration))
    rebuttal_labeled = [record for record in claim_records if llm_rebuttal(record["claim"])]
    return {
        "schema_version": PRESENTATION_CHECKS_VERSION,
        "tests": {
            "test_1_materiality_resolution": materiality_resolution_tables(rebuttal_labeled),
            "test_2_sample_size_alignment": sample_size_alignment(reviewer_calibration, claim_records),
            "test_3_grounding_check": grounding_check(claim_records, grounding_validation=grounding_validation),
        },
    }


def iter_claim_records(report: dict[str, Any]):
    for paper_index, paper in enumerate(report.get("papers", [])):
        reviews = paper.get("reviews", [])
        for review_index, review in enumerate(reviews):
            for claim_index, claim in enumerate(review.get("claims", [])):
                yield {
                    "paper_index": paper_index,
                    "review_index": review_index,
                    "paper_id": paper.get("paper_id", ""),
                    "review_id": review.get("review_id", ""),
                    "claim_index": claim_index,
                    "claim": claim,
                }


def materiality_resolution_tables(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for record in records:
        claim = record["claim"]
        label = llm_rebuttal(claim)
        response = label.get("rebuttal_response_label", "")
        effect = label.get("rebuttal_effect_on_claim", "")
        importance = normalize_importance(claim.get("importance", ""))
        rows.append(
            {
                "key": record_key(record),
                "paper_id": record["paper_id"],
                "review_id": record["review_id"],
                "claim_index": record["claim_index"],
                "claim_text": claim.get("claim_text", ""),
                "importance_raw": claim.get("importance", ""),
                "importance": importance,
                "response": response,
                "effect": effect,
                "axis_relation": response_effect_relation(response, effect),
            }
        )
    high_unresolved = [
        row
        for row in rows
        if row["importance"] == "high" and row["effect"] in UNRESOLVED_OR_PARTIAL_EFFECTS
    ]
    specific_but_not_solved = [
        row
        for row in rows
        if row["response"] == "specifically_addressed" and row["effect"] in UNRESOLVED_OR_PARTIAL_EFFECTS
    ]
    relations = Counter(row["axis_relation"] for row in rows)
    return {
        "claim_count": len(rows),
        "importance_raw_counts": dict(Counter(row["importance_raw"] for row in rows)),
        "importance_counts": dict(Counter(row["importance"] for row in rows)),
        "response_counts": dict(Counter(row["response"] for row in rows)),
        "effect_counts": dict(Counter(row["effect"] for row in rows)),
        "importance_by_effect": nested_counts(rows, "importance", "effect"),
        "response_by_effect": nested_counts(rows, "response", "effect"),
        "response_effect_pair_counts": nested_counts(rows, "response", "effect"),
        "high_importance_unresolved_or_partial_count": len(high_unresolved),
        "high_importance_unresolved_or_partial_rate": rate(len(high_unresolved), len(rows)),
        "specifically_addressed_unresolved_or_partial_count": len(specific_but_not_solved),
        "specifically_addressed_unresolved_or_partial_rate": rate(len(specific_but_not_solved), len(rows)),
        "axis_relation_counts": dict(relations),
        "axis_relation_rates": {key: rate(value, len(rows)) for key, value in relations.items()},
        "examples": {
            "high_importance_unresolved_or_partial": example_rows(high_unresolved),
            "specifically_addressed_unresolved_or_partial": example_rows(specific_but_not_solved),
        },
        "notes": [
            "`importance` is the current system proxy (`major` mapped to high). It is useful for sizing only and is not a validated materiality gold label.",
            "`axis_relation` compares response and effect as ordered labels: exact, adjacent, or conflict. The raw response-by-effect table should be treated as the primary evidence.",
        ],
    }


def sample_size_alignment(reviewer_calibration: dict[str, Any], claim_records: list[dict[str, Any]]) -> dict[str, Any]:
    papers = reviewer_calibration.get("papers", [])
    reviews = [review for paper in papers for review in paper.get("reviews", [])]
    reviews_with_claims = [
        review
        for paper in papers
        for review in paper.get("reviews", [])
        if review.get("claims")
    ]
    papers_with_claims = {record["paper_id"] for record in claim_records if record["claim"]}
    summary = reviewer_calibration.get("summary", {})
    return {
        "source_calibration_version": reviewer_calibration.get("calibration_version", ""),
        "summary_counts": {
            "paper_count": summary.get("paper_count"),
            "review_count": summary.get("review_count"),
            "claim_count": summary.get("claim_count"),
            "llm_rebuttal_label_count": reviewer_calibration.get("source", {}).get("llm_rebuttal_label_count"),
            "llm_consensus_label_count": reviewer_calibration.get("source", {}).get("llm_consensus_label_count"),
        },
        "actual_nested_counts": {
            "paper_count": len(papers),
            "review_count": len(reviews),
            "claim_count": len(claim_records),
            "paper_with_claim_count": len(papers_with_claims),
            "review_with_claim_count": len(reviews_with_claims),
        },
        "interpretation": (
            "Use 80 papers / 205 reviews / 854 claims for the reviewer-calibration report scope. "
            "Use 53 papers / 202 reviews / 854 claims when reporting only papers/reviews that contain claim records."
        ),
    }


def grounding_check(
    claim_records: list[dict[str, Any]],
    *,
    grounding_validation: dict[str, Any] | None,
) -> dict[str, Any]:
    grounded = [record for record in claim_records if record["claim"].get("grounded")]
    not_grounded = [record for record in claim_records if not record["claim"].get("grounded")]
    stats = (grounding_validation or {}).get("stats", {})
    return {
        "reviewer_calibration_grounding": {
            "claim_count": len(claim_records),
            "grounded_true_count": len(grounded),
            "grounded_false_count": len(not_grounded),
            "grounded_rate": rate(len(grounded), len(claim_records)),
            "grounding_logic": "In reviewer_calibration.py, `grounded` is set to bool(clean_text(claim.get('source_sentence', ''))).",
            "interpretation": "In lifecycle/reviewer-calibration, grounding is currently an extraction/source-sentence gate, not a discriminative review-quality axis.",
            "examples": grounding_examples(grounded),
            "non_grounded_examples": grounding_examples(not_grounded),
        },
        "grounding_validation_stats": {
            "review_count": stats.get("review_count"),
            "raw_candidate_count": stats.get("raw_candidate_count"),
            "raw_grounding_pass_count": stats.get("raw_grounding_pass_count"),
            "raw_grounding_fail_count": stats.get("raw_grounding_fail_count"),
            "raw_grounding_pass_rate": stats.get("raw_grounding_pass_rate"),
            "final_claim_count": stats.get("final_claim_count"),
            "final_grounding_pass_count": stats.get("final_grounding_pass_count"),
            "final_grounding_fail_count": stats.get("final_grounding_fail_count"),
            "final_grounding_pass_rate": stats.get("final_grounding_pass_rate"),
            "raw_failure_reason_counts": stats.get("raw_failure_reason_counts", {}),
        },
        "grounding_validation_failure_examples": (grounding_validation or {}).get("examples", {}).get("raw_grounding_failures", [])[:5],
    }


def llm_rebuttal(claim: dict[str, Any]) -> dict[str, Any]:
    return claim.get("rebuttal_resolution", {}).get("llm_calibration", {}) or {}


def normalize_importance(value: Any) -> str:
    value = str(value or "").strip().lower()
    if value in {"major", "high"}:
        return "high"
    if value in {"medium", "moderate"}:
        return "medium"
    if value in {"minor", "low", "tone-only", "question"}:
        return "low"
    return value or "unknown"


def response_effect_relation(response: str, effect: str) -> str:
    response_score = {
        "not_addressed": 0,
        "generic_or_unclear": 1,
        "specifically_addressed": 2,
        "likely_resolved": 3,
    }
    effect_score = {
        "does_not_address": 0,
        "unclear": 1,
        "partially_addresses": 2,
        "resolved_or_weakened": 3,
    }
    if response not in response_score or effect not in effect_score:
        return "unknown"
    delta = abs(response_score[response] - effect_score[effect])
    if delta == 0:
        return "exact"
    if delta == 1:
        return "adjacent"
    return "conflict"


def nested_counts(rows: list[dict[str, Any]], row_key: str, col_key: str) -> dict[str, dict[str, int]]:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        table[str(row.get(row_key, ""))][str(row.get(col_key, ""))] += 1
    return {key: dict(value) for key, value in sorted(table.items())}


def example_rows(rows: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    return [
        {
            "key": row["key"],
            "paper_id": row["paper_id"],
            "review_id": row["review_id"],
            "claim_text": truncate(row["claim_text"], 240),
            "importance": row["importance"],
            "response": row["response"],
            "effect": row["effect"],
        }
        for row in rows[:limit]
    ]


def grounding_examples(records: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    examples = []
    for record in records[:limit]:
        claim = record["claim"]
        examples.append(
            {
                "key": record_key(record),
                "paper_id": record["paper_id"],
                "review_id": record["review_id"],
                "claim_text": truncate(claim.get("claim_text", ""), 220),
                "source_sentence": truncate(claim.get("source_sentence", ""), 220),
                "grounded": bool(claim.get("grounded")),
            }
        )
    return examples


def record_key(record: dict[str, Any]) -> str:
    return f"{record.get('paper_id', '')}:{record.get('review_id', '')}:{record.get('claim_index', 0)}"


def render_p0_markdown(report: dict[str, Any]) -> str:
    test1 = report["tests"]["test_1_materiality_resolution"]
    test2 = report["tests"]["test_2_sample_size_alignment"]
    test3 = report["tests"]["test_3_grounding_check"]
    lines = [
        "# Presentation P0 Checks",
        "",
        "## Test 1 - Materiality Proxy x Resolution",
        "",
        f"- LLM-labeled rebuttal claims: {test1['claim_count']}",
        f"- Importance proxy counts: `{json.dumps(test1['importance_counts'], sort_keys=True)}`",
        f"- Response counts: `{json.dumps(test1['response_counts'], sort_keys=True)}`",
        f"- Effect counts: `{json.dumps(test1['effect_counts'], sort_keys=True)}`",
        f"- High-importance and unresolved/partial effect: {test1['high_importance_unresolved_or_partial_count']} ({test1['high_importance_unresolved_or_partial_rate']:.1%})",
        f"- Specifically addressed but unresolved/partial effect: {test1['specifically_addressed_unresolved_or_partial_count']} ({test1['specifically_addressed_unresolved_or_partial_rate']:.1%})",
        f"- Response/effect relation counts: `{json.dumps(test1['axis_relation_counts'], sort_keys=True)}`",
        "",
        "### Importance x Effect",
        "",
        f"`{json.dumps(test1['importance_by_effect'], sort_keys=True)}`",
        "",
        "### Response x Effect",
        "",
        f"`{json.dumps(test1['response_by_effect'], sort_keys=True)}`",
        "",
        "## Test 2 - Sample Size Alignment",
        "",
        f"- Summary counts: `{json.dumps(test2['summary_counts'], sort_keys=True)}`",
        f"- Actual nested counts: `{json.dumps(test2['actual_nested_counts'], sort_keys=True)}`",
        f"- Interpretation: {test2['interpretation']}",
        "",
        "## Test 3 - Grounding Check",
        "",
    ]
    grounding = test3["reviewer_calibration_grounding"]
    validation = test3["grounding_validation_stats"]
    lines.extend(
        [
            f"- Reviewer-calibration claims: {grounding['claim_count']}",
            f"- Grounded true/false: {grounding['grounded_true_count']} / {grounding['grounded_false_count']}",
            f"- Grounded rate: {grounding['grounded_rate']:.1%}",
            f"- Logic: {grounding['grounding_logic']}",
            f"- Interpretation: {grounding['interpretation']}",
            f"- Grounding validation raw pass rate: {format_optional_rate(validation.get('raw_grounding_pass_rate'))}",
            f"- Grounding validation final pass rate: {format_optional_rate(validation.get('final_grounding_pass_rate'))}",
            f"- Raw grounding failures: {validation.get('raw_grounding_fail_count')} of {validation.get('raw_candidate_count')}",
            "",
            "### Grounding Examples",
            "",
        ]
    )
    for example in grounding["examples"]:
        lines.append(f"- `{example['key']}` grounded={example['grounded']} claim={example['claim_text']}")
    lines.append("")
    lines.append("### Raw Grounding Failure Examples From Validation")
    lines.append("")
    for example in test3.get("grounding_validation_failure_examples", []):
        lines.append(f"- `{example.get('paper_id', '')}:{example.get('review_id', '')}` reason={example.get('failure_reasons', [])} claim={truncate(example.get('claim_text', ''), 220)}")
    return "\n".join(lines) + "\n"


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_p0_markdown(report), encoding="utf-8")


def format_optional_rate(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.1%}"


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def truncate(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run presentation-ready P0 sanity checks.")
    parser.add_argument("--reviewer-calibration", required=True)
    parser.add_argument("--grounding-validation", default="")
    parser.add_argument("--out", default="data/validation/presentation_p0_checks_v0.1.json")
    parser.add_argument("--markdown", default="reports/validation/presentation_p0_checks_v0.1.md")
    args = parser.parse_args(argv)

    reviewer_calibration = read_json(args.reviewer_calibration)
    grounding_validation = read_json(args.grounding_validation) if args.grounding_validation else None
    report = build_p0_report(reviewer_calibration, grounding_validation=grounding_validation)
    write_json(args.out, report)
    write_markdown(args.markdown, report)
    print(f"Saved presentation P0 checks to {args.out} and {args.markdown}.")


if __name__ == "__main__":
    main()
