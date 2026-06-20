from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .component_benchmark import benchmark_classification
from .retrieval import token_list


SCORING_MEMORY_VERSION = "scoring-memory-v0.1"
HYBRID_SCORING_VERSION = "hybrid-scoring-v0.1"
SCORING_SUITE_VERSION = "scoring-benchmark-suite-v0.1"

DEFAULT_LABEL_SCORE_MAPS: dict[str, dict[str, float]] = {
    "specificity": {
        "specific": 0.9,
        "partially_specific": 0.55,
        "vague": 0.15,
    },
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
    "consensus_conflict": {
        "same_concern": 0.9,
        "related_but_different": 0.55,
        "not_same_concern": 0.15,
        "not_contradiction": 0.65,
        "contradiction": 0.1,
    },
    "rebuttal_robustness": {
        "not_addressed": 0.9,
        "generic_or_unclear": 0.7,
        "partially_addresses": 0.5,
        "specifically_addressed": 0.3,
        "resolved_or_weakened": 0.1,
        "likely_resolved": 0.1,
    },
    "professionalism": {
        "professional": 0.9,
        "polite": 0.85,
        "neutral": 0.55,
        "unprofessional": 0.15,
        "impolite": 0.15,
    },
}


def build_memory_records(
    records: list[dict[str, Any]],
    *,
    dimension: str,
    dataset: str = "",
    text_fields: list[str] | None = None,
    context_fields: list[str] | None = None,
    label_field: str = "gold_label",
    score_field: str = "",
    label_score_map: dict[str, float] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    label_score_map = normalize_score_map(label_score_map or DEFAULT_LABEL_SCORE_MAPS.get(dimension, {}))
    text_fields = text_fields or ["input_text", "comment", "claim_text", "premise", "hypothesis", "review_text"]
    context_fields = context_fields or ["context_text", "paper_title", "aspect", "rebuttal", "response"]
    memory = []
    for index, record in enumerate(records):
        if limit is not None and len(memory) >= limit:
            break
        input_text = join_fields(record, text_fields)
        if not input_text:
            continue
        label = str(record.get(label_field, "") or "").strip()
        mapped_score = score_from_record(record, score_field=score_field, label=label, label_score_map=label_score_map)
        if mapped_score is None:
            continue
        dataset_name = dataset or str(record.get("dataset", "") or "external")
        task_id = str(record.get("task_id", "") or f"{dataset_name}:{index}")
        memory.append(
            {
                "schema_version": SCORING_MEMORY_VERSION,
                "memory_id": f"{dataset_name}:{dimension}:{task_id}",
                "dimension": dimension,
                "dataset": dataset_name,
                "task_id": task_id,
                "input_text": input_text,
                "context_text": join_fields(record, context_fields),
                "gold_label": label,
                "mapped_score": round(float(mapped_score), 4),
                "rationale": str(record.get("rationale", "") or record.get("explanation", "") or ""),
                "metadata": compact_metadata(record, exclude=set(text_fields + context_fields + [label_field, score_field])),
            }
        )
    return memory


def build_memory_records_from_normalized(
    records: list[dict[str, Any]],
    *,
    dimension_field: str = "dimension",
    dataset: str = "",
    text_fields: list[str] | None = None,
    context_fields: list[str] | None = None,
    label_field: str = "gold_label",
    score_field: str = "mapped_score",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    by_dimension: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        dimension = str(record.get(dimension_field, "") or "").strip()
        if dimension:
            by_dimension[dimension].append(record)
    memory = []
    for dimension, items in sorted(by_dimension.items()):
        remaining = None if limit is None else max(0, limit - len(memory))
        if remaining == 0:
            break
        memory.extend(
            build_memory_records(
                items,
                dimension=dimension,
                dataset=dataset,
                text_fields=text_fields or ["input_text"],
                context_fields=context_fields or ["context_text"],
                label_field=label_field,
                score_field=score_field,
                limit=remaining,
            )
        )
    return memory


def retrieve_memory(
    query_text: str,
    memory_records: list[dict[str, Any]],
    *,
    dimension: str = "",
    top_k: int = 5,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    query_tokens = set(token_list(query_text))
    if not query_tokens:
        return []
    candidates = []
    for record in memory_records:
        if dimension and record.get("dimension") != dimension:
            continue
        candidate_tokens = set(token_list(" ".join([str(record.get("input_text", "")), str(record.get("context_text", ""))])))
        score = jaccard(query_tokens, candidate_tokens)
        if score < min_score:
            continue
        candidates.append(
            {
                "memory_id": record.get("memory_id", ""),
                "dimension": record.get("dimension", ""),
                "dataset": record.get("dataset", ""),
                "input_text": record.get("input_text", ""),
                "context_text": record.get("context_text", ""),
                "gold_label": record.get("gold_label", ""),
                "mapped_score": record.get("mapped_score", 0.0),
                "similarity": round(score, 4),
                "rationale": record.get("rationale", ""),
                "metadata": record.get("metadata", {}),
            }
        )
    candidates.sort(key=lambda item: (item["similarity"], item.get("mapped_score", 0.0)), reverse=True)
    return candidates[:top_k]


def memory_prior(examples: list[dict[str, Any]], *, similarity_weighted: bool = True) -> dict[str, Any]:
    scored = [
        (float(example.get("mapped_score", 0.0)), max(0.0, float(example.get("similarity", 0.0))))
        for example in examples
        if example.get("mapped_score") is not None
    ]
    if not scored:
        return {
            "prior_score": None,
            "example_count": 0,
            "label_counts": {},
            "mean_similarity": 0.0,
        }
    if similarity_weighted and sum(weight for _, weight in scored) > 0:
        total_weight = sum(weight for _, weight in scored)
        prior = sum(score * weight for score, weight in scored) / total_weight
    else:
        prior = sum(score for score, _ in scored) / len(scored)
    return {
        "prior_score": round(prior, 4),
        "example_count": len(scored),
        "label_counts": dict(Counter(str(example.get("gold_label", "")) for example in examples if example.get("gold_label"))),
        "mean_similarity": round(sum(weight for _, weight in scored) / len(scored), 4),
    }


def hybrid_score(
    *,
    llm_score: float | None,
    retrieved_examples: list[dict[str, Any]],
    llm_weight: float = 0.6,
    similarity_weighted: bool = True,
) -> dict[str, Any]:
    prior = memory_prior(retrieved_examples, similarity_weighted=similarity_weighted)
    prior_score = prior["prior_score"]
    if llm_score is None and prior_score is None:
        final = None
        source = "missing"
    elif llm_score is None:
        final = prior_score
        source = "memory_prior"
    elif prior_score is None:
        final = bounded_score(llm_score)
        source = "llm_only"
    else:
        weight = min(1.0, max(0.0, llm_weight))
        final = weight * bounded_score(llm_score) + (1.0 - weight) * prior_score
        source = "hybrid"
    return {
        "schema_version": HYBRID_SCORING_VERSION,
        "final_score": None if final is None else round(final, 4),
        "llm_score": None if llm_score is None else bounded_score(llm_score),
        "llm_weight": round(min(1.0, max(0.0, llm_weight)), 4),
        "memory_prior": prior,
        "source": source,
        "retrieved_examples": retrieved_examples,
    }


def score_with_memory(
    *,
    query_text: str,
    memory_records: list[dict[str, Any]],
    dimension: str,
    llm_score: float | None = None,
    top_k: int = 5,
    llm_weight: float = 0.6,
    min_similarity: float = 0.0,
) -> dict[str, Any]:
    examples = retrieve_memory(query_text, memory_records, dimension=dimension, top_k=top_k, min_score=min_similarity)
    result = hybrid_score(llm_score=llm_score, retrieved_examples=examples, llm_weight=llm_weight)
    result.update(
        {
            "dimension": dimension,
            "query_text": query_text,
            "top_k": top_k,
            "min_similarity": min_similarity,
        }
    )
    return result


def score_dimensions_with_memory(
    *,
    query_text: str,
    memory_records: list[dict[str, Any]],
    llm_scores: dict[str, float | None] | None = None,
    dimensions: list[str] | None = None,
    top_k: int = 5,
    llm_weight: float = 0.6,
    min_similarity: float = 0.0,
) -> dict[str, Any]:
    dimensions = dimensions or list(DEFAULT_LABEL_SCORE_MAPS)
    llm_scores = llm_scores or {}
    scores = {}
    for dimension in dimensions:
        scores[dimension] = score_with_memory(
            query_text=query_text,
            memory_records=memory_records,
            dimension=dimension,
            llm_score=llm_scores.get(dimension),
            top_k=top_k,
            llm_weight=llm_weight,
            min_similarity=min_similarity,
        )
    final_scores = [
        result["final_score"]
        for result in scores.values()
        if result.get("final_score") is not None
    ]
    return {
        "schema_version": HYBRID_SCORING_VERSION,
        "query_text": query_text,
        "top_k": top_k,
        "llm_weight": round(min(1.0, max(0.0, llm_weight)), 4),
        "overall_score": round(sum(final_scores) / len(final_scores), 4) if final_scores else None,
        "hybrid_scores": scores,
    }


def build_scoring_benchmark_suite(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_dimension: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_dimension[str(record.get("dimension", "") or "unknown")].append(record)
    dimension_reports = {
        dimension: benchmark_classification(rows)
        for dimension, rows in sorted(by_dimension.items())
    }
    overall = benchmark_classification(records)
    return {
        "schema_version": SCORING_SUITE_VERSION,
        "task_type": "scoring_dimension_classification",
        "summary": {
            "record_count": len(records),
            "dimension_count": len(dimension_reports),
            "dimensions": sorted(dimension_reports),
            "accuracy": overall["summary"]["accuracy"],
            "macro_f1": overall["summary"]["macro_f1"],
            "gold_label_counts": overall["summary"]["gold_label_counts"],
            "predicted_label_counts": overall["summary"]["predicted_label_counts"],
        },
        "overall": overall,
        "by_dimension": dimension_reports,
    }


def render_scoring_suite_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Scoring Memory Benchmark Suite",
        "",
        f"- Records: {summary.get('record_count', 0)}",
        f"- Dimensions: {summary.get('dimension_count', 0)}",
        f"- Overall accuracy: {format_optional(summary.get('accuracy'))}",
        f"- Overall macro F1: {format_optional(summary.get('macro_f1'))}",
        "",
        "## By Dimension",
        "",
        "| Dimension | Records | Accuracy | Macro F1 | Majority baseline |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for dimension, item in report.get("by_dimension", {}).items():
        item_summary = item.get("summary", {})
        lines.append(
            f"| `{dimension}` | {item_summary.get('record_count', 0)} | "
            f"{format_optional(item_summary.get('accuracy'))} | {format_optional(item_summary.get('macro_f1'))} | "
            f"{format_optional(item_summary.get('majority_baseline'))} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This suite checks external component labels used as scoring memory.",
            "- It is a regression guardrail for the scorer, not proof that reviewer comments are objectively correct.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_guardrail_report(
    current_report: dict[str, Any],
    *,
    baseline_report: dict[str, Any] | None = None,
    min_accuracy: float | None = None,
    min_macro_f1: float | None = None,
    max_accuracy_drop: float = 0.02,
    max_macro_f1_drop: float = 0.02,
) -> dict[str, Any]:
    current = current_report.get("summary", {})
    baseline = (baseline_report or {}).get("summary", {})
    checks = []
    checks.append(threshold_check("accuracy_min", current.get("accuracy"), min_accuracy, direction="min"))
    checks.append(threshold_check("macro_f1_min", current.get("macro_f1"), min_macro_f1, direction="min"))
    checks.append(drop_check("accuracy_drop", current.get("accuracy"), baseline.get("accuracy"), max_accuracy_drop))
    checks.append(drop_check("macro_f1_drop", current.get("macro_f1"), baseline.get("macro_f1"), max_macro_f1_drop))
    active_checks = [check for check in checks if check["status"] != "skipped"]
    return {
        "schema_version": "scoring-guardrail-v0.1",
        "status": "pass" if all(check["passed"] for check in active_checks) else "fail",
        "current_summary": current,
        "baseline_summary": baseline,
        "checks": checks,
    }


def render_guardrail_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Scoring Benchmark Guardrail",
        "",
        f"- Status: `{report.get('status', 'unknown')}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Current | Baseline / Threshold | Limit |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for check in report.get("checks", []):
        lines.append(
            f"| `{check['name']}` | `{check['status']}` | {format_optional(check.get('current'))} | "
            f"{format_optional(check.get('baseline_or_threshold'))} | {format_optional(check.get('limit'))} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Guardrails are for benchmark regression only. They do not prove the scoring construct is correct.",
            "- Use this after prompt, retrieval, adapter, or scoring-weight changes.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, markdown: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").split("\n") if line.strip()]


def parse_fields(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_label_score_map(items: list[str] | None) -> dict[str, float]:
    mapping = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"Expected label=score mapping, got {item!r}")
        label, score = item.split("=", 1)
        mapping[label.strip()] = bounded_score(float(score.strip()))
    return mapping


def join_fields(record: dict[str, Any], fields: list[str]) -> str:
    values = []
    for field in fields:
        value = record.get(field)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            values.extend(str(item).strip() for item in value if str(item).strip())
        else:
            text = str(value).strip()
            if text:
                values.append(text)
    return "\n".join(values)


def score_from_record(
    record: dict[str, Any],
    *,
    score_field: str,
    label: str,
    label_score_map: dict[str, float],
) -> float | None:
    if score_field and record.get(score_field) is not None:
        return bounded_score(float(record[score_field]))
    normalized_label = label.strip().lower()
    if normalized_label in label_score_map:
        return label_score_map[normalized_label]
    return None


def normalize_score_map(mapping: dict[str, float]) -> dict[str, float]:
    return {str(key).strip().lower(): bounded_score(float(value)) for key, value in mapping.items()}


def compact_metadata(record: dict[str, Any], *, exclude: set[str]) -> dict[str, Any]:
    metadata = {}
    for key, value in record.items():
        if key in exclude or isinstance(value, (dict, list)):
            continue
        text = str(value)
        if len(text) <= 200:
            metadata[key] = value
    return metadata


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def bounded_score(value: float) -> float:
    return round(min(1.0, max(0.0, float(value))), 4)


def threshold_check(name: str, current: Any, threshold: float | None, *, direction: str) -> dict[str, Any]:
    if threshold is None or current is None:
        return {
            "name": name,
            "status": "skipped",
            "passed": True,
            "current": current,
            "baseline_or_threshold": threshold,
            "limit": None,
        }
    current_value = float(current)
    passed = current_value >= threshold if direction == "min" else current_value <= threshold
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "current": current_value,
        "baseline_or_threshold": threshold,
        "limit": threshold,
    }


def drop_check(name: str, current: Any, baseline: Any, max_drop: float) -> dict[str, Any]:
    if current is None or baseline is None:
        return {
            "name": name,
            "status": "skipped",
            "passed": True,
            "current": current,
            "baseline_or_threshold": baseline,
            "limit": max_drop,
        }
    drop = float(baseline) - float(current)
    passed = drop <= max_drop
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "current": float(current),
        "baseline_or_threshold": float(baseline),
        "limit": max_drop,
        "drop": round(drop, 4),
    }


def format_optional(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build and use external scoring memory for reviewer comment scoring.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-memory")
    build.add_argument("--input", required=True)
    build.add_argument("--out", required=True)
    build.add_argument("--dimension", required=True)
    build.add_argument("--dataset", default="")
    build.add_argument("--text-fields", default="input_text,comment,claim_text,premise,hypothesis,review_text")
    build.add_argument("--context-fields", default="context_text,paper_title,aspect,rebuttal,response")
    build.add_argument("--label-field", default="gold_label")
    build.add_argument("--score-field", default="")
    build.add_argument("--label-score", action="append", default=[])
    build.add_argument("--limit", type=int, default=None)

    retrieve = subparsers.add_parser("retrieve")
    retrieve.add_argument("--memory", required=True)
    retrieve.add_argument("--query", required=True)
    retrieve.add_argument("--dimension", required=True)
    retrieve.add_argument("--out", default="")
    retrieve.add_argument("--top-k", type=int, default=5)
    retrieve.add_argument("--llm-score", type=float, default=None)
    retrieve.add_argument("--llm-weight", type=float, default=0.6)
    retrieve.add_argument("--min-similarity", type=float, default=0.0)

    guardrail = subparsers.add_parser("guardrail")
    guardrail.add_argument("--current", required=True)
    guardrail.add_argument("--baseline", default="")
    guardrail.add_argument("--out", required=True)
    guardrail.add_argument("--markdown", default="")
    guardrail.add_argument("--min-accuracy", type=float, default=None)
    guardrail.add_argument("--min-macro-f1", type=float, default=None)
    guardrail.add_argument("--max-accuracy-drop", type=float, default=0.02)
    guardrail.add_argument("--max-macro-f1-drop", type=float, default=0.02)

    args = parser.parse_args(argv)
    if args.command == "build-memory":
        records = read_jsonl(args.input)
        memory = build_memory_records(
            records,
            dimension=args.dimension,
            dataset=args.dataset,
            text_fields=parse_fields(args.text_fields),
            context_fields=parse_fields(args.context_fields),
            label_field=args.label_field,
            score_field=args.score_field,
            label_score_map=parse_label_score_map(args.label_score) or None,
            limit=args.limit,
        )
        write_jsonl(args.out, memory)
        print(f"Saved {len(memory)} scoring-memory records to {args.out}.")
    elif args.command == "retrieve":
        memory = read_jsonl(args.memory)
        result = score_with_memory(
            query_text=args.query,
            memory_records=memory,
            dimension=args.dimension,
            llm_score=args.llm_score,
            top_k=args.top_k,
            llm_weight=args.llm_weight,
            min_similarity=args.min_similarity,
        )
        if args.out:
            write_json(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.command == "guardrail":
        current = read_json(args.current)
        baseline = read_json(args.baseline) if args.baseline else None
        report = build_guardrail_report(
            current,
            baseline_report=baseline,
            min_accuracy=args.min_accuracy,
            min_macro_f1=args.min_macro_f1,
            max_accuracy_drop=args.max_accuracy_drop,
            max_macro_f1_drop=args.max_macro_f1_drop,
        )
        write_json(args.out, report)
        if args.markdown:
            Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
            Path(args.markdown).write_text(render_guardrail_markdown(report), encoding="utf-8")
        print(f"Guardrail {report['status']}: saved to {args.out}.")


if __name__ == "__main__":
    main()
