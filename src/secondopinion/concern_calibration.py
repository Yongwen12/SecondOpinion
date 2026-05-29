from __future__ import annotations

import datetime as dt
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from .model_config import DEFAULT_CHEAP_MODEL
from .text import clean_text


CONCERN_CALIBRATION_LABEL_VERSION = "concern-calibration-label-v0.2"
DEFAULT_CONCERN_CALIBRATION_MODEL = DEFAULT_CHEAP_MODEL

SURVIVAL_LABELS = ("survived", "partial", "not_found", "unsure")
CONCERN_QUALITY_LABELS = ("high", "medium", "low", "unsure")
AC_TREATMENT_LABELS = (
    "endorsed_or_relied_on",
    "mentioned_neutrally",
    "mentioned_as_resolved_or_outweighed",
    "not_mentioned",
    "unclear",
)
CONFIDENCE_LABELS = ("high", "medium", "low")
TRAINING_USE_LABELS = ("include", "exclude")


def label_concern_calibration_item(
    item: dict[str, Any],
    *,
    llm_client: Any,
    model: str = DEFAULT_CONCERN_CALIBRATION_MODEL,
    annotator_id: str | None = None,
) -> dict[str, Any]:
    annotator_id = annotator_id or f"llm:{model}"
    payload = llm_client.complete_json(
        model=model,
        messages=concern_calibration_messages(item),
        schema_name="concern_survival_calibration_label",
        schema=concern_calibration_schema(),
    )
    label = {
        "label_id": stable_label_id(item.get("task_id", ""), annotator_id),
        "task_id": item.get("task_id", ""),
        "paper_id": item.get("paper_id", ""),
        "review_id": item.get("review_id", ""),
        "label_schema_version": CONCERN_CALIBRATION_LABEL_VERSION,
        "annotator_type": "llm",
        "annotator_id": annotator_id,
        "model": model,
        "auto_survival_label": item.get("auto_survival_label", ""),
        "auto_survival_score": item.get("auto_survival_score", 0.0),
        "labels": payload.get("labels", {}),
        "notes": str(payload.get("notes", "")),
        "created_at": utc_now(),
    }
    errors = validate_concern_calibration_label(label)
    if errors:
        raise ValueError(f"Invalid concern calibration label for {label['task_id']}: {errors}")
    return label


