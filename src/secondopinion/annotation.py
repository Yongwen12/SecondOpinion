from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from .model_config import DEFAULT_CHEAP_MODEL

ANNOTATION_TASK_VERSION = "annotation-task-v0.1"
ANNOTATION_LABEL_VERSION = "annotation-label-v0.1"
ANNOTATION_LLM_PROMPT_VERSION = "annotation-llm-label-v0.1"
DEFAULT_ANNOTATION_MODEL = DEFAULT_CHEAP_MODEL

TASK_TYPES = (
    "claim_quality",
    "evidence_relevance",
    "verdict_correctness",
    "review_audit_quality",
    "evidence_chain_quality",
)
EXTERNAL_EVIDENCE_SOURCE_TYPES = ("venue_guideline", "external_reference", "field_consensus")
CLAIM_TYPES = (
    "ablation",
    "baseline",
    "experiment",
    "methodology",
    "theory",
    "novelty",
    "clarity",
    "writing",
    "ethics",
    "tone",
    "general",
)
CLAIM_VALID_VALUES = ("valid", "invalid", "unclear")
CLAIM_ERROR_TYPES = (
    "none",
    "not_a_claim",
    "too_broad",
    "too_narrow",
    "over_split",
    "under_split",
    "hallucinated",
    "wrong_type",
    "other",
)
TRIAGE_VALUES = ("yes", "no", "unclear")
EVIDENCE_RELEVANCE_VALUES = ("high", "medium", "low", "irrelevant", "unclear")
EVIDENCE_ERROR_TYPES = (
    "none",
    "irrelevant",
    "weakly_related",
    "wrong_section",
    "missed_appendix",
    "needs_external_reference",
    "needs_venue_guideline",
    "other",
)
VERDICT_VALUES = (
    "supported",
    "partially_supported",
    "insufficient",
    "possibly_contradicted",
    "vague_or_not_checkable",
    "needs_human_check",
    "unclear",
)
CONFIDENCE_VALUES = ("high", "medium", "low", "unclear")
EXPERT_TRIAGE_VALUES = ("yes", "partial", "no")
EVIDENCE_SUPPORT_VALUES = ("supports", "mixed", "contradicts", "insufficient")
CLAIM_IMPORTANCE_VALUES = ("high", "medium", "low")
REBUTTAL_ADDRESS_VALUES = ("resolved", "partially_addressed", "generic_or_unclear", "not_addressed")
RECOMMENDED_ACTION_VALUES = ("must_address", "clarify", "provide_evidence", "deprioritize", "ignore_or_low_priority")

PRIMARY_LABEL_FIELDS = {
    "claim_quality": ("claim_valid", "claim_type_correct", "correct_claim_type"),
    "evidence_relevance": ("evidence_relevance", "evidence_error_type"),
    "verdict_correctness": ("verdict_correct", "correct_verdict", "confidence_correct"),
    "review_audit_quality": ("rqs_reasonable", "main_issue_detected", "needs_human_expert"),
    "evidence_chain_quality": (
        "claim_extraction_correct",
        "claim_grounded",
        "evidence_supports_claim",
        "rebuttal_addresses_claim",
        "recommended_action",
    ),
}


def stable_id(prefix: str, *parts: Any) -> str:
    text = "||".join(json.dumps(part, sort_keys=True, ensure_ascii=False, default=str) for part in parts)
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def stable_run_id(audit_result: dict[str, Any]) -> str:
    dataset = str(audit_result.get("dataset") or "dataset")
    slug = "".join(char.lower() if char.isalnum() else "-" for char in dataset).strip("-") or "dataset"
    digest_payload = {
        "dataset": audit_result.get("dataset"),
        "audit_count": audit_result.get("audit_count"),
        "model_version": audit_result.get("model_version"),
        "claim_extraction_version": audit_result.get("claim_extraction_version"),
        "judge_version": audit_result.get("judge_version"),
        "retrieval_version": audit_result.get("retrieval_version"),
        "audits": [
            {
                "audit_id": audit.get("audit_id"),
                "review_id": audit.get("review_id"),
                "paper_id": audit.get("paper_id"),
                "claim_ids": [claim.get("claim_id") for claim in audit.get("claims", [])],
            }
            for audit in audit_result.get("audits", [])
        ],
    }
    return f"{slug}_{stable_id('run', digest_payload).split('_', 1)[1]}"


def annotation_provenance(audit_result: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "dataset": audit_result.get("dataset", "unknown"),
        "audit_schema_version": audit_result.get("schema_version"),
        "model_version": audit_result.get("model_version"),
        "rubric_version": audit_result.get("rubric_version"),
        "claim_extraction_version": audit_result.get("claim_extraction_version"),
        "claim_model": audit_result.get("claim_model"),
        "judge_version": audit_result.get("judge_version"),
        "judge_model": audit_result.get("judge_model"),
        "retrieval_version": audit_result.get("retrieval_version"),
        "reserved_external_evidence_source_types": list(EXTERNAL_EVIDENCE_SOURCE_TYPES),
    }


