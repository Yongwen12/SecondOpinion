from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ADDRESSABILITY_TASK_VERSION = "addressability-task-v0.1"
TARGET_RESPONSES = {"not_addressed", "generic_or_unclear"}
TARGET_EFFECTS = {"does_not_address", "partially_addresses"}


def build_addressability_tasks(reviewer_calibration: dict[str, Any], *, limit: int | None = None) -> list[dict[str, Any]]:
    tasks = []
    for record in iter_claim_records(reviewer_calibration):
        claim = record["claim"]
        llm = claim.get("rebuttal_resolution", {}).get("llm_calibration", {}) or {}
        response = llm.get("rebuttal_response_label", "")
        effect = llm.get("rebuttal_effect_on_claim", "")
        if response not in TARGET_RESPONSES and effect not in TARGET_EFFECTS:
            continue
        tasks.append(addressability_task(record, response=response, effect=effect))
        if limit is not None and len(tasks) >= limit:
            break
    return tasks


def addressability_task(record: dict[str, Any], *, response: str, effect: str) -> dict[str, Any]:
    claim = record["claim"]
    rebuttal = claim.get("rebuttal_resolution", {})
    llm = rebuttal.get("llm_calibration", {}) or {}
    return {
        "schema_version": ADDRESSABILITY_TASK_VERSION,
        "task_id": record_key(record),
        "paper_id": record["paper_id"],
        "review_id": record["review_id"],
        "claim_index": record["claim_index"],
        "title": record.get("title", ""),
        "reviewer_claim": claim.get("claim_text", ""),
        "claim_type": claim.get("claim_type", ""),
        "importance_proxy": claim.get("importance", ""),
        "source_sentence": claim.get("source_sentence", ""),
        "matched_rebuttal_segment": rebuttal.get("matched_segment", ""),
        "current_rebuttal_response_label": response,
        "current_rebuttal_effect_label": effect,
        "current_rationale": llm.get("rationale", ""),
        "label_schema": {
            "concern_addressability": [
                "answerable_fixable",
                "structurally_unresolvable",
                "requires_concession",
            ],
            "instruction": (
                "Judge the concern itself, independent of whether the author actually answered it well. "
                "answerable_fixable means a substantive rebuttal could plausibly address it with clarification, evidence, or a feasible added result. "
                "structurally_unresolvable means it is a broad framing/novelty/impact judgment or fundamental limitation that cannot be fully solved inside rebuttal. "
                "requires_concession means the concern is valid and the right move is to concede/scope down rather than claim it is solved."
            ),
        },
    }


def iter_claim_records(report: dict[str, Any]):
    for paper in report.get("papers", []):
        for review in paper.get("reviews", []):
            for claim_index, claim in enumerate(review.get("claims", [])):
                yield {
                    "paper_id": paper.get("paper_id", ""),
                    "review_id": review.get("review_id", ""),
                    "claim_index": claim_index,
                    "title": paper.get("title", ""),
                    "claim": claim,
                }


def record_key(record: dict[str, Any]) -> str:
    return f"{record.get('paper_id', '')}:{record.get('review_id', '')}:{record.get('claim_index', 0)}"


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export addressability labeling candidates for unresolved/partial rebuttal concerns.")
    parser.add_argument("--reviewer-calibration", required=True)
    parser.add_argument("--out", default="data/validation/addressability_test4_candidates_v0.1.jsonl")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    reviewer_calibration = read_json(args.reviewer_calibration)
    tasks = build_addressability_tasks(reviewer_calibration, limit=args.limit)
    write_jsonl(args.out, tasks)
    print(f"Saved {len(tasks)} addressability candidates to {args.out}.")


if __name__ == "__main__":
    main()
