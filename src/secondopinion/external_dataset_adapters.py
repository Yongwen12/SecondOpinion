from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .retrieval import token_list


NORMALIZED_EXTERNAL_DATASET_VERSION = "external-scoring-record-v0.1"

CONTRASCIVIEW_LABELS = {
    "c": "contradiction",
    "contradiction": "contradiction",
    "n": "not_contradiction",
    "not_contradiction": "not_contradiction",
    "neutral": "not_contradiction",
}

DATASET_SPECS: dict[str, dict[str, Any]] = {
    "react": {
        "dataset": "ReAct",
        "default_dimension": "actionability",
        "text_fields": ["comment", "comment_text", "review_comment", "review_text", "sentence", "text"],
        "context_fields": ["aspect", "paper_title", "section", "review_id"],
        "label_fields": ["gold_label", "label", "actionability", "actionability_label", "specificity_label"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "substanreview": {
        "dataset": "SubstanReview",
        "default_dimension": "substantiation",
        "text_fields": ["claim", "claim_text", "comment", "review_comment", "review_text", "sentence", "text"],
        "context_fields": ["evidence", "evidence_text", "justification", "rationale", "paper_title", "section"],
        "label_fields": ["gold_label", "label", "substantiation", "substantiation_label", "is_substantiated"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "disapere": {
        "dataset": "DISAPERE",
        "default_dimension": "rebuttal_robustness",
        "text_fields": ["review_comment", "comment", "review_segment", "claim", "claim_text", "text"],
        "context_fields": ["rebuttal", "rebuttal_text", "response", "response_text", "stance", "paper_title"],
        "label_fields": ["gold_label", "label", "rebuttal_label", "stance", "response_type"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "rbtact": {
        "dataset": "RbtAct",
        "default_dimension": "rebuttal_robustness",
        "text_fields": ["review_comment", "comment", "review_segment", "claim", "claim_text", "text"],
        "context_fields": ["rebuttal", "rebuttal_text", "response", "response_text", "action", "revision"],
        "label_fields": ["gold_label", "label", "rebuttal_action", "action_label", "impact_label"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
}

LABEL_NORMALIZERS = {
    "specificity": {
        "specific": "specific",
        "concrete": "specific",
        "high": "specific",
        "partially_specific": "partially_specific",
        "partial": "partially_specific",
        "medium": "partially_specific",
        "vague": "vague",
        "generic": "vague",
        "low": "vague",
    },
    "substantiation": {
        "substantiated": "substantiated",
        "supported": "substantiated",
        "true": "substantiated",
        "yes": "substantiated",
        "1": "substantiated",
        "partially_substantiated": "partially_substantiated",
        "partial": "partially_substantiated",
        "mixed": "partially_substantiated",
        "unsubstantiated": "unsubstantiated",
        "unsupported": "unsubstantiated",
        "false": "unsubstantiated",
        "no": "unsubstantiated",
        "0": "unsubstantiated",
        "deficient": "deficient",
        "not_deficient": "not_deficient",
    },
    "actionability": {
        "actionable": "actionable",
        "constructive": "constructive",
        "yes": "actionable",
        "true": "actionable",
        "1": "actionable",
        "partially_actionable": "partially_actionable",
        "partial": "partially_actionable",
        "mixed": "partially_actionable",
        "not_actionable": "not_actionable",
        "non_actionable": "not_actionable",
        "non_constructive": "non_constructive",
        "not constructive": "non_constructive",
        "no": "not_actionable",
        "false": "not_actionable",
        "0": "not_actionable",
    },
    "consensus_conflict": CONTRASCIVIEW_LABELS,
    "rebuttal_robustness": {
        "not_addressed": "not_addressed",
        "does_not_address": "not_addressed",
        "unaddressed": "not_addressed",
        "generic_or_unclear": "generic_or_unclear",
        "generic": "generic_or_unclear",
        "unclear": "generic_or_unclear",
        "partially_addresses": "partially_addresses",
        "partial": "partially_addresses",
        "partially_addressed": "partially_addresses",
        "specifically_addressed": "specifically_addressed",
        "addressed": "specifically_addressed",
        "revision": "resolved_or_weakened",
        "revised": "resolved_or_weakened",
        "resolved": "resolved_or_weakened",
        "resolved_or_weakened": "resolved_or_weakened",
        "likely_resolved": "likely_resolved",
        "defended": "generic_or_unclear",
        "rejected": "not_addressed",
    },
    "professionalism": {
        "professional": "professional",
        "polite": "polite",
        "constructive": "professional",
        "neutral": "neutral",
        "unprofessional": "unprofessional",
        "impolite": "impolite",
        "toxic": "unprofessional",
    },
}

MAPPED_SCORES = {
    "specificity": {"specific": 0.9, "partially_specific": 0.55, "vague": 0.15},
    "substantiation": {
        "substantiated": 0.9,
        "partially_substantiated": 0.55,
        "unsubstantiated": 0.15,
        "deficient": 0.2,
        "not_deficient": 0.8,
    },
    "actionability": {
        "actionable": 0.9,
        "partially_actionable": 0.55,
        "not_actionable": 0.15,
        "constructive": 0.85,
        "non_constructive": 0.2,
    },
    "consensus_conflict": {"not_contradiction": 0.65, "contradiction": 0.1},
    "rebuttal_robustness": {
        "not_addressed": 0.9,
        "generic_or_unclear": 0.7,
        "partially_addresses": 0.5,
        "specifically_addressed": 0.3,
        "resolved_or_weakened": 0.1,
        "likely_resolved": 0.1,
    },
    "professionalism": {"professional": 0.9, "polite": 0.85, "neutral": 0.55, "unprofessional": 0.15, "impolite": 0.15},
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
            predicted_label = contrasciview_baseline_prediction(
                row,
                baseline=baseline,
                overlap_threshold=overlap_threshold,
            )
            token_overlap = round(text_jaccard(row.get("premise", ""), row.get("hypothesis", "")), 4)
            record = normalized_record(
                task_id=contrasciview_task_id(row, index),
                dataset="ContraSciView",
                dimension="consensus_conflict",
                input_text=join_text([row.get("premise", ""), row.get("hypothesis", "")]),
                context_text=clean_value(row.get("aspect", "")),
                gold_label=gold_label,
                predicted_label=predicted_label,
                metadata={
                    "paper_id": clean_value(row.get("paper_id", "")),
                    "pair_id": clean_value(row.get("pair_id", "")),
                    "aspect": clean_value(row.get("aspect", "")),
                    "premise": clean_value(row.get("premise", "")),
                    "hypothesis": clean_value(row.get("hypothesis", "")),
                    "premise_polarity": normalize_polarity(row.get("s1", "")),
                    "hypothesis_polarity": normalize_polarity(row.get("s2", "")),
                    "token_jaccard": token_overlap,
                    "source_label": clean_value(row.get("label", "")),
                    "baseline": baseline,
                },
            )
            record.update(
                {
                    "paper_id": clean_value(row.get("paper_id", "")),
                    "pair_id": clean_value(row.get("pair_id", "")),
                    "aspect": clean_value(row.get("aspect", "")),
                    "premise": clean_value(row.get("premise", "")),
                    "hypothesis": clean_value(row.get("hypothesis", "")),
                    "premise_polarity": normalize_polarity(row.get("s1", "")),
                    "hypothesis_polarity": normalize_polarity(row.get("s2", "")),
                    "token_jaccard": token_overlap,
                    "source_label": clean_value(row.get("label", "")),
                }
            )
            rows.append(record)
    return rows


def normalize_react_records(
    records: Iterable[dict[str, Any]],
    *,
    dimension: str = "actionability",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="react", dimension=dimension, limit=limit)


def normalize_substanreview_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="substanreview", dimension="substantiation", limit=limit)


def normalize_disapere_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="disapere", dimension="rebuttal_robustness", limit=limit)


def normalize_rbtact_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="rbtact", dimension="rebuttal_robustness", limit=limit)


def normalize_dataset_records(
    records: Iterable[dict[str, Any]],
    *,
    dataset_key: str,
    dimension: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    spec = DATASET_SPECS[dataset_key]
    dimension = dimension or spec["default_dimension"]
    normalized = []
    for index, row in enumerate(records):
        if limit is not None and len(normalized) >= limit:
            break
        gold_label = normalize_dimension_label(first_value(row, spec["label_fields"]), dimension)
        if not gold_label:
            continue
        predicted_label = normalize_dimension_label(first_value(row, spec["predicted_fields"]), dimension)
        if not predicted_label:
            predicted_label = heuristic_prediction(row, dataset_key=dataset_key, dimension=dimension, gold_label=gold_label)
        input_text = join_fields(row, spec["text_fields"])
        if not input_text:
            continue
        normalized.append(
            normalized_record(
                task_id=clean_value(row.get("task_id") or row.get("id") or row.get("uid") or f"{dataset_key}:{index}"),
                dataset=spec["dataset"],
                dimension=dimension,
                input_text=input_text,
                context_text=join_fields(row, spec["context_fields"]),
                gold_label=gold_label,
                predicted_label=predicted_label,
                metadata=compact_metadata(row, exclude=set(spec["text_fields"] + spec["context_fields"] + spec["label_fields"])),
            )
        )
    return normalized


def normalized_record(
    *,
    task_id: str,
    dataset: str,
    dimension: str,
    input_text: str,
    context_text: str,
    gold_label: str,
    predicted_label: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score = MAPPED_SCORES.get(dimension, {}).get(gold_label)
    return {
        "schema_version": NORMALIZED_EXTERNAL_DATASET_VERSION,
        "task_id": task_id,
        "dataset": dataset,
        "dimension": dimension,
        "input_text": input_text,
        "context_text": context_text,
        "gold_label": gold_label,
        "predicted_label": predicted_label,
        "mapped_score": score,
        "metadata": metadata or {},
    }


def heuristic_prediction(row: dict[str, Any], *, dataset_key: str, dimension: str, gold_label: str) -> str:
    text = " ".join(str(row.get(key, "")) for key in row)
    tokens = set(token_list(text))
    if dimension == "actionability":
        if tokens & {"add", "clarify", "compare", "provide", "report", "run", "explain", "include", "revise"}:
            return "actionable"
        return "not_actionable"
    if dimension == "specificity":
        if tokens & {"table", "figure", "section", "baseline", "experiment", "ablation", "equation", "result"}:
            return "specific"
        return "vague"
    if dimension == "substantiation":
        context = join_fields(row, DATASET_SPECS[dataset_key]["context_fields"])
        return "substantiated" if context else "unsubstantiated"
    if dimension == "rebuttal_robustness":
        context = join_fields(row, DATASET_SPECS[dataset_key]["context_fields"]).lower()
        if any(term in context for term in ["will add", "we added", "revised", "resolved", "fixed"]):
            return "resolved_or_weakened"
        if any(term in context for term in ["clarify", "partially", "will include"]):
            return "partially_addresses"
        if context:
            return "generic_or_unclear"
        return "not_addressed"
    return gold_label


def normalize_contrasciview_label(value: Any) -> str:
    return normalize_dimension_label(value, "consensus_conflict")


def normalize_dimension_label(value: Any, dimension: str) -> str:
    text = clean_value(value).lower().replace("-", "_").replace(" ", "_")
    mapping = LABEL_NORMALIZERS.get(dimension, {})
    if text in mapping:
        return mapping[text]
    return ""


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


def first_value(row: dict[str, Any], fields: list[str]) -> Any:
    for field in fields:
        value = row.get(field)
        if clean_value(value):
            return value
    return ""


def join_fields(row: dict[str, Any], fields: list[str]) -> str:
    return join_text(row.get(field, "") for field in fields)


def join_text(values: Iterable[Any]) -> str:
    return "\n".join(clean_value(value) for value in values if clean_value(value))


def compact_metadata(row: dict[str, Any], *, exclude: set[str]) -> dict[str, Any]:
    metadata = {}
    for key, value in row.items():
        if key in exclude:
            continue
        if isinstance(value, (dict, list)):
            continue
        text = clean_value(value)
        if text and len(text) <= 200:
            metadata[key] = value
    return metadata


def summarize_normalized(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "record_count": len(records),
        "dataset_counts": dict(Counter(record.get("dataset", "") for record in records)),
        "dimension_counts": dict(Counter(record.get("dimension", "") for record in records)),
        "gold_label_counts": dict(Counter(record.get("gold_label", "") for record in records)),
        "predicted_label_counts": dict(Counter(record.get("predicted_label", "") for record in records)),
    }


def read_records(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, list):
            return payload
        for key in ("records", "items", "data", "examples"):
            if isinstance(payload.get(key), list):
                return payload[key]
        raise ValueError(f"No record list found in {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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

    generic = subparsers.add_parser("normalize")
    generic.add_argument("--dataset", choices=sorted(DATASET_SPECS), required=True)
    generic.add_argument("--input", required=True)
    generic.add_argument("--out", required=True)
    generic.add_argument("--dimension", default="")
    generic.add_argument("--limit", type=int, default=None)

    args = parser.parse_args(argv)
    if args.command == "normalize-contrasciview":
        records = normalize_contrasciview_csv(
            args.input,
            baseline=args.baseline,
            overlap_threshold=args.overlap_threshold,
            limit=args.limit,
        )
    else:
        source_records = read_records(args.input)
        records = normalize_dataset_records(
            source_records,
            dataset_key=args.dataset,
            dimension=args.dimension or None,
            limit=args.limit,
        )
    write_jsonl(args.out, records)
    summary = summarize_normalized(records)
    print(
        f"Saved {summary['record_count']} normalized records to {args.out}. "
        f"datasets={summary['dataset_counts']}; dimensions={summary['dimension_counts']}; "
        f"gold={summary['gold_label_counts']}."
    )


if __name__ == "__main__":
    main()
