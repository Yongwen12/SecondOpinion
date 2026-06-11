from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


COMPONENT_BENCHMARK_VERSION = "component-benchmark-v0.1"


def benchmark_classification(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for record in records:
        gold = str(record.get("gold_label", ""))
        predicted = str(record.get("predicted_label", ""))
        rows.append(
            {
                "task_id": record.get("task_id", ""),
                "dataset": record.get("dataset", ""),
                "split": record.get("split", ""),
                "gold_label": gold,
                "predicted_label": predicted,
                "correct": bool(gold and predicted and gold == predicted),
            }
        )
    return build_classification_report(rows)


def build_classification_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold_counts = Counter(row["gold_label"] for row in rows if row["gold_label"])
    pred_counts = Counter(row["predicted_label"] for row in rows if row["predicted_label"])
    labels = sorted(set(gold_counts) | set(pred_counts))
    per_label = {}
    for label in labels:
        tp = sum(1 for row in rows if row["gold_label"] == label and row["predicted_label"] == label)
        fp = sum(1 for row in rows if row["gold_label"] != label and row["predicted_label"] == label)
        fn = sum(1 for row in rows if row["gold_label"] == label and row["predicted_label"] != label)
        per_label[label] = precision_recall_f1(tp, fp, fn)
    return {
        "schema_version": COMPONENT_BENCHMARK_VERSION,
        "task_type": "classification",
        "summary": {
            "record_count": len(rows),
            "accuracy": rate(sum(1 for row in rows if row["correct"]), len(rows)),
            "majority_baseline": majority_baseline(gold_counts),
            "balanced_accuracy": round(mean(item["recall"] for item in per_label.values()), 4),
            "macro_f1": round(mean(item["f1"] for item in per_label.values()), 4),
            "gold_label_counts": dict(gold_counts),
            "predicted_label_counts": dict(pred_counts),
        },
        "per_label": per_label,
        "by_dataset": grouped_classification(rows, "dataset"),
        "by_split": grouped_classification(rows, "split"),
        "examples": {
            "errors": [row for row in rows if not row["correct"]][:20],
        },
        "rows": rows,
    }


def grouped_classification(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get(key):
            groups[str(row[key])].append(row)
    return {
        name: {
            "record_count": len(group),
            "accuracy": rate(sum(1 for row in group if row["correct"]), len(group)),
        }
        for name, group in sorted(groups.items())
    }


def benchmark_alignment(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for record in records:
        gold = normalize_id_set(record.get("gold_ids", record.get("gold_response_ids", [])))
        predicted = normalize_id_list(record.get("predicted_ids", record.get("predicted_response_ids", [])))
        predicted_set = set(predicted)
        overlap = gold & predicted_set
        rows.append(
            {
                "task_id": record.get("task_id", ""),
                "dataset": record.get("dataset", ""),
                "split": record.get("split", ""),
                "gold_ids": sorted(gold),
                "predicted_ids": predicted,
                "exact_match": bool(gold) and gold == predicted_set,
                "any_overlap": bool(overlap),
                "precision": rate(len(overlap), len(predicted_set)),
                "recall": rate(len(overlap), len(gold)),
                "f1": f1(rate(len(overlap), len(predicted_set)), rate(len(overlap), len(gold))),
            }
        )
    return build_alignment_report(rows)


def build_alignment_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": COMPONENT_BENCHMARK_VERSION,
        "task_type": "alignment",
        "summary": {
            "record_count": len(rows),
            "exact_match_rate": rate(sum(1 for row in rows if row["exact_match"]), len(rows)),
            "any_overlap_rate": rate(sum(1 for row in rows if row["any_overlap"]), len(rows)),
            "mean_precision": round(mean(row["precision"] for row in rows), 4),
            "mean_recall": round(mean(row["recall"] for row in rows), 4),
            "mean_f1": round(mean(row["f1"] for row in rows), 4),
        },
        "by_dataset": grouped_alignment(rows, "dataset"),
        "by_split": grouped_alignment(rows, "split"),
        "examples": {
            "misses": [row for row in rows if not row["any_overlap"]][:20],
        },
        "rows": rows,
    }


def grouped_alignment(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get(key):
            groups[str(row[key])].append(row)
    return {
        name: {
            "record_count": len(group),
            "any_overlap_rate": rate(sum(1 for row in group if row["any_overlap"]), len(group)),
            "mean_f1": round(mean(row["f1"] for row in group), 4),
        }
        for name, group in sorted(groups.items())
    }


def precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, Any]:
    precision = rate(tp, tp + fp)
    recall = rate(tp, tp + fn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1(precision, recall),
    }


def render_markdown(report: dict[str, Any]) -> str:
    task_type = report.get("task_type", "")
    summary = report.get("summary", {})
    lines = [
        "# Component Benchmark",
        "",
        f"- Task type: `{task_type}`",
        f"- Records: {summary.get('record_count', 0)}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in summary.items():
        if isinstance(value, dict):
            continue
        lines.append(f"| `{key}` | {format_metric(value)} |")
    if task_type == "classification":
        lines.extend(["", "## Label Counts", ""])
        lines.append(f"- Gold: `{json.dumps(summary.get('gold_label_counts', {}), sort_keys=True)}`")
        lines.append(f"- Predicted: `{json.dumps(summary.get('predicted_label_counts', {}), sort_keys=True)}`")
        lines.extend(["", "## Per Label", "", "| Label | Precision | Recall | F1 | TP | FP | FN |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
        for label, item in report.get("per_label", {}).items():
            lines.append(
                f"| `{label}` | {item.get('precision', 0.0):.3f} | {item.get('recall', 0.0):.3f} | "
                f"{item.get('f1', 0.0):.3f} | {item.get('tp', 0)} | {item.get('fp', 0)} | {item.get('fn', 0)} |"
            )
    lines.extend(["", "## Notes", ""])
    lines.append("- This benchmark validates component outputs only. It does not validate core materiality or substantive resolution unless the input gold labels explicitly come from that construct.")
    return "\n".join(lines) + "\n"


def normalize_id_set(value: Any) -> set[str]:
    return set(normalize_id_list(value))


def normalize_id_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in value if str(item)]


def f1(precision: float, recall: float) -> float:
    if precision + recall <= 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def majority_baseline(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    return rate(max(counts.values(), default=0), total)


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def mean(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(float(value) for value in items) / len(items)


def format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark external component predictions against normalized gold JSONL.")
    parser.add_argument("--input", required=True, help="Normalized benchmark JSONL.")
    parser.add_argument("--task-type", choices=["classification", "alignment"], required=True)
    parser.add_argument("--out", default="data/validation/component_benchmark.json")
    parser.add_argument("--markdown", default="reports/validation/component_benchmark.md")
    args = parser.parse_args(argv)

    records = read_jsonl(args.input)
    if args.task_type == "classification":
        report = benchmark_classification(records)
    else:
        report = benchmark_alignment(records)
    write_json(args.out, report)
    write_markdown(args.markdown, report)
    print(f"Saved {args.task_type} component benchmark to {args.out} and {args.markdown}.")


if __name__ == "__main__":
    main()
