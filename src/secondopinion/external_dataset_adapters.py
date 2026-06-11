from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .retrieval import token_list


CONTRASCIVIEW_LABELS = {
    "c": "contradiction",
    "contradiction": "contradiction",
    "n": "not_contradiction",
    "not_contradiction": "not_contradiction",
    "neutral": "not_contradiction",
}


def normalize_contrasciview_csv(
    path: str | Path,
    *,
    baseline: str = "polarity",
    overlap_threshold: float = 0.10,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            if limit is not None and len(rows) >= limit:
                break
            gold_label = normalize_contrasciview_label(row.get("label", ""))
            if not gold_label:
                continue
            rows.append(
                {
                    "task_id": contrasciview_task_id(row, index),
                    "dataset": "ContraSciView",
                    "split": "",
                    "gold_label": gold_label,
                    "predicted_label": contrasciview_baseline_prediction(
                        row,
                        baseline=baseline,
                        overlap_threshold=overlap_threshold,
                    ),
                    "paper_id": clean_value(row.get("paper_id", "")),
                    "pair_id": clean_value(row.get("pair_id", "")),
                    "aspect": clean_value(row.get("aspect", "")),
                    "premise": clean_value(row.get("premise", "")),
                    "hypothesis": clean_value(row.get("hypothesis", "")),
                    "premise_polarity": normalize_polarity(row.get("s1", "")),
                    "hypothesis_polarity": normalize_polarity(row.get("s2", "")),
                    "token_jaccard": round(text_jaccard(row.get("premise", ""), row.get("hypothesis", "")), 4),
                    "source_label": clean_value(row.get("label", "")),
                }
            )
    return rows


def contrasciview_baseline_prediction(row: dict[str, Any], *, baseline: str, overlap_threshold: float = 0.10) -> str:
    if baseline == "majority":
        return "not_contradiction"
    left = normalize_polarity(row.get("s1", ""))
    right = normalize_polarity(row.get("s2", ""))
    opposite_polarity = left in {"positive", "negative"} and right in {"positive", "negative"} and left != right
    if baseline == "polarity":
        if opposite_polarity:
            return "contradiction"
        return "not_contradiction"
    if baseline == "polarity_overlap":
        if opposite_polarity and text_jaccard(row.get("premise", ""), row.get("hypothesis", "")) >= overlap_threshold:
            return "contradiction"
        return "not_contradiction"
    raise ValueError(f"Unsupported ContraSciView baseline: {baseline}")


def text_jaccard(left: Any, right: Any) -> float:
    left_terms = set(token_list(clean_value(left)))
    right_terms = set(token_list(clean_value(right)))
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def normalize_contrasciview_label(value: Any) -> str:
    return CONTRASCIVIEW_LABELS.get(clean_value(value).lower(), "")


def normalize_polarity(value: Any) -> str:
    value = clean_value(value).lower()
    if value in {"pos", "positive", "+"}:
        return "positive"
    if value in {"neg", "negative", "-"}:
        return "negative"
    if value in {"neu", "neutral", "mixed"}:
        return "neutral"
    return value


def contrasciview_task_id(row: dict[str, Any], index: int) -> str:
    paper_id = clean_value(row.get("paper_id", ""))
    pair_id = clean_value(row.get("pair_id", ""))
    source_index = clean_value(row.get("", "")) or clean_value(row.get("H1", "")) or str(index)
    return f"contrasciview:{paper_id}:{pair_id}:{source_index}"


def clean_value(value: Any) -> str:
    return str(value or "").strip()


def summarize_normalized(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "record_count": len(records),
        "gold_label_counts": dict(Counter(record.get("gold_label", "") for record in records)),
        "predicted_label_counts": dict(Counter(record.get("predicted_label", "") for record in records)),
        "aspect_counts": dict(Counter(record.get("aspect", "") for record in records)),
    }


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Normalize external peer-review datasets into benchmark JSONL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    contrasciview = subparsers.add_parser("normalize-contrasciview")
    contrasciview.add_argument("--input", required=True)
    contrasciview.add_argument("--out", default="data/validation/contrasciview_polarity_baseline.jsonl")
    contrasciview.add_argument("--baseline", choices=["polarity", "polarity_overlap", "majority"], default="polarity")
    contrasciview.add_argument("--overlap-threshold", type=float, default=0.10)
    contrasciview.add_argument("--limit", type=int, default=None)

    args = parser.parse_args(argv)
    if args.command == "normalize-contrasciview":
        records = normalize_contrasciview_csv(
            args.input,
            baseline=args.baseline,
            overlap_threshold=args.overlap_threshold,
            limit=args.limit,
        )
        write_jsonl(args.out, records)
        summary = summarize_normalized(records)
        print(
            f"Saved {summary['record_count']} ContraSciView records to {args.out}. "
            f"gold={summary['gold_label_counts']}; predicted={summary['predicted_label_counts']}."
        )


if __name__ == "__main__":
    main()