def concern_calibration_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    compact = compact_calibration_item(item)
    return [
        {
            "role": "system",
            "content": (
                "You are calibrating a reviewer-claim survival dataset. "
                "Judge whether the reviewer concern is semantically present in the meta-review, "
                "whether the AC endorses/relies on it, and whether the concern itself is high-quality. "
                "Do not treat lexical overlap as sufficient. Prefer exclude when the evidence is ambiguous."
            ),
        },
        {
            "role": "user",
            "content": (
                "Label this calibration item. Definitions:\n"
                "- survived: the meta-review substantively repeats, endorses, or relies on the same concern.\n"
                "- partial: the meta-review covers the same broad issue but loses important specificity.\n"
                "- not_found: the meta-review does not meaningfully mention the concern.\n"
                "- meta_review_match asks whether the review claim and meta-review discuss the same concern.\n"
                "- ac_treatment asks how the AC/meta-review treats the concern if it is mentioned.\n"
                "- label_evidence_strength asks whether the evidence for your label is clear. "
                "For not_found, high strength is allowed when the full meta-review clearly discusses other issues "
                "but omits this specific claim; do not mark low merely because there is no matching sentence.\n"
                "- concern_quality high: specific, evidence-seeking, decision-relevant, and actionable.\n"
                "- concern_quality medium: reasonable but incomplete, broad, or only partly actionable.\n"
                "- concern_quality low: vague, weakly supported, subjective, or likely irrelevant.\n\n"
                "Important calibration rule: confidence/training_use are about label reliability, not whether the "
                "reviewer concern is good. A low-quality concern can still be confidence=high and training_use=include "
                "when the text clearly shows it is vague, weak, or irrelevant. A not_found item can also be "
                "confidence=high and training_use=include when the meta-review clearly omits the specific concern.\n\n"
                "Set training_use=include when this item is reliable enough to use as a future "
                "evaluation/training example, including reliable negative examples where the claim is clearly not in "
                "the meta-review. This does not mean the reviewer claim is about model training. "
                "Set training_use=exclude only when the labels are ambiguous or context is insufficient.\n\n"
                f"Calibration item JSON:\n{json.dumps(compact, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def compact_calibration_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": item.get("task_id", ""),
        "title": truncate(item.get("title", ""), 240),
        "decision_label": item.get("decision_label", ""),
        "review_rating_raw": item.get("review_rating_raw", ""),
        "review_confidence_raw": item.get("review_confidence_raw", ""),
        "claim_text": item.get("claim_text", ""),
        "claim_type": item.get("claim_type", ""),
        "importance": item.get("importance", ""),
        "source_field": item.get("source_field", ""),
        "source_sentence": item.get("source_sentence", ""),
        "auto_survival_label": item.get("auto_survival_label", ""),
        "auto_survival_score": item.get("auto_survival_score", 0.0),
        "matched_meta_segment": item.get("matched_meta_segment", ""),
        "matched_terms": item.get("matched_terms", []),
        "meta_review_text": truncate(item.get("meta_review_text", ""), 6000),
    }


def concern_calibration_schema() -> dict[str, Any]:
    labels_properties = {
        "meta_review_match": {"type": "string", "enum": list(SURVIVAL_LABELS)},
        "ac_treatment": {"type": "string", "enum": list(AC_TREATMENT_LABELS)},
        "concern_quality": {"type": "string", "enum": list(CONCERN_QUALITY_LABELS)},
        "label_evidence_strength": {"type": "string", "enum": list(CONFIDENCE_LABELS)},
        "confidence": {"type": "string", "enum": list(CONFIDENCE_LABELS)},
        "training_use": {"type": "string", "enum": list(TRAINING_USE_LABELS)},
        "rationale": {"type": "string"},
    }
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


def validate_concern_calibration_label(label: dict[str, Any]) -> list[str]:
    errors = []
    for key in (
        "label_id",
        "task_id",
        "label_schema_version",
        "annotator_type",
        "annotator_id",
        "labels",
        "notes",
        "created_at",
    ):
        if key not in label:
            errors.append(f"missing:{key}")
    if errors:
        return errors
    if label["label_schema_version"] != CONCERN_CALIBRATION_LABEL_VERSION:
        errors.append("invalid:label_schema_version")
    if label["annotator_type"] != "llm":
        errors.append("invalid:annotator_type")
    labels = label.get("labels")
    if not isinstance(labels, dict):
        errors.append("invalid:labels")
        return errors
    normalized = normalized_label_payload(labels)
    errors.extend(require_enum(normalized, "meta_review_match", SURVIVAL_LABELS))
    errors.extend(require_enum(normalized, "ac_treatment", AC_TREATMENT_LABELS))
    errors.extend(require_enum(labels, "concern_quality", CONCERN_QUALITY_LABELS))
    errors.extend(require_enum(normalized, "label_evidence_strength", CONFIDENCE_LABELS))
    errors.extend(require_enum(labels, "confidence", CONFIDENCE_LABELS))
    errors.extend(require_enum(labels, "training_use", TRAINING_USE_LABELS))
    if not isinstance(labels.get("rationale"), str):
        errors.append("invalid:labels.rationale")
    return errors


def merge_calibration_labels(
    items: list[dict[str, Any]],
    labels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    labels_by_task = {label["task_id"]: label for label in labels}
    merged = []
    for item in items:
        label = labels_by_task.get(item.get("task_id", ""))
        if not label:
            continue
        label_payload = normalized_label_payload(label["labels"])
        meta_review_match = label_payload.get("meta_review_match", "unsure")
        auto_label = item.get("auto_survival_label", "")
        record = dict(item)
        record.update(
            {
                "llm_label_id": label["label_id"],
                "llm_meta_review_match": meta_review_match,
                "llm_ac_treatment": label_payload.get("ac_treatment", "unclear"),
                "llm_concern_quality": label_payload.get("concern_quality", "unsure"),
                "llm_label_evidence_strength": label_payload.get("label_evidence_strength", "low"),
                "llm_confidence": label_payload.get("confidence", "low"),
                "llm_training_use": label_payload.get("training_use", "exclude"),
                "llm_rationale": label_payload.get("rationale", ""),
                "llm_notes": label.get("notes", ""),
                "auto_agrees_with_llm": auto_label == meta_review_match,
            }
        )
        record["high_confidence_training_candidate"] = is_high_confidence_training_candidate(record)
        merged.append(record)
    return merged


def is_high_confidence_training_candidate(record: dict[str, Any]) -> bool:
    training_use = record.get("llm_training_use")
    if training_use and training_use != "include":
        return False
    if record.get("llm_confidence") != "high":
        return False
    evidence_strength = record.get("llm_label_evidence_strength", record.get("llm_evidence_clarity", ""))
    meta_review_match = record.get("llm_meta_review_match", record.get("llm_survival_label", ""))
    if evidence_strength == "low":
        return False
    if meta_review_match == "unsure":
        return False
    if record.get("llm_concern_quality") == "unsure":
        return False
    return True


def build_gold_expansion_calibration_sample(
    survival_report: dict[str, Any],
    *,
    existing_records: list[dict[str, Any]] | None = None,
    sample_size: int = 500,
    seed: int = 29,
) -> dict[str, Any]:
    from .concern_survival import iter_concern_survival_records

    existing_task_ids = {
        normalized_calibration_record(record).get("task_id", "")
        for record in (existing_records or [])
        if normalized_calibration_record(record).get("task_id", "")
    }
    records = [
        item
        for item in iter_concern_survival_records(survival_report)
        if item.get("task_id", "") not in existing_task_ids
    ]
    sampled = targeted_gold_expansion_sample(records, sample_size=sample_size, seed=seed)
    return {
        "schema_version": "0.1",
        "sample_type": "concern_gold_expansion_calibration",
        "sample_size_requested": max(0, sample_size),
        "sample_size": len(sampled),
        "seed": seed,
        "excluded_existing_count": len(existing_task_ids),
        "source_snapshot": survival_report.get("snapshot", {}),
        "summary": {
            "candidate_count": len(records),
            "sample_auto_label_counts": dict(Counter(item.get("auto_survival_label", "") for item in sampled)),
            "sample_importance_counts": dict(Counter(item.get("importance", "") for item in sampled)),
            "sample_claim_type_counts": dict(Counter(item.get("claim_type", "") for item in sampled)),
            "sample_reason_counts": dict(Counter(item.get("sampling_reason", "") for item in sampled)),
        },
        "items": sampled,
    }


def targeted_gold_expansion_sample(records: list[dict[str, Any]], *, sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size <= 0 or not records:
        return []
    rng = random.Random(seed)
    buckets = [
        ("auto_not_found_very_low_score", 0.30, lambda item: auto_label(item) == "not_found" and auto_score(item) <= 0.08),
        ("auto_not_found_low_score", 0.20, lambda item: auto_label(item) == "not_found" and auto_score(item) <= 0.18),
        ("possible_low_quality", 0.25, looks_like_low_quality_candidate),
        ("auto_survived_or_partial", 0.25, lambda item: auto_label(item) in {"survived", "partial"}),
    ]
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    leftovers = list(records)
    for index, (reason, ratio, predicate) in enumerate(buckets):
        target = int(sample_size * ratio)
        if index == len(buckets) - 1:
            target = sample_size - len(selected)
        candidates = [item for item in records if item.get("task_id", "") not in selected_ids and predicate(item)]
        rng.shuffle(candidates)
        for item in candidates[: max(0, target)]:
            selected.append(with_sampling_reason(item, reason))
            selected_ids.add(item.get("task_id", ""))
    rng.shuffle(leftovers)
    for item in leftovers:
        if len(selected) >= sample_size:
            break
        task_id = item.get("task_id", "")
        if task_id in selected_ids:
            continue
        selected.append(with_sampling_reason(item, "fill_remaining"))
        selected_ids.add(task_id)
    rng.shuffle(selected)
    return selected[:sample_size]


def looks_like_low_quality_candidate(item: dict[str, Any]) -> bool:
    claim_text = clean_text(item.get("claim_text", "")).lower()
    claim_type = clean_text(item.get("claim_type", "")).lower()
    importance = clean_text(item.get("importance", "")).lower()
    source_field = clean_text(item.get("source_field", "")).lower()
    weak_type = claim_type in {"writing", "general", "clarity", "novelty", "ethics"}
    weak_importance = importance in {"minor", "question", "medium"}
    short_or_question = len(claim_text.split()) <= 35 or source_field == "questions"
    vague_markers = (
        "minor" in claim_text
        or "typo" in claim_text
        or "unclear" in claim_text
        or "not clear" in claim_text
        or "hard to follow" in claim_text
        or "would be nice" in claim_text
        or "i wonder" in claim_text
    )
    return (weak_type and weak_importance) or (weak_type and short_or_question) or (weak_importance and vague_markers)


def with_sampling_reason(item: dict[str, Any], reason: str) -> dict[str, Any]:
    copied = dict(item)
    copied["sampling_reason"] = reason
    return copied


def auto_label(item: dict[str, Any]) -> str:
    return str(item.get("auto_survival_label", ""))


def auto_score(item: dict[str, Any]) -> float:
    try:
        return float(item.get("auto_survival_score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def build_concern_calibration_report(
    *,
    items: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    merged: list[dict[str, Any]],
) -> dict[str, Any]:
    merged = [normalized_calibration_record(item) for item in merged]
    high_confidence = [item for item in merged if item.get("high_confidence_training_candidate")]
    agreement_count = sum(1 for item in merged if item.get("auto_agrees_with_llm"))
    return {
        "schema_version": "concern-calibration-report-v0.1",
        "label_schema_version": CONCERN_CALIBRATION_LABEL_VERSION,
        "created_at": utc_now(),
        "input_item_count": len(items),
        "label_count": len(labels),
        "merged_count": len(merged),
        "high_confidence_count": len(high_confidence),
        "auto_llm_agreement_count": agreement_count,
        "auto_llm_agreement_rate": safe_rate(agreement_count, len(merged)),
        "auto_label_counts": dict(Counter(item.get("auto_survival_label", "") for item in merged)),
        "llm_meta_review_match_counts": dict(Counter(item.get("llm_meta_review_match", "") for item in merged)),
        "llm_concern_quality_counts": dict(Counter(item.get("llm_concern_quality", "") for item in merged)),
        "llm_ac_treatment_counts": dict(Counter(item.get("llm_ac_treatment", "") for item in merged)),
        "high_confidence_match_counts": dict(Counter(item.get("llm_meta_review_match", "") for item in high_confidence)),
        "examples": {
            "agreement": [example_record(item) for item in merged if item.get("auto_agrees_with_llm")][:10],
            "disagreement": [example_record(item) for item in merged if not item.get("auto_agrees_with_llm")][:10],
            "high_confidence": [example_record(item) for item in high_confidence][:10],
        },
    }


def write_concern_calibration_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_concern_calibration_markdown(report), encoding="utf-8")


def render_concern_calibration_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Concern Survival LLM Calibration",
        "",
        f"- Input items: {report.get('input_item_count', 0)}",
        f"- Labels: {report.get('label_count', 0)}",
        f"- High-confidence training candidates: {report.get('high_confidence_count', 0)}",
        f"- Auto/LLM agreement: {format_rate(report.get('auto_llm_agreement_rate', 0.0))}",
        "",
        "## Label Counts",
        "",
        "| Label set | Counts |",
        "| --- | --- |",
    ]
    for key in (
        "auto_label_counts",
        "llm_meta_review_match_counts",
        "llm_concern_quality_counts",
        "llm_ac_treatment_counts",
        "high_confidence_match_counts",
    ):
        lines.append(f"| `{key}` | `{json.dumps(report.get(key, {}), ensure_ascii=False, sort_keys=True)}` |")

    for section, examples in report.get("examples", {}).items():
        lines.extend(["", f"## {section.replace('_', ' ').title()}", ""])
        if not examples:
            lines.append("No examples.")
            continue
        for example in examples:
            lines.append(
                f"- `{example['task_id']}` auto=`{example['auto_survival_label']}` "
                f"llm=`{example['llm_meta_review_match']}` quality=`{example['llm_concern_quality']}`"
            )
            lines.append(f"  - Claim: {example['claim_text']}")
            lines.append(f"  - Meta: {example['matched_meta_segment'] or 'No match'}")
            lines.append(f"  - Rationale: {example['llm_rationale']}")
    return "\n".join(lines)


def example_record(item: dict[str, Any]) -> dict[str, Any]:
    item = normalized_calibration_record(item)
    return {
        "task_id": item.get("task_id", ""),
        "auto_survival_label": item.get("auto_survival_label", ""),
        "llm_meta_review_match": item.get("llm_meta_review_match", ""),
        "llm_concern_quality": item.get("llm_concern_quality", ""),
        "claim_text": truncate(item.get("claim_text", ""), 320),
        "matched_meta_segment": truncate(item.get("matched_meta_segment", ""), 320),
        "llm_rationale": truncate(item.get("llm_rationale", ""), 320),
    }


def normalized_label_payload(labels: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(labels)
    if "meta_review_match" not in normalized:
        normalized["meta_review_match"] = normalized.get("semantic_survival_label", "unsure")
    if "ac_treatment" not in normalized:
        normalized["ac_treatment"] = normalized.get("ac_stance", "unclear")
    if "label_evidence_strength" not in normalized:
        normalized["label_evidence_strength"] = normalized.get("evidence_clarity", "low")
    return normalized


def normalized_calibration_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    if "llm_meta_review_match" not in normalized:
        normalized["llm_meta_review_match"] = normalized.get("llm_survival_label", "")
    if "llm_ac_treatment" not in normalized:
        normalized["llm_ac_treatment"] = normalized.get("llm_ac_stance", "")
    if "llm_label_evidence_strength" not in normalized:
        normalized["llm_label_evidence_strength"] = normalized.get("llm_evidence_clarity", "")
    if "high_confidence_training_candidate" not in normalized:
        normalized["high_confidence_training_candidate"] = is_high_confidence_training_candidate(normalized)
    return normalized


def build_negative_calibration_sample(
    survival_report: dict[str, Any],
    *,
    sample_size: int = 100,
    seed: int = 11,
    max_auto_score: float = 0.16,
) -> dict[str, Any]:
    from .concern_survival import iter_concern_survival_records

    candidates = [
        item
        for item in iter_concern_survival_records(survival_report)
        if item.get("auto_survival_label") == "not_found"
        and float(item.get("auto_survival_score") or 0.0) <= max_auto_score
    ]
    candidates.sort(key=lambda item: (float(item.get("auto_survival_score") or 0.0), item.get("task_id", "")))
    rng = random.Random(seed)
    if len(candidates) > sample_size:
        low_bucket = candidates[: max(sample_size * 2, sample_size)]
        rng.shuffle(low_bucket)
        candidates = low_bucket[:sample_size]
    for item in candidates:
        item["sampling_reason"] = "auto_not_found_low_score"
        item["human_survival_label"] = ""
        item["human_concern_quality"] = ""
        item["human_notes"] = ""
    return {
        "schema_version": "0.1",
        "sample_type": "concern_survival_negative_calibration",
        "sample_size_requested": sample_size,
        "sample_size": len(candidates),
        "seed": seed,
        "max_auto_score": max_auto_score,
        "source_snapshot": survival_report.get("snapshot", {}),
        "summary": {
            "candidate_count": len(candidates),
            "auto_label_counts": dict(Counter(item.get("auto_survival_label", "") for item in candidates)),
            "decision_counts": dict(Counter(item.get("decision_label", "") for item in candidates)),
        },
        "items": candidates,
    }


def build_rag_memory_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [rag_memory_record(record) for record in dedupe_records(records)]


def rag_memory_record(record: dict[str, Any]) -> dict[str, Any]:
    record = normalized_calibration_record(record)
    return {
        "memory_id": f"concern_case:{record.get('task_id', '')}",
        "source_task_id": record.get("task_id", ""),
        "paper_id": record.get("paper_id", ""),
        "review_id": record.get("review_id", ""),
        "title": record.get("title", ""),
        "decision_label": record.get("decision_label", ""),
        "claim": {
            "text": record.get("claim_text", ""),
            "type": record.get("claim_type", ""),
            "importance": record.get("importance", ""),
            "source_field": record.get("source_field", ""),
            "source_sentence": record.get("source_sentence", ""),
        },
        "meta_review": {
            "match": record.get("llm_meta_review_match", ""),
            "ac_treatment": record.get("llm_ac_treatment", ""),
            "matched_segment": record.get("matched_meta_segment", ""),
        },
        "quality": {
            "concern_quality": record.get("llm_concern_quality", ""),
            "label_evidence_strength": record.get("llm_label_evidence_strength", ""),
            "confidence": record.get("llm_confidence", ""),
        },
        "rationale": record.get("llm_rationale", ""),
        "tags": rag_tags(record),
    }


def build_sft_examples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [sft_example(record) for record in dedupe_records(records)]


def sft_example(record: dict[str, Any]) -> dict[str, Any]:
    record = normalized_calibration_record(record)
    target = expected_assistant_payload(record)
    return {
        "messages": [
            {
                "role": "system",
                "content": "You audit reviewer claims using paper-review lifecycle evidence. Return concise JSON.",
            },
            {
                "role": "user",
                "content": json.dumps(training_input_payload(record), ensure_ascii=False, indent=2),
            },
            {
                "role": "assistant",
                "content": json.dumps(target, ensure_ascii=False, sort_keys=True),
            },
        ],
        "metadata": training_metadata(record),
    }


def build_preference_pairs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [preference_pair(record) for record in dedupe_records(records)]


def preference_pair(record: dict[str, Any]) -> dict[str, Any]:
    record = normalized_calibration_record(record)
    chosen = expected_assistant_payload(record)
    rejected = dict(chosen)
    rejected["meta_review_match"] = opposite_match(record.get("llm_meta_review_match", "unsure"))
    rejected["concern_quality"] = "low" if record.get("llm_concern_quality") != "low" else "high"
    rejected["rationale"] = "This answer over-relies on superficial wording and does not track the provided evidence."
    return {
        "prompt": json.dumps(training_input_payload(record), ensure_ascii=False, indent=2),
        "chosen": json.dumps(chosen, ensure_ascii=False, sort_keys=True),
        "rejected": json.dumps(rejected, ensure_ascii=False, sort_keys=True),
        "metadata": training_metadata(record),
    }


def expected_assistant_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "meta_review_match": record.get("llm_meta_review_match", ""),
        "ac_treatment": record.get("llm_ac_treatment", ""),
        "concern_quality": record.get("llm_concern_quality", ""),
        "label_evidence_strength": record.get("llm_label_evidence_strength", ""),
        "confidence": record.get("llm_confidence", ""),
        "rationale": record.get("llm_rationale", ""),
    }


def training_input_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": record.get("title", ""),
        "decision_label": record.get("decision_label", ""),
        "reviewer_claim": record.get("claim_text", ""),
        "claim_type": record.get("claim_type", ""),
        "importance": record.get("importance", ""),
        "source_sentence": record.get("source_sentence", ""),
        "matched_meta_review_segment": record.get("matched_meta_segment", ""),
        "meta_review_text": truncate(record.get("meta_review_text", ""), 5000),
    }


def training_metadata(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": record.get("task_id", ""),
        "paper_id": record.get("paper_id", ""),
        "review_id": record.get("review_id", ""),
        "decision_label": record.get("decision_label", ""),
        "auto_survival_label": record.get("auto_survival_label", ""),
        "auto_survival_score": record.get("auto_survival_score", 0.0),
        "high_confidence_training_candidate": bool(record.get("high_confidence_training_candidate")),
    }


def rag_tags(record: dict[str, Any]) -> list[str]:
    tags = [
        f"match:{record.get('llm_meta_review_match', '')}",
        f"quality:{record.get('llm_concern_quality', '')}",
        f"type:{record.get('claim_type', '')}",
        f"decision:{record.get('decision_label', '')}",
    ]
    return [tag for tag in tags if not tag.endswith(":")]


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for record in records:
        task_id = record.get("task_id", "")
        if task_id in seen:
            continue
        seen.add(task_id)
        deduped.append(normalized_calibration_record(record))
    return deduped


def opposite_match(match: str) -> str:
    if match == "not_found":
        return "survived"
    if match == "survived":
        return "not_found"
    if match == "partial":
        return "not_found"
    return "survived"


def require_enum(labels: dict[str, Any], key: str, values: tuple[str, ...]) -> list[str]:
    if key not in labels:
        return [f"missing:labels.{key}"]
    if labels[key] not in values:
        return [f"invalid:labels.{key}"]
    return []


def stable_label_id(task_id: str, annotator_id: str) -> str:
    import hashlib

    digest = hashlib.sha1(f"{task_id}|{annotator_id}|{CONCERN_CALIBRATION_LABEL_VERSION}".encode("utf-8")).hexdigest()
    return f"concern_cal_{digest[:16]}"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def safe_rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def format_rate(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def truncate(text: Any, limit: int) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