def export_annotation_tasks(audit_result: dict[str, Any], *, run_id: str | None = None) -> tuple[str, list[dict[str, Any]]]:
    run_id = run_id or stable_run_id(audit_result)
    provenance = annotation_provenance(audit_result, run_id)
    tasks: list[dict[str, Any]] = []
    for audit in audit_result.get("audits", []):
        tasks.append(review_task(run_id, audit, provenance))
        for claim in audit.get("claims", []):
            tasks.append(claim_task(run_id, audit, claim, provenance))
            if claim.get("evidence"):
                tasks.append(evidence_task(run_id, audit, claim, claim["evidence"][0], provenance))
            tasks.append(verdict_task(run_id, audit, claim, provenance))
    return run_id, tasks


def export_evidence_chain_annotation_tasks(
    evidence_chain_demo: dict[str, Any],
    *,
    run_id: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    run_id = run_id or stable_id("evidence_chain", evidence_chain_demo.get("paper", {}), evidence_chain_demo.get("summary", {}))
    provenance = {
        "run_id": run_id,
        "dataset": evidence_chain_demo.get("paper", {}).get("paper_id", "evidence-chain-demo"),
        "audit_schema_version": evidence_chain_demo.get("source", {}).get("audit_schema_version", ""),
        "model_version": "",
        "rubric_version": "",
        "claim_extraction_version": "",
        "claim_model": "",
        "judge_version": "",
        "judge_model": "",
        "retrieval_version": "",
        "reserved_external_evidence_source_types": list(EXTERNAL_EVIDENCE_SOURCE_TYPES),
    }
    tasks = []
    paper = evidence_chain_demo.get("paper", {})
    for reviewer in evidence_chain_demo.get("reviewers", []):
        audit = {
            "audit_id": f"evidence-chain:{reviewer.get('review_id', '')}",
            "paper_id": paper.get("paper_id", ""),
            "review_id": reviewer.get("review_id", ""),
            "summary": reviewer.get("summary", ""),
        }
        for claim in reviewer.get("claims", []):
            tasks.append(evidence_chain_task(run_id, audit, claim, paper, reviewer, provenance))
    return run_id, tasks


def export_evidence_chain_benchmark_annotation_tasks(
    benchmark: dict[str, Any],
    *,
    run_id: str | None = None,
    sample_size: int | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    run_id = run_id or stable_id("evidence_chain_benchmark", benchmark.get("summary", {}))
    provenance = {
        "run_id": run_id,
        "dataset": "evidence-chain-benchmark",
        "audit_schema_version": benchmark.get("schema_version", ""),
        "model_version": "",
        "rubric_version": "",
        "claim_extraction_version": "",
        "claim_model": "",
        "judge_version": "",
        "judge_model": "",
        "retrieval_version": "",
        "reserved_external_evidence_source_types": list(EXTERNAL_EVIDENCE_SOURCE_TYPES),
    }
    tasks = []
    items = benchmark.get("items", [])
    if sample_size is not None:
        items = items[: max(0, sample_size)]
    for item in items:
        full = item.get("variants", {}).get("full_evidence_chain", {})
        paper = item.get("paper", {})
        reviewer = {
            "review_id": item.get("review_id", ""),
            "rating": full.get("rating"),
            "confidence": full.get("confidence"),
            "review_reliability_score": full.get("scores", {}).get("reviewer_reliability"),
        }
        claim = {
            "claim_id": item.get("claim_id", ""),
            "claim_text": item.get("claim_text", ""),
            "source_sentence": item.get("source_sentence", ""),
            "claim_type": item.get("claim_type", ""),
            "importance": full.get("importance", ""),
            "stance": item.get("expected", {}).get("stance", ""),
            "verdict": "",
            "scores": full.get("scores", {}),
            "evidence_chain": full.get("evidence_chain", {}),
            "system_judgment": {
                "issue_flags": [],
                "benchmark_expected": item.get("expected", {}),
            },
            "rebuttal_guidance": full.get("rebuttal_guidance", {}),
        }
        audit = {
            "audit_id": f"evidence-chain-benchmark:{item.get('task_id', '')}",
            "paper_id": paper.get("paper_id", ""),
            "review_id": item.get("review_id", ""),
            "summary": "",
        }
        tasks.append(evidence_chain_task(run_id, audit, claim, paper, reviewer, provenance))
    return run_id, tasks


def base_task(run_id: str, audit: dict[str, Any], claim: dict[str, Any] | None, task_type: str, provenance: dict[str, Any]) -> dict[str, Any]:
    claim_id = claim.get("claim_id") if claim else None
    return {
        "task_id": stable_id("task", run_id, task_type, audit.get("paper_id"), audit.get("review_id"), claim_id),
        "run_id": run_id,
        "paper_id": audit.get("paper_id", ""),
        "review_id": audit.get("review_id", ""),
        "claim_id": claim_id,
        "task_type": task_type,
        "context": {},
        "system_output": {},
        "provenance": {
            **provenance,
            "annotation_task_version": ANNOTATION_TASK_VERSION,
            "audit_id": audit.get("audit_id"),
        },
    }


def claim_task(run_id: str, audit: dict[str, Any], claim: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    task = base_task(run_id, audit, claim, "claim_quality", provenance)
    task["context"] = {
        "source_field": claim.get("source_field"),
        "source_sentence_index": claim.get("source_sentence_index"),
        "source_locator": claim.get("source_locator"),
        "source_char_start": claim.get("source_char_start"),
        "source_char_end": claim.get("source_char_end"),
        "source_paragraph_index": claim.get("source_paragraph_index"),
        "source_bullet_index": claim.get("source_bullet_index"),
        "source_sentence": claim.get("source_sentence"),
        "review_summary": audit.get("summary"),
    }
    task["system_output"] = {
        "claim_text": claim.get("claim_text"),
        "claim_type": claim.get("claim_type"),
        "importance": claim.get("importance"),
        "extraction_reason": claim.get("extraction_reason"),
        "extraction_version": claim.get("extraction_version"),
    }
    return task


def evidence_task(
    run_id: str,
    audit: dict[str, Any],
    claim: dict[str, Any],
    evidence: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    task = base_task(run_id, audit, claim, "evidence_relevance", provenance)
    task["task_id"] = stable_id(
        "task",
        run_id,
        "evidence_relevance",
        audit.get("paper_id"),
        audit.get("review_id"),
        claim.get("claim_id"),
        evidence.get("evidence_id"),
    )
    task["context"] = {
        "claim_text": claim.get("claim_text"),
        "claim_type": claim.get("claim_type"),
        "source_sentence": claim.get("source_sentence"),
    }
    task["system_output"] = {
        "evidence": evidence,
        "system_verdict": claim.get("verdict"),
        "audit_confidence": claim.get("audit_confidence"),
    }
    return task


def verdict_task(run_id: str, audit: dict[str, Any], claim: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    task = base_task(run_id, audit, claim, "verdict_correctness", provenance)
    task["context"] = {
        "claim_text": claim.get("claim_text"),
        "claim_type": claim.get("claim_type"),
        "source_sentence": claim.get("source_sentence"),
        "top_evidence": (claim.get("evidence") or [None])[0],
    }
    task["system_output"] = {
        "verdict": claim.get("verdict"),
        "audit_confidence": claim.get("audit_confidence"),
        "issue_flags": claim.get("issue_flags", []),
        "evidence_support": claim.get("evidence_support"),
        "factual_alignment": claim.get("factual_alignment"),
    }
    return task


def review_task(run_id: str, audit: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    task = base_task(run_id, audit, None, "review_audit_quality", provenance)
    task["context"] = {
        "review_id": audit.get("review_id"),
        "paper_id": audit.get("paper_id"),
        "claim_count": len(audit.get("claims", [])),
        "claim_summaries": [
            {
                "claim_id": claim.get("claim_id"),
                "claim_text": claim.get("claim_text"),
                "verdict": claim.get("verdict"),
                "issue_flags": claim.get("issue_flags", []),
            }
            for claim in audit.get("claims", [])
        ],
    }
    task["system_output"] = {
        "rqs_score": audit.get("rqs_score"),
        "audit_confidence": audit.get("audit_confidence"),
        "issue_flags": audit.get("issue_flags", []),
        "summary": audit.get("summary"),
        "dimensions": audit.get("dimensions", {}),
    }
    return task


def evidence_chain_task(
    run_id: str,
    audit: dict[str, Any],
    claim: dict[str, Any],
    paper: dict[str, Any],
    reviewer: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    task = base_task(run_id, audit, claim, "evidence_chain_quality", provenance)
    task["context"] = {
        "paper": paper,
        "reviewer": {
            "review_id": reviewer.get("review_id", ""),
            "rating": reviewer.get("rating"),
            "confidence": reviewer.get("confidence"),
            "review_reliability_score": reviewer.get("review_reliability_score"),
        },
        "claim_text": claim.get("claim_text", ""),
        "source_sentence": claim.get("source_sentence", ""),
        "evidence_chain": claim.get("evidence_chain", {}),
    }
    task["system_output"] = {
        "stance": claim.get("stance", ""),
        "verdict": claim.get("verdict", ""),
        "claim_type": claim.get("claim_type", ""),
        "importance": claim.get("importance", ""),
        "scores": claim.get("scores", {}),
        "system_judgment": claim.get("system_judgment", {}),
        "rebuttal_guidance": claim.get("rebuttal_guidance", {}),
    }
    return task


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    items = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"Invalid JSONL object at {path}:{line_number}")
            items.append(item)
    return items


def write_jsonl(path: str | Path, items: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def default_task_paths(run_id: str) -> dict[str, str]:
    return {
        "tasks": f"data/annotations/tasks/{run_id}.jsonl",
        "html": f"reports/annotations/{run_id}.html",
        "llm_labels": f"data/annotations/labels/llm/{run_id}.jsonl",
        "comparison": f"data/annotations/comparisons/{run_id}.json",
        "comparison_markdown": f"reports/annotations/{run_id}_comparison.md",
        "comparison_html": f"reports/annotations/{run_id}_comparison.html",
    }


def label_id(task_id: str, annotator_type: str, annotator_id: str) -> str:
    return stable_id("ann", task_id, annotator_type, annotator_id, ANNOTATION_LABEL_VERSION)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def validate_label(label: dict[str, Any]) -> list[str]:
    errors = []
    required = [
        "annotation_id",
        "task_id",
        "task_type",
        "annotator_type",
        "annotator_id",
        "label_schema_version",
        "labels",
        "notes",
        "created_at",
        "llm_label_visible",
    ]
    for key in required:
        if key not in label:
            errors.append(f"missing:{key}")
    if errors:
        return errors
    if label["task_type"] not in TASK_TYPES:
        errors.append("invalid:task_type")
    if label["annotator_type"] not in {"human", "llm"}:
        errors.append("invalid:annotator_type")
    if label["label_schema_version"] != ANNOTATION_LABEL_VERSION:
        errors.append("invalid:label_schema_version")
    if not isinstance(label["llm_label_visible"], bool):
        errors.append("invalid:llm_label_visible")
    if not isinstance(label["labels"], dict):
        errors.append("invalid:labels")
        return errors
    errors.extend(validate_label_payload(label["task_type"], label["labels"]))
    return errors


def validate_label_payload(task_type: str, labels: dict[str, Any]) -> list[str]:
    errors = []
    if task_type == "claim_quality":
        errors.extend(_require_enum(labels, "claim_valid", CLAIM_VALID_VALUES))
        errors.extend(_require_enum(labels, "claim_error_type", CLAIM_ERROR_TYPES))
        errors.extend(_require_enum(labels, "claim_type_correct", TRIAGE_VALUES))
        errors.extend(_require_enum(labels, "correct_claim_type", CLAIM_TYPES + ("unclear",)))
    elif task_type == "evidence_relevance":
        errors.extend(_require_enum(labels, "evidence_relevance", EVIDENCE_RELEVANCE_VALUES))
        errors.extend(_require_enum(labels, "evidence_error_type", EVIDENCE_ERROR_TYPES))
        if "better_evidence" not in labels:
            errors.append("missing:labels.better_evidence")
    elif task_type == "verdict_correctness":
        errors.extend(_require_enum(labels, "verdict_correct", TRIAGE_VALUES))
        errors.extend(_require_enum(labels, "correct_verdict", VERDICT_VALUES))
        errors.extend(_require_enum(labels, "confidence_correct", TRIAGE_VALUES))
        errors.extend(_require_enum(labels, "correct_confidence", CONFIDENCE_VALUES))
    elif task_type == "review_audit_quality":
        errors.extend(_require_enum(labels, "rqs_reasonable", TRIAGE_VALUES))
        errors.extend(_require_enum(labels, "main_issue_detected", TRIAGE_VALUES))
        errors.extend(_require_enum(labels, "needs_human_expert", TRIAGE_VALUES))
        usefulness = labels.get("report_usefulness")
        if not isinstance(usefulness, int) or usefulness < 1 or usefulness > 5:
            errors.append("invalid:labels.report_usefulness")
    elif task_type == "evidence_chain_quality":
        errors.extend(_require_enum(labels, "claim_extraction_correct", EXPERT_TRIAGE_VALUES))
        errors.extend(_require_enum(labels, "claim_grounded", EXPERT_TRIAGE_VALUES))
        errors.extend(_require_enum(labels, "evidence_supports_claim", EVIDENCE_SUPPORT_VALUES))
        errors.extend(_require_enum(labels, "claim_importance", CLAIM_IMPORTANCE_VALUES))
        errors.extend(_require_enum(labels, "rebuttal_addresses_claim", REBUTTAL_ADDRESS_VALUES))
        errors.extend(_require_enum(labels, "recommended_action", RECOMMENDED_ACTION_VALUES))
        errors.extend(_require_enum(labels, "expert_confidence", CONFIDENCE_VALUES[:-1]))
    else:
        errors.append("invalid:task_type")
    return errors


def _require_enum(payload: dict[str, Any], key: str, allowed: tuple[str, ...]) -> list[str]:
    if key not in payload:
        return [f"missing:labels.{key}"]
    if payload[key] not in allowed:
        return [f"invalid:labels.{key}"]
    return []


def validate_labels(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    for index, label in enumerate(labels, start=1):
        errors = validate_label(label)
        if errors:
            issues.append({"line": index, "task_id": label.get("task_id"), "errors": errors})
    return issues


def label_schema_for_task(task_type: str) -> dict[str, Any]:
    if task_type == "claim_quality":
        labels_properties = {
            "claim_valid": {"type": "string", "enum": list(CLAIM_VALID_VALUES)},
            "claim_error_type": {"type": "string", "enum": list(CLAIM_ERROR_TYPES)},
            "claim_type_correct": {"type": "string", "enum": list(TRIAGE_VALUES)},
            "correct_claim_type": {"type": "string", "enum": list(CLAIM_TYPES + ("unclear",))},
        }
    elif task_type == "evidence_relevance":
        labels_properties = {
            "evidence_relevance": {"type": "string", "enum": list(EVIDENCE_RELEVANCE_VALUES)},
            "evidence_error_type": {"type": "string", "enum": list(EVIDENCE_ERROR_TYPES)},
            "better_evidence": {"type": "string"},
        }
    elif task_type == "verdict_correctness":
        labels_properties = {
            "verdict_correct": {"type": "string", "enum": list(TRIAGE_VALUES)},
            "correct_verdict": {"type": "string", "enum": list(VERDICT_VALUES)},
            "confidence_correct": {"type": "string", "enum": list(TRIAGE_VALUES)},
            "correct_confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES)},
        }
    elif task_type == "review_audit_quality":
        labels_properties = {
            "rqs_reasonable": {"type": "string", "enum": list(TRIAGE_VALUES)},
            "main_issue_detected": {"type": "string", "enum": list(TRIAGE_VALUES)},
            "needs_human_expert": {"type": "string", "enum": list(TRIAGE_VALUES)},
            "report_usefulness": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        }
    elif task_type == "evidence_chain_quality":
        labels_properties = {
            "claim_extraction_correct": {"type": "string", "enum": list(EXPERT_TRIAGE_VALUES)},
            "claim_grounded": {"type": "string", "enum": list(EXPERT_TRIAGE_VALUES)},
            "evidence_supports_claim": {"type": "string", "enum": list(EVIDENCE_SUPPORT_VALUES)},
            "claim_importance": {"type": "string", "enum": list(CLAIM_IMPORTANCE_VALUES)},
            "rebuttal_addresses_claim": {"type": "string", "enum": list(REBUTTAL_ADDRESS_VALUES)},
            "recommended_action": {"type": "string", "enum": list(RECOMMENDED_ACTION_VALUES)},
            "expert_confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES[:-1])},
        }
    else:
        raise ValueError(f"Unsupported task type: {task_type}")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "labels": {
                "type": "object",
                "additionalProperties": False,
                "properties": labels_properties,
                "required": list(labels_properties),
            },
            "notes": {"type": "string"},
        },
        "required": ["labels", "notes"],
    }


def llm_label_task(
    task: dict[str, Any],
    *,
    llm_client: Any,
    model: str = DEFAULT_ANNOTATION_MODEL,
    annotator_id: str | None = None,
) -> dict[str, Any]:
    task_type = task["task_type"]
    annotator_id = annotator_id or f"llm:{model}"
    payload = llm_client.complete_json(
        model=model,
        messages=llm_label_messages(task),
        schema_name=f"{task_type}_annotation_label",
        schema=label_schema_for_task(task_type),
    )
    label = {
        "annotation_id": label_id(task["task_id"], "llm", annotator_id),
        "task_id": task["task_id"],
        "run_id": task["run_id"],
        "task_type": task_type,
        "annotator_type": "llm",
        "annotator_id": annotator_id,
        "label_schema_version": ANNOTATION_LABEL_VERSION,
        "labels": payload.get("labels", {}),
        "notes": str(payload.get("notes", "")),
        "created_at": utc_now(),
        "llm_label_visible": False,
        "provenance": {
            "annotation_version": ANNOTATION_LABEL_VERSION,
            "prompt_version": ANNOTATION_LLM_PROMPT_VERSION,
            "model": model,
            "temperature": 0,
        },
    }
    errors = validate_label(label)
    if errors:
        raise ValueError(f"Invalid LLM label for {task['task_id']}: {errors}")
    return label


def llm_label_tasks(
    tasks: list[dict[str, Any]],
    *,
    llm_client: Any,
    model: str = DEFAULT_ANNOTATION_MODEL,
    annotator_id: str | None = None,
) -> list[dict[str, Any]]:
    return [llm_label_task(task, llm_client=llm_client, model=model, annotator_id=annotator_id) for task in tasks]


def llm_label_messages(task: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are labeling SecondOpinion audit outputs for calibration. "
                "Return JSON matching the schema. Judge only the provided task, and do not change the system output."
            ),
        },
        {
            "role": "user",
            "content": f"Annotation task JSON:\n{json.dumps(task, ensure_ascii=False, indent=2)}",
        },
    ]


def compare_annotations(
    human_labels: list[dict[str, Any]],
    llm_labels: list[dict[str, Any]],
    *,
    tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    human_by_task = {label["task_id"]: label for label in human_labels}
    llm_by_task = {label["task_id"]: label for label in llm_labels}
    task_by_id = {task["task_id"]: task for task in tasks or []}
    common = sorted(set(human_by_task) & set(llm_by_task))
    by_type: dict[str, dict[str, Any]] = {
        task_type: {"common": 0, "exact_match": 0, "field_matches": {}, "field_totals": {}} for task_type in TASK_TYPES
    }
    disagreements = []
    for task_id in common:
        human_label = human_by_task[task_id]
        llm_label = llm_by_task[task_id]
        task_type = human_label["task_type"]
        fields = PRIMARY_LABEL_FIELDS.get(task_type, ())
        row = by_type[task_type]
        row["common"] += 1
        all_match = True
        for field in fields:
            row["field_totals"][field] = row["field_totals"].get(field, 0) + 1
            if human_label["labels"].get(field) == llm_label["labels"].get(field):
                row["field_matches"][field] = row["field_matches"].get(field, 0) + 1
            else:
                all_match = False
        if all_match:
            row["exact_match"] += 1
        else:
            disagreements.append(
                {
                    "task_id": task_id,
                    "task_type": task_type,
                    "paper_id": task_by_id.get(task_id, {}).get("paper_id"),
                    "review_id": task_by_id.get(task_id, {}).get("review_id"),
                    "claim_id": task_by_id.get(task_id, {}).get("claim_id"),
                    "human_labels": human_label["labels"],
                    "llm_labels": llm_label["labels"],
                }
            )
    for row in by_type.values():
        common_count = row["common"]
        row["exact_match_rate"] = round(row["exact_match"] / common_count, 3) if common_count else 0
        row["field_match_rates"] = {
            field: round(row["field_matches"].get(field, 0) / total, 3) if total else 0
            for field, total in row["field_totals"].items()
        }
    return {
        "schema_version": "annotation-comparison-v0.1",
        "created_at": utc_now(),
        "task_count": len(tasks or []),
        "human_label_count": len(human_labels),
        "llm_label_count": len(llm_labels),
        "common_label_count": len(common),
        "by_task_type": by_type,
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
    }


def write_comparison_markdown(comparison: dict[str, Any], path: str | Path) -> None:
    lines = [
        "# SecondOpinion Annotation Comparison",
        "",
        f"- Common labels: {comparison.get('common_label_count', 0)}",
        f"- Disagreements: {comparison.get('disagreement_count', 0)}",
        "",
        "| Task type | Common | Exact match | Rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for task_type, row in comparison.get("by_task_type", {}).items():
        lines.append(
            f"| {task_type} | {row.get('common', 0)} | {row.get('exact_match', 0)} | {row.get('exact_match_rate', 0)} |"
        )
    lines.extend(["", "## Disagreements", ""])
    for item in comparison.get("disagreements", [])[:100]:
        lines.append(f"- `{item['task_id']}` `{item['task_type']}` human={item['human_labels']} llm={item['llm_labels']}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_comparison_html(comparison: dict[str, Any], path: str | Path) -> None:
    rows = []
    for task_type, row in comparison.get("by_task_type", {}).items():
        rows.append(
            "<tr>"
            f"<td>{html.escape(task_type)}</td>"
            f"<td>{row.get('common', 0)}</td>"
            f"<td>{row.get('exact_match', 0)}</td>"
            f"<td>{row.get('exact_match_rate', 0)}</td>"
            "</tr>"
        )
    disagreements = []
    for item in comparison.get("disagreements", [])[:100]:
        disagreements.append(
            "<li>"
            f"<code>{html.escape(item['task_id'])}</code> "
            f"{html.escape(item['task_type'])} "
            f"<pre>{html.escape(json.dumps({'human': item['human_labels'], 'llm': item['llm_labels']}, ensure_ascii=False, indent=2))}</pre>"
            "</li>"
        )
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SecondOpinion Annotation Comparison</title>
  <style>
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #172026; background: #f5f7f8; }}
    header, main {{ padding: 24px clamp(20px, 5vw, 64px); }}
    header {{ background: #fff; border-bottom: 1px solid #d8dee4; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee4; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #d8dee4; text-align: left; }}
    pre {{ white-space: pre-wrap; background: #fff; border: 1px solid #d8dee4; padding: 10px; border-radius: 6px; }}
  </style>
</head>
<body>
  <header>
    <h1>Annotation Comparison</h1>
    <p>{comparison.get('common_label_count', 0)} common labels, {comparison.get('disagreement_count', 0)} disagreements.</p>
  </header>
  <main>
    <table>
      <thead><tr><th>Task type</th><th>Common</th><th>Exact match</th><th>Rate</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    <h2>Disagreements</h2>
    <ul>{''.join(disagreements) or '<li>No disagreements.</li>'}</ul>
  </main>
</body>
</html>
"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")


def write_annotation_html(tasks: list[dict[str, Any]], path: str | Path) -> None:
    data = json.dumps(tasks, ensure_ascii=False)
    task_cards = "\n".join(render_task_card(task) for task in tasks)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SecondOpinion Annotation Packet</title>
  <style>
    :root {{ --ink: #172026; --muted: #5b6670; --line: #d8dee4; --panel: #fff; --soft: #f5f7f8; --accent: #0f766e; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: var(--ink); background: var(--soft); }}
    header {{ position: sticky; top: 0; z-index: 1; padding: 18px clamp(20px, 5vw, 64px); background: var(--panel); border-bottom: 1px solid var(--line); }}
    main {{ padding: 20px clamp(20px, 5vw, 64px) 48px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
    button {{ border: 1px solid var(--accent); background: var(--accent); color: #fff; border-radius: 6px; padding: 8px 12px; cursor: pointer; }}
    .task {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin-bottom: 14px; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }}
    code, .chip {{ border: 1px solid var(--line); border-radius: 6px; padding: 3px 7px; background: #f8fafb; color: var(--muted); font-size: 12px; }}
    blockquote {{ margin: 10px 0; border-left: 3px solid var(--accent); padding: 8px 12px; background: #f0fdfa; }}
    label {{ display: block; margin: 8px 0 4px; color: var(--muted); font-size: 13px; }}
    select, textarea, input {{ width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 8px; font: inherit; background: #fff; }}
    textarea {{ min-height: 70px; }}
    pre {{ white-space: pre-wrap; background: #f8fafb; border: 1px solid var(--line); border-radius: 6px; padding: 10px; overflow: auto; }}
  </style>
</head>
<body>
  <header>
    <div class="toolbar">
      <strong>SecondOpinion Annotation Packet</strong>
      <span class="chip">{len(tasks)} tasks</span>
      <button type="button" onclick="downloadLabels()">Export JSONL</button>
    </div>
  </header>
  <main>
    {task_cards}
  </main>
  <script id="task-data" type="application/json">{html.escape(data)}</script>
  <script>
    const tasks = JSON.parse(document.getElementById('task-data').textContent);
    const nowIso = () => new Date().toISOString().replace(/\\.\\d{{3}}Z$/, '+00:00');
    function options(values, selected='') {{
      return values.map(v => `<option value="${{v}}" ${{v === selected ? 'selected' : ''}}>${{v}}</option>`).join('');
    }}
    function renderControls(task) {{
      const root = document.querySelector(`[data-task-id="${{task.task_id}}"] .controls`);
      if (task.task_type === 'claim_quality') {{
        root.innerHTML = `
          <label>Claim valid</label><select data-key="claim_valid">${{options(['valid','invalid','unclear'])}}</select>
          <label>Claim error type</label><select data-key="claim_error_type">${{options(['none','not_a_claim','too_broad','too_narrow','over_split','under_split','hallucinated','wrong_type','other'])}}</select>
          <label>Claim type correct</label><select data-key="claim_type_correct">${{options(['yes','no','unclear'])}}</select>
          <label>Correct claim type</label><select data-key="correct_claim_type">${{options(['ablation','baseline','experiment','methodology','theory','novelty','clarity','writing','ethics','tone','general','unclear'])}}</select>`;
      }} else if (task.task_type === 'evidence_relevance') {{
        root.innerHTML = `
          <label>Evidence relevance</label><select data-key="evidence_relevance">${{options(['high','medium','low','irrelevant','unclear'])}}</select>
          <label>Evidence error type</label><select data-key="evidence_error_type">${{options(['none','irrelevant','weakly_related','wrong_section','missed_appendix','needs_external_reference','needs_venue_guideline','other'])}}</select>
          <label>Better evidence</label><textarea data-key="better_evidence"></textarea>`;
      }} else if (task.task_type === 'verdict_correctness') {{
        root.innerHTML = `
          <label>Verdict correct</label><select data-key="verdict_correct">${{options(['yes','no','unclear'])}}</select>
          <label>Correct verdict</label><select data-key="correct_verdict">${{options(['supported','partially_supported','insufficient','possibly_contradicted','vague_or_not_checkable','needs_human_check','unclear'])}}</select>
          <label>Confidence correct</label><select data-key="confidence_correct">${{options(['yes','no','unclear'])}}</select>
          <label>Correct confidence</label><select data-key="correct_confidence">${{options(['high','medium','low','unclear'])}}</select>`;
      }} else if (task.task_type === 'review_audit_quality') {{
        root.innerHTML = `
          <label>RQS reasonable</label><select data-key="rqs_reasonable">${{options(['yes','no','unclear'])}}</select>
          <label>Main issue detected</label><select data-key="main_issue_detected">${{options(['yes','no','unclear'])}}</select>
          <label>Needs human expert</label><select data-key="needs_human_expert">${{options(['yes','no','unclear'])}}</select>
          <label>Report usefulness</label><select data-key="report_usefulness">${{options(['1','2','3','4','5'], '3')}}</select>`;
      }} else {{
        root.innerHTML = `
          <label>Claim extraction correct</label><select data-key="claim_extraction_correct">${{options(['yes','partial','no'])}}</select>
          <label>Claim grounded</label><select data-key="claim_grounded">${{options(['yes','partial','no'])}}</select>
          <label>Evidence supports claim</label><select data-key="evidence_supports_claim">${{options(['supports','mixed','contradicts','insufficient'])}}</select>
          <label>Claim importance</label><select data-key="claim_importance">${{options(['high','medium','low'])}}</select>
          <label>Rebuttal addresses claim</label><select data-key="rebuttal_addresses_claim">${{options(['resolved','partially_addressed','generic_or_unclear','not_addressed'])}}</select>
          <label>Recommended action</label><select data-key="recommended_action">${{options(['must_address','clarify','provide_evidence','deprioritize','ignore_or_low_priority'])}}</select>
          <label>Expert confidence</label><select data-key="expert_confidence">${{options(['high','medium','low'])}}</select>`;
      }}
      root.insertAdjacentHTML('beforeend', '<label>Notes</label><textarea data-notes="true"></textarea>');
    }}
    function collectTaskLabel(task) {{
      const card = document.querySelector(`[data-task-id="${{task.task_id}}"]`);
      const labels = {{}};
      card.querySelectorAll('[data-key]').forEach(input => {{
        labels[input.dataset.key] = input.dataset.key === 'report_usefulness' ? Number(input.value) : input.value;
      }});
      const annotatorId = document.getElementById('annotator-id').value || 'human';
      return {{
        annotation_id: `ann_${{task.task_id}}_${{annotatorId}}`,
        task_id: task.task_id,
        run_id: task.run_id,
        task_type: task.task_type,
        annotator_type: 'human',
        annotator_id: annotatorId,
        label_schema_version: 'annotation-label-v0.1',
        labels,
        notes: card.querySelector('[data-notes]').value || '',
        created_at: nowIso(),
        llm_label_visible: false
      }};
    }}
    function downloadLabels() {{
      const text = tasks.map(task => JSON.stringify(collectTaskLabel(task))).join('\\n') + '\\n';
      const blob = new Blob([text], {{type: 'application/jsonl'}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${{tasks[0]?.run_id || 'annotations'}}_human_labels.jsonl`;
      link.click();
      URL.revokeObjectURL(url);
    }}
    document.querySelector('header .toolbar').insertAdjacentHTML('beforeend', '<label style="margin:0">Annotator <input id="annotator-id" value="human"></label>');
    tasks.forEach(renderControls);
  </script>
</body>
</html>
"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")


def render_task_card(task: dict[str, Any]) -> str:
    evidence = top_evidence_text(task)
    return f"""
<section class="task" data-task-id="{html.escape(task['task_id'])}">
  <div class="meta">
    <code>{html.escape(task['task_type'])}</code>
    <code>{html.escape(task['paper_id'])}</code>
    <code>{html.escape(task['review_id'])}</code>
    <code>{html.escape(str(task.get('claim_id') or 'review'))}</code>
  </div>
  <h2>{html.escape(task_title(task))}</h2>
  <blockquote>{html.escape(source_sentence(task) or 'No source sentence.')}</blockquote>
  <pre>{html.escape(json.dumps(task['system_output'], ensure_ascii=False, indent=2))}</pre>
  {evidence}
  <div class="controls"></div>
</section>
"""


def task_title(task: dict[str, Any]) -> str:
    if task["task_type"] == "review_audit_quality":
        return f"Review audit quality for {task['review_id']}"
    if task["task_type"] == "evidence_chain_quality":
        return str(task.get("context", {}).get("claim_text") or task["task_id"])
    return str(task.get("context", {}).get("claim_text") or task.get("system_output", {}).get("claim_text") or task["task_id"])


def source_sentence(task: dict[str, Any]) -> str:
    context = task.get("context", {})
    return str(context.get("source_sentence") or "")


def top_evidence_text(task: dict[str, Any]) -> str:
    evidence = task.get("system_output", {}).get("evidence") or task.get("context", {}).get("top_evidence")
    if not evidence:
        return ""
    text = json.dumps(evidence, ensure_ascii=False, indent=2)
    return f"<h3>Evidence</h3><pre>{html.escape(text)}</pre>"
