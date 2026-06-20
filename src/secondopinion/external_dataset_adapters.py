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
        "text_fields": ["comment", "comment_text", "review_comment", "review_text", "sentence", "text", "Text"],
        "context_fields": ["aspect", "paper_title", "section", "review_id", "ReviewId", "SentenceId", "Label2", "set"],
        "label_fields": ["gold_label", "label", "actionability", "actionability_label", "specificity_label", "Label1"],
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
    "reviewcritique": {
        "dataset": "ReviewCritique",
        "default_dimension": "substantiation",
        "text_fields": ["segment_text", "review_segment", "comment", "review_comment", "claim", "claim_text", "text"],
        "context_fields": ["explanation", "rationale", "error_type", "deficiency_type", "paper_title", "section"],
        "label_fields": ["gold_label", "label", "deficiency_label", "deficiency", "is_deficient", "quality_label"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "betterpr": {
        "dataset": "BetterPR",
        "default_dimension": "actionability",
        "text_fields": ["comment", "comment_text", "review_comment", "review_text", "sentence", "text", "Text"],
        "context_fields": ["aspect", "paper_title", "section", "review_id"],
        "label_fields": ["gold_label", "label", "constructiveness", "constructive_label", "is_constructive", "Target"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "politepeer": {
        "dataset": "PolitePEER",
        "default_dimension": "professionalism",
        "text_fields": ["comment", "comment_text", "review_comment", "review_text", "sentence", "text", "review"],
        "context_fields": ["politeness_strategy", "tone_cue", "paper_title", "section", "Venue", "Review ID", "Review URL"],
        "label_fields": ["gold_label", "label", "politeness", "politeness_label", "politeness_level", "tone_label", "Tone"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "revci": {
        "dataset": "RevCI",
        "default_dimension": "consensus_conflict",
        "text_fields": ["premise", "hypothesis", "comment_a", "comment_b", "review_comment", "text"],
        "context_fields": ["aspect", "evidence", "evidence_text", "paper_title", "intensity"],
        "label_fields": ["gold_label", "label", "contradiction_label", "relation", "conflict_label", "intensity_label"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "ampere": {
        "dataset": "AMPERE",
        "default_dimension": "argument_role",
        "text_fields": ["proposition", "proposition_text", "segment_text", "comment", "review_text", "sentence", "text"],
        "context_fields": ["aspect", "paper_title", "section", "review_id"],
        "label_fields": ["gold_label", "label", "argument_type", "proposition_type", "role"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "asap_review": {
        "dataset": "ASAP-Review",
        "default_dimension": "review_aspect",
        "text_fields": ["sentence", "comment", "review_comment", "review_text", "text"],
        "context_fields": ["sentiment", "paper_title", "section", "review_id"],
        "label_fields": ["gold_label", "label", "aspect", "aspect_label", "category"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "ape": {
        "dataset": "APE",
        "default_dimension": "rebuttal_alignment",
        "text_fields": ["review_argument", "review_comment", "comment", "claim", "claim_text", "text"],
        "context_fields": ["rebuttal_argument", "rebuttal", "response", "response_text", "paper_title"],
        "label_fields": ["gold_label", "label", "alignment_label", "pair_label", "is_pair", "matched"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "aries": {
        "dataset": "ARIES",
        "default_dimension": "revision_alignment",
        "text_fields": ["review_comment", "comment", "feedback", "claim", "claim_text", "text"],
        "context_fields": ["paper_edit", "edit_text", "revision", "revised_text", "paper_title"],
        "label_fields": ["gold_label", "label", "edit_label", "revision_label", "is_linked", "linked"],
        "predicted_fields": ["predicted_label", "prediction", "baseline_label"],
    },
    "re2": {
        "dataset": "Re2",
        "default_dimension": "rebuttal_robustness",
        "text_fields": ["review_comment", "comment", "review_text", "claim", "claim_text", "text"],
        "context_fields": ["rebuttal", "rebuttal_text", "discussion", "response", "response_text", "paper_title"],
        "label_fields": ["gold_label", "label", "response_status", "rebuttal_label", "resolution_label"],
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
        "partially_supported": "partially_substantiated",
        "partial": "partially_substantiated",
        "mixed": "partially_substantiated",
        "unsubstantiated": "unsubstantiated",
        "unsupported": "unsubstantiated",
        "not_substantiated": "unsubstantiated",
        "false": "unsubstantiated",
        "no": "unsubstantiated",
        "0": "unsubstantiated",
        "deficient": "deficient",
        "has_deficiency": "deficient",
        "not substantiated": "unsubstantiated",
        "not_deficient": "not_deficient",
        "no_deficiency": "not_deficient",
        "non_deficient": "not_deficient",
    },
    "actionability": {
        "actionable": "actionable",
        "constructive": "constructive",
        "c": "constructive",
        "yes": "actionable",
        "true": "actionable",
        "1": "actionable",
        "partially_actionable": "partially_actionable",
        "partial": "partially_actionable",
        "mixed": "partially_actionable",
        "not_actionable": "not_actionable",
        "non_actionable": "not_actionable",
        "non_constructive": "non_constructive",
        "n": "non_constructive",
        "not constructive": "non_constructive",
        "not_constructive": "non_constructive",
        "unconstructive": "non_constructive",
        "no": "not_actionable",
        "false": "not_actionable",
        "0": "not_actionable",
    },
    "consensus_conflict": {
        **CONTRASCIVIEW_LABELS,
        "same_concern": "same_concern",
        "same": "same_concern",
        "agreement": "same_concern",
        "agree": "same_concern",
        "support": "same_concern",
        "related": "related_but_different",
        "related_but_different": "related_but_different",
        "not_same": "not_same_concern",
        "not_same_concern": "not_same_concern",
        "conflict": "contradiction",
        "contradictory": "contradiction",
        "strong_contradiction": "contradiction",
        "weak_contradiction": "contradiction",
        "no_contradiction": "not_contradiction",
        "non_contradiction": "not_contradiction",
    },
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
        "specific": "specifically_addressed",
        "addressed": "specifically_addressed",
        "accepted": "specifically_addressed",
        "revision": "resolved_or_weakened",
        "revised": "resolved_or_weakened",
        "resolved": "resolved_or_weakened",
        "resolved_or_weakened": "resolved_or_weakened",
        "likely_resolved": "likely_resolved",
        "unresolved": "not_addressed",
        "defended": "generic_or_unclear",
        "rejected": "not_addressed",
    },
    "professionalism": {
        "professional": "professional",
        "polite": "polite",
        "high": "polite",
        "5": "polite",
        "4": "polite",
        "constructive": "professional",
        "neutral": "neutral",
        "medium": "neutral",
        "3": "neutral",
        "unprofessional": "unprofessional",
        "impolite": "impolite",
        "low": "impolite",
        "2": "impolite",
        "1": "impolite",
        "rude": "impolite",
        "toxic": "unprofessional",
    },
    "argument_role": {
        "request": "request",
        "arg_request": "request",
        "suggestion": "request",
        "evaluation": "evaluation",
        "evaluative": "evaluation",
        "arg_evaluative": "evaluation",
        "fact": "fact",
        "arg_fact": "fact",
        "reference": "reference",
        "arg_reference": "reference",
        "quote": "quote",
        "arg_quote": "quote",
        "summary": "summary",
        "arg_structuring": "summary",
        "non_argument": "non_argument",
        "nonarg": "non_argument",
        "other": "other",
    },
    "review_aspect": {
        "clarity": "clarity",
        "asp_clarity": "clarity",
        "soundness": "soundness",
        "asp_soundness": "soundness",
        "substance": "substance",
        "asp_substance": "substance",
        "originality": "originality",
        "asp_originality": "originality",
        "novelty": "originality",
        "meaningful_comparison": "meaningful_comparison",
        "comparison": "meaningful_comparison",
        "motivation": "motivation",
        "asp_motivation": "motivation",
        "reproducibility": "reproducibility",
        "asp_reproducibility": "reproducibility",
        "presentation": "presentation",
        "asp_presentation": "presentation",
        "overall": "overall",
        "none": "overall",
    },
    "rebuttal_alignment": {
        "matched": "matched",
        "match": "matched",
        "aligned": "matched",
        "linked": "matched",
        "pair": "matched",
        "true": "matched",
        "yes": "matched",
        "1": "matched",
        "partial_match": "partial_match",
        "partial": "partial_match",
        "unmatched": "unmatched",
        "not_matched": "unmatched",
        "not_aligned": "unmatched",
        "false": "unmatched",
        "no": "unmatched",
        "0": "unmatched",
    },
    "revision_alignment": {
        "linked_edit": "linked_edit",
        "linked": "linked_edit",
        "edit": "linked_edit",
        "edited": "linked_edit",
        "revision": "linked_edit",
        "true": "linked_edit",
        "yes": "linked_edit",
        "1": "linked_edit",
        "indirect_edit": "indirect_edit",
        "partial_edit": "indirect_edit",
        "no_edit": "no_edit",
        "unlinked": "no_edit",
        "false": "no_edit",
        "no": "no_edit",
        "0": "no_edit",
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
    "professionalism": {"professional": 0.9, "polite": 0.85, "neutral": 0.55, "unprofessional": 0.15, "impolite": 0.15},
    "argument_role": {
        "request": 0.85,
        "evaluation": 0.7,
        "fact": 0.65,
        "reference": 0.75,
        "quote": 0.75,
        "summary": 0.45,
        "other": 0.4,
        "non_argument": 0.15,
    },
    "review_aspect": {
        "clarity": 0.6,
        "soundness": 0.75,
        "substance": 0.75,
        "originality": 0.7,
        "meaningful_comparison": 0.8,
        "motivation": 0.6,
        "reproducibility": 0.65,
        "presentation": 0.55,
        "overall": 0.5,
    },
    "rebuttal_alignment": {"matched": 0.85, "partial_match": 0.55, "unmatched": 0.15},
    "revision_alignment": {"linked_edit": 0.9, "indirect_edit": 0.65, "no_edit": 0.15},
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
    materialized = list(records)
    if any(is_substanreview_span_record(record) for record in materialized):
        return normalize_substanreview_span_records(materialized, limit=limit)
    records = materialized
    return normalize_dataset_records(records, dataset_key="substanreview", dimension="substantiation", limit=limit)


def normalize_disapere_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    materialized = list(records)
    if any(is_disapere_annotation_record(record) for record in materialized):
        return normalize_disapere_annotation_records(materialized, limit=limit)
    records = materialized
    return normalize_dataset_records(records, dataset_key="disapere", dimension="rebuttal_robustness", limit=limit)


def normalize_rbtact_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="rbtact", dimension="rebuttal_robustness", limit=limit)


def normalize_reviewcritique_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="reviewcritique", dimension="substantiation", limit=limit)


def normalize_betterpr_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="betterpr", dimension="actionability", limit=limit)


def normalize_politepeer_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="politepeer", dimension="professionalism", limit=limit)


def normalize_revci_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="revci", dimension="consensus_conflict", limit=limit)


def normalize_ampere_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="ampere", dimension="argument_role", limit=limit)


def normalize_asap_review_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="asap_review", dimension="review_aspect", limit=limit)


def normalize_ape_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="ape", dimension="rebuttal_alignment", limit=limit)


def normalize_aries_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="aries", dimension="revision_alignment", limit=limit)


def normalize_re2_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return normalize_dataset_records(records, dataset_key="re2", dimension="rebuttal_robustness", limit=limit)


def is_substanreview_span_record(record: dict[str, Any]) -> bool:
    return bool(record.get("review") and isinstance(record.get("label"), list))


def normalize_substanreview_span_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    normalized = []
    for record_index, record in enumerate(records):
        review = clean_value(record.get("review", ""))
        labels = record.get("label", [])
        if not review or not isinstance(labels, list):
            continue
        evidence_by_key: dict[str, list[str]] = {}
        claims: list[tuple[str, str, str]] = []
        for span in labels:
            if not isinstance(span, list | tuple) or len(span) < 3:
                continue
            start, end, tag = span[0], span[1], clean_value(span[2])
            if not isinstance(start, int) or not isinstance(end, int) or not tag:
                continue
            text = review[max(0, start) : max(0, end)].strip()
            if not text:
                continue
            key = substantiation_pair_key(tag)
            if tag.startswith("Jus_"):
                evidence_by_key.setdefault(key, []).append(text)
            elif tag.startswith("Eval_"):
                claims.append((key, tag, text))
        for claim_index, (key, tag, claim_text) in enumerate(claims):
            if limit is not None and len(normalized) >= limit:
                break
            evidence_text = join_text(evidence_by_key.get(key, []))
            gold_label = "substantiated" if evidence_text else "unsubstantiated"
            normalized.append(
                normalized_record(
                    task_id=f"substanreview:{clean_value(record.get('id')) or record_index}:{tag}:{claim_index}",
                    dataset="SubstanReview",
                    dimension="substantiation",
                    input_text=claim_text,
                    context_text=evidence_text,
                    gold_label=gold_label,
                    predicted_label=gold_label,
                    metadata={
                        "source_review_id": record.get("id", record_index),
                        "span_label": tag,
                        "pair_key": key,
                    },
                )
            )
        if limit is not None and len(normalized) >= limit:
            break
    return normalized


def substantiation_pair_key(tag: str) -> str:
    parts = tag.split("_")
    if len(parts) >= 3:
        return "_".join(parts[1:])
    return tag


def is_disapere_annotation_record(record: dict[str, Any]) -> bool:
    return isinstance(record.get("review_sentences"), list) and isinstance(record.get("rebuttal_sentences"), list)


def normalize_disapere_annotation_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    normalized = []
    for record_index, record in enumerate(records):
        metadata = record.get("metadata", {}) if isinstance(record.get("metadata"), dict) else {}
        aligned_rebuttals = disapere_rebuttals_by_review_sentence(record.get("rebuttal_sentences", []))
        for review_sentence in record.get("review_sentences", []):
            if limit is not None and len(normalized) >= limit:
                break
            if not isinstance(review_sentence, dict):
                continue
            review_text = clean_value(review_sentence.get("text", ""))
            if not review_text:
                continue
            sentence_index = review_sentence.get("sentence_index")
            rebuttals = aligned_rebuttals.get(sentence_index, [])
            context = join_text(rebuttal.get("text", "") for rebuttal in rebuttals)
            gold_label = disapere_rebuttal_robustness_label(rebuttals)
            normalized.append(
                normalized_record(
                    task_id=":".join(
                        [
                            "disapere",
                            clean_value(metadata.get("forum_id")) or str(record_index),
                            clean_value(metadata.get("review_id")) or "review",
                            str(sentence_index),
                        ]
                    ),
                    dataset="DISAPERE",
                    dimension="rebuttal_robustness",
                    input_text=review_text,
                    context_text=context,
                    gold_label=gold_label,
                    predicted_label=gold_label,
                    metadata={
                        "forum_id": metadata.get("forum_id", ""),
                        "review_id": metadata.get("review_id", ""),
                        "rebuttal_id": metadata.get("rebuttal_id", ""),
                        "title": metadata.get("title", ""),
                        "conference": metadata.get("conference", ""),
                        "review_action": review_sentence.get("review_action", ""),
                        "fine_review_action": review_sentence.get("fine_review_action", ""),
                        "aspect": review_sentence.get("aspect", ""),
                        "polarity": review_sentence.get("polarity", ""),
                        "aligned_rebuttal_count": len(rebuttals),
                        "rebuttal_actions": [clean_value(item.get("rebuttal_action", "")) for item in rebuttals],
                        "rebuttal_stances": [clean_value(item.get("rebuttal_stance", "")) for item in rebuttals],
                    },
                )
            )
        if limit is not None and len(normalized) >= limit:
            break
    return normalized


def disapere_rebuttals_by_review_sentence(rebuttal_sentences: Any) -> dict[Any, list[dict[str, Any]]]:
    aligned: dict[Any, list[dict[str, Any]]] = {}
    if not isinstance(rebuttal_sentences, list):
        return aligned
    for rebuttal in rebuttal_sentences:
        if not isinstance(rebuttal, dict):
            continue
        alignment = rebuttal.get("alignment", [])
        if not isinstance(alignment, list | tuple) or len(alignment) < 2:
            continue
        target = alignment[1]
        if isinstance(target, list):
            indices = target
        elif target is None:
            indices = []
        else:
            indices = [target]
        for index in indices:
            aligned.setdefault(index, []).append(rebuttal)
    return aligned


def disapere_rebuttal_robustness_label(rebuttals: list[dict[str, Any]]) -> str:
    if not rebuttals:
        return "not_addressed"
    actions = {clean_value(rebuttal.get("rebuttal_action", "")).lower() for rebuttal in rebuttals}
    stances = {clean_value(rebuttal.get("rebuttal_stance", "")).lower() for rebuttal in rebuttals}
    if actions & {"rebuttal_done", "rebuttal_resolution", "rebuttal_resolved"}:
        return "resolved_or_weakened"
    if stances & {"concur", "answer"}:
        return "specifically_addressed"
    if actions & {"rebuttal_future", "rebuttal_partial", "rebuttal_followup"}:
        return "partially_addresses"
    if stances & {"dispute", "mitigate", "clarification"}:
        return "generic_or_unclear"
    return "generic_or_unclear"


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
        gold_field, gold_value = first_field_value(row, spec["label_fields"])
        gold_label = normalize_source_label(gold_value, dimension=dimension, dataset_key=dataset_key, field_name=gold_field)
        if not gold_label:
            continue
        predicted_field, predicted_value = first_field_value(row, spec["predicted_fields"])
        predicted_label = normalize_source_label(
            predicted_value,
            dimension=dimension,
            dataset_key=dataset_key,
            field_name=predicted_field,
        )
        if not predicted_label:
            predicted_label = heuristic_prediction(row, dataset_key=dataset_key, dimension=dimension, gold_label=gold_label)
        input_text = join_fields(row, spec["text_fields"])
        if not input_text:
            continue
        normalized.append(
            normalized_record(
                task_id=clean_value(
                    row_value(row, "task_id")
                    or row_value(row, "id")
                    or row_value(row, "uid")
                    or row_value(row, "ReviewId")
                    or f"{dataset_key}:{index}"
                ),
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


def normalize_source_label(value: Any, *, dimension: str, dataset_key: str, field_name: str) -> str:
    text = clean_value(value).lower().replace("-", "_").replace(" ", "_")
    if dataset_key == "reviewcritique" and "deficien" in field_name:
        if text in {"true", "yes", "1", "deficient", "has_deficiency"}:
            return "deficient"
        if text in {"false", "no", "0", "not_deficient", "no_deficiency", "non_deficient"}:
            return "not_deficient"
    if dataset_key == "politepeer" and field_name.lower() == "tone":
        if text in {"1", "2"}:
            return "impolite"
        if text == "3":
            return "neutral"
        if text in {"4", "5"}:
            return "polite"
    return normalize_dimension_label(value, dimension)


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


def normalized_field_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def row_value(row: dict[str, Any], field: str) -> Any:
    if field in row:
        return row.get(field)
    lowered = field.lower()
    for key, value in row.items():
        if str(key).lower() == lowered:
            return value
    normalized = normalized_field_name(field)
    for key, value in row.items():
        if normalized_field_name(str(key)) == normalized:
            return value
    return ""


def first_value(row: dict[str, Any], fields: list[str]) -> Any:
    for field in fields:
        value = row_value(row, field)
        if clean_value(value):
            return value
    return ""


def first_field_value(row: dict[str, Any], fields: list[str]) -> tuple[str, Any]:
    for field in fields:
        value = row_value(row, field)
        if clean_value(value):
            return field, value
    return "", ""


def join_fields(row: dict[str, Any], fields: list[str]) -> str:
    return join_text(row_value(row, field) for field in fields)


def join_text(values: Iterable[Any]) -> str:
    seen = set()
    parts = []
    for value in values:
        text = clean_value(value)
        if not text or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n".join(parts)


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
        return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").split("\n") if line.strip()]
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
        "".join(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n" for record in records),
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
