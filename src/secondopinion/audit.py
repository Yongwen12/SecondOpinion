from __future__ import annotations

import hashlib
import json
import re
import statistics
from typing import Any

from .claim_extraction import (
    CLAIM_EXTRACTION_VERSION,
    DEFAULT_CLAIM_MODEL,
    TONE_PROBLEM_WORDS,
    StructuredLLMClient,
    extract_claims,
)
from .external_evidence import (
    DEFAULT_COLLECTOR_MODEL,
    EXTERNAL_CLAIM_TYPES,
    EXTERNAL_EVIDENCE_VERSION,
    attach_external_evidence_to_paper,
    collect_external_evidence_for_claims,
)
from .external_providers.openalex import OpenAlexClient
from .model_config import DEFAULT_CHEAP_MODEL
from .models import ClaimAudit, Evidence, ReviewAudit
from .prompt_assets import load_prompt
from .retrieval import RETRIEVAL_VERSION, retrieve_evidence
from .text import clean_text, tokens


RULE_MODEL_VERSION = "rule-baseline-v0.1"
LLM_JUDGE_VERSION = "review-point-judge-v0.4"
DEFAULT_JUDGE_MODEL = DEFAULT_CHEAP_MODEL
RUBRIC_VERSION = "iclr-review-audit-rubric-v0.1"

CLAIM_VERDICTS = (
    "supported",
    "partially_supported",
    "insufficient",
    "possibly_contradicted",
    "vague_or_not_checkable",
    "needs_human_check",
)
CONFIDENCE_VALUES = ("high", "medium", "low")
REVIEW_POINT_TYPES = ("comment", "question", "suggestion", "score_justification", "summary", "other")
SECONDOPINION_STANCES = (
    "strongly_disagree",
    "disagree",
    "mixed",
    "agree",
    "strongly_agree",
)
REBUTTAL_PRIORITIES = ("high", "medium", "low")
REBUTTAL_STRATEGIES = (
    "acknowledge_and_clarify",
    "cite_existing_evidence",
    "concede_and_fix",
    "add_experiment_or_analysis",
    "explain_scope",
    "challenge_politely",
    "seek_expert_context",
)
LEGACY_STANCE_MAP = {
    "well_supported": "agree",
    "partially_supported": "mixed",
    "weakly_supported": "disagree",
    "answered_or_contradicted": "strongly_disagree",
    "not_enough_context": "mixed",
    "too_broad_or_unclear": "mixed",
}
EVIDENCE_VERDICTS = (
    "supporting_candidate",
    "partial_candidate",
    "possibly_contradicting_candidate",
    "contradicting_candidate",
    "irrelevant",
    "not_enough_info",
)

ABSENCE_CLAIM_WORDS = (
    "lack",
    "lacks",
    "lacking",
    "missing",
    "insufficient",
    "without",
    "does not provide",
    "do not provide",
    "doesn't provide",
    "not compared",
    "not compare",
    "no ablation",
    "no baseline",
    "no comparison",
)
ACTION_WORDS = ("should", "could", "recommend", "suggest", "need to", "needs to", "clarify", "include", "compare")
SPECIFICITY_WORDS = (
    "section",
    "table",
    "figure",
    "appendix",
    "experiment",
    "baseline",
    "ablation",
    "equation",
    "theorem",
    "metric",
    "dataset",
    "citation",
)
TECHNICAL_WORDS = (
    "method",
    "experiment",
    "baseline",
    "ablation",
    "dataset",
    "metric",
    "theorem",
    "proof",
    "evaluation",
    "architecture",
    "algorithm",
)
EXPERT_REQUIRED_TYPES = {"novelty", "theory"}


def _id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def score_specificity(text: str) -> int:
    lowered = text.lower()
    score = sum(1 for word in SPECIFICITY_WORDS if word in lowered)
    has_number = any(char.isdigit() for char in text)
    if score >= 2 or (score >= 1 and has_number):
        return 4
    if score == 1:
        return 3
    if len(tokens(text)) >= 12:
        return 2
    return 1


def score_auditability(text: str, claim_type: str) -> int:
    if claim_type == "tone":
        return 4
    if claim_type in EXPERT_REQUIRED_TYPES:
        return 2
    if any(word in text.lower() for word in SPECIFICITY_WORDS):
        return 4
    if len(tokens(text)) >= 10:
        return 3
    if len(tokens(text)) >= 5:
        return 2
    return 1


def score_actionability(text: str) -> int:
    lowered = text.lower()
    if any(word in lowered for word in ACTION_WORDS):
        if "because" in lowered or "so that" in lowered or "impact" in lowered:
            return 4
        return 3
    if any(word in lowered for word in ("why", "how", "what")):
        return 2
    return 1


def score_tone(text: str) -> int:
    lowered = text.lower()
    hits = sum(1 for word in TONE_PROBLEM_WORDS if word in lowered)
    if hits >= 2:
        return 1
    if hits == 1:
        return 2
    if any(word in lowered for word in ("clearly wrong", "obviously")):
        return 3
    return 4


def classify_evidence_verdict(claim_text: str, evidence: list[Evidence], claim_type: str) -> tuple[str, str, int | None]:
    if claim_type in EXPERT_REQUIRED_TYPES:
        return "needs_human_check", "low", None
    if not evidence:
        return "insufficient", "low", 1

    best = evidence[0]
    lowered_claim = claim_text.lower()
    absence_claim = any(word in lowered_claim for word in ABSENCE_CLAIM_WORDS)
    strong_absence_counterevidence = best.score >= 0.35 and len(best.matched_terms) >= 2
    if absence_claim and best.section != "title" and strong_absence_counterevidence:
        for item in evidence:
            item.verdict = "possibly_contradicting_candidate"
            item.confidence = "medium" if item.score < 0.6 else "high"
        return "possibly_contradicted", evidence[0].confidence, 0
    if best.score >= 0.62:
        for item in evidence:
            item.verdict = "supporting_candidate"
            item.confidence = "medium" if item.score < 0.7 else "high"
        return "supported", evidence[0].confidence, 3
    if best.score >= 0.35:
        for item in evidence:
            item.verdict = "partial_candidate"
        return "partially_supported", "low", 2
    return "insufficient", "low", 1


def claim_issue_flags(
    *,
    verdict: str,
    importance: str,
    specificity: int,
    tone: int,
    actionability: int,
    requires_human_expert: bool,
    judge_error: str = "",
) -> list[str]:
    flags = []
    if verdict == "possibly_contradicted":
        flags.append("possibly-contradicted-by-paper")
    if verdict == "insufficient" and importance in {"major", "medium"}:
        flags.append("unsupported-major-claim")
    if verdict == "vague_or_not_checkable":
        flags.append("vague-or-not-checkable")
    if specificity <= 1:
        flags.append("vague-criticism")
    if tone <= 2:
        flags.append("unprofessional-tone")
    if actionability <= 1 and importance not in {"tone-only", "question"}:
        flags.append("missing-actionable-suggestions")
    if requires_human_expert:
        flags.append("requires-human-expert-check")
    if judge_error:
        flags.append("llm-judge-failed")
    return flags


def audit_claim(
    paper: dict[str, Any],
    review: dict[str, Any],
    claim: dict[str, Any],
    *,
    judge_llm_client: StructuredLLMClient | None = None,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> ClaimAudit:
    review_id = review.get("review_id", "review")
    claim_text = claim["claim_text"]
    claim_id = _id("claim", review_id, claim_text)
    claim_type = claim["claim_type"]
    auditability = score_auditability(claim_text, claim_type)
    specificity = score_specificity(claim_text)
    actionability = score_actionability(claim_text)
    tone = score_tone(claim_text)
    evidence = retrieve_evidence(
        claim_id,
        claim_text,
        paper,
        claim_type=claim_type,
        include_rebuttals=False,
    )
    verdict, confidence, evidence_score = classify_evidence_verdict(claim_text, evidence, claim_type)
    factual_alignment = evidence_score
    judge_version = RULE_MODEL_VERSION
    judge_model_used = ""
    judge_rationale = "Rule baseline verdict."
    judge_error = ""
    review_point_type = default_review_point_type(claim, claim_text)
    support_score = default_support_score(verdict, evidence_score)
    stance = default_stance(verdict, support_score)
    answer_coverage_score = default_answer_coverage_score(review_point_type, verdict, support_score)
    question_value_score = default_question_value_score(review_point_type, specificity, actionability)
    quoted_manuscript_evidence = best_evidence_quote(evidence)
    second_opinion_take = default_second_opinion_take(claim_text, verdict, quoted_manuscript_evidence)
    rebuttal_guidance = default_rebuttal_guidance(
        claim=claim,
        review_point_type=review_point_type,
        verdict=verdict,
        stance=stance,
        evidence=evidence,
    )
    reasoning_summary = judge_rationale
    professionalism_score = tone * 25
    specificity_score = specificity * 25
    helpfulness_score = actionability * 25
    fairness_score = default_fairness_score(verdict)

    if judge_llm_client is not None:
        judged = judge_claim_with_llm(
            paper,
            review,
            claim,
            evidence,
            llm_client=judge_llm_client,
            model=judge_model,
        )
        if judged["ok"]:
            verdict = judged["verdict"]
            confidence = judged["confidence"]
            evidence_score = judged["evidence_support"]
            factual_alignment = judged["factual_alignment"]
            severity = judged["severity_calibration"]
            judge_version = LLM_JUDGE_VERSION
            judge_model_used = judge_model
            judge_rationale = judged["rationale"]
            review_point_type = judged["review_point_type"]
            stance = judged["stance"]
            support_score = judged["support_score"]
            answer_coverage_score = judged["answer_coverage_score"]
            question_value_score = judged["question_value_score"]
            second_opinion_take = judged["second_opinion_take"]
            quoted_manuscript_evidence = judged["quoted_manuscript_evidence"]
            reasoning_summary = judged["reasoning_summary"]
            rebuttal_guidance = judged["rebuttal_guidance"]
            professionalism_score = judged["professionalism_score"]
            specificity_score = judged["specificity_score"]
            helpfulness_score = judged["helpfulness_score"]
            fairness_score = judged["fairness_score"]
        else:
            severity = 2 if claim_type in EXPERT_REQUIRED_TYPES or verdict == "needs_human_check" else (
                1 if verdict == "possibly_contradicted" else 3
            )
            judge_version = f"{LLM_JUDGE_VERSION}+fallback"
            judge_model_used = judge_model
            judge_rationale = "LLM judge failed; retained rule baseline verdict."
            judge_error = judged["error"]
            reasoning_summary = judge_rationale
    else:
        severity = 2 if claim_type in EXPERT_REQUIRED_TYPES or verdict == "needs_human_check" else (
            1 if verdict == "possibly_contradicted" else 3
        )

    requires_human_expert = claim_type in EXPERT_REQUIRED_TYPES or verdict == "needs_human_check"
    has_external_evidence = any(item.source_type in {"venue_guideline", "external_reference", "field_consensus"} for item in evidence)
    requires_external = claim_type in EXTERNAL_CLAIM_TYPES and not has_external_evidence

    flags = claim_issue_flags(
        verdict=verdict,
        importance=claim["importance"],
        specificity=specificity,
        tone=tone,
        actionability=actionability,
        requires_human_expert=requires_human_expert,
        judge_error=judge_error,
    )

    result = ClaimAudit(
        claim_id=claim_id,
        review_id=review_id,
        claim_text=claim_text,
        claim_type=claim_type,
        importance=claim["importance"],
        source_field=str(claim.get("source_field", "")),
        source_sentence_index=claim.get("source_sentence_index"),
        source_sentence=str(claim.get("source_sentence", "")),
        extraction_reason=str(claim.get("extraction_reason", "")),
        extraction_version=str(claim.get("extraction_version", CLAIM_EXTRACTION_VERSION)),
        auditability=auditability,
        specificity=specificity,
        evidence_support=evidence_score,
        factual_alignment=factual_alignment,
        severity_calibration=severity,
        actionability=actionability,
        tone=tone,
        verdict=verdict,
        audit_confidence=confidence,
        requires_external_knowledge=requires_external,
        requires_human_expert=requires_human_expert,
        review_point_type=review_point_type,
        stance=stance,
        support_score=support_score,
        answer_coverage_score=answer_coverage_score,
        question_value_score=question_value_score,
        second_opinion_take=second_opinion_take,
        quoted_manuscript_evidence=quoted_manuscript_evidence,
        reasoning_summary=reasoning_summary,
        rebuttal_guidance=rebuttal_guidance,
        professionalism_score=professionalism_score,
        specificity_score=specificity_score,
        helpfulness_score=helpfulness_score,
        fairness_score=fairness_score,
        judge_version=judge_version,
        judge_model=judge_model_used,
        judge_rationale=judge_rationale,
        issue_flags=flags,
        evidence=evidence,
        source_locator=claim.get("source_locator") if isinstance(claim.get("source_locator"), dict) else {},
        source_char_start=claim.get("source_char_start"),
        source_char_end=claim.get("source_char_end"),
        source_paragraph_index=claim.get("source_paragraph_index"),
        source_bullet_index=claim.get("source_bullet_index"),
        source_line_start=claim.get("source_line_start"),
        source_line_end=claim.get("source_line_end"),
    )
    apply_reliability_gate(result)
    return result


def judge_claim_with_llm(
    paper: dict[str, Any],
    review: dict[str, Any],
    claim: dict[str, Any],
    evidence: list[Evidence],
    *,
    llm_client: StructuredLLMClient,
    model: str,
) -> dict[str, Any]:
    try:
        payload = llm_client.complete_json(
            model=model,
            messages=build_judge_messages(paper, review, claim, evidence),
            schema_name="review_point_judgement",
            schema=judge_claim_schema(),
        )
        judged = validate_judge_payload(payload, evidence)
    except Exception as exc:  # noqa: BLE001 - keep the audit usable when the judge call fails.
        return {"ok": False, "error": str(exc)}
    if judged is None:
        return {"ok": False, "error": "LLM judge returned an invalid payload."}
    return {"ok": True, **judged}


def judge_review_claims_with_llm(
    paper: dict[str, Any],
    review: dict[str, Any],
    claims: list[ClaimAudit],
    *,
    llm_client: StructuredLLMClient,
    model: str,
) -> dict[str, Any]:
    if not claims:
        return {"ok": True, "judgements": {}}
    try:
        payload = llm_client.complete_json(
            model=model,
            messages=build_batch_judge_messages(paper, review, claims),
            schema_name="review_point_batch_judgement",
            schema=batch_judge_schema(),
        )
        judgements = validate_batch_judge_payload(payload, claims)
    except Exception as exc:  # noqa: BLE001 - keep the audit usable when the judge call fails.
        return {"ok": False, "error": str(exc)}
    if judgements is None:
        return {"ok": False, "error": "LLM batch judge returned an invalid payload."}
    return {"ok": True, "judgements": judgements}


def apply_batch_judgements(claims: list[ClaimAudit], batch_result: dict[str, Any], *, judge_model: str) -> None:
    if not claims:
        return
    if not batch_result["ok"]:
        for claim in claims:
            mark_claim_judge_failure(claim, judge_model=judge_model, error=batch_result["error"])
        return
    judgements = batch_result["judgements"]
    for claim in claims:
        judged = judgements.get(claim.claim_id)
        if judged is None:
            mark_claim_judge_failure(
                claim,
                judge_model=judge_model,
                error="LLM batch judge did not return a judgement for this claim.",
            )
            continue
        apply_judgement_to_claim(claim, judged, judge_model=judge_model)


def apply_batch_judgements_with_single_retry(
    paper: dict[str, Any],
    review: dict[str, Any],
    claims: list[ClaimAudit],
    batch_result: dict[str, Any],
    *,
    judge_llm_client: StructuredLLMClient,
    judge_model: str,
) -> None:
    if not claims or not batch_result.get("ok"):
        apply_batch_judgements(claims, batch_result, judge_model=judge_model)
        return
    judgements = batch_result["judgements"]
    for claim in claims:
        judged = judgements.get(claim.claim_id)
        if judged is not None:
            apply_judgement_to_claim(claim, judged, judge_model=judge_model)
            continue

        single_result = judge_claim_with_llm(
            paper,
            review,
            claim_to_extracted_payload(claim),
            claim.evidence,
            llm_client=judge_llm_client,
            model=judge_model,
        )
        if single_result["ok"]:
            apply_judgement_to_claim(claim, single_result, judge_model=judge_model)
        else:
            mark_claim_judge_failure(
                claim,
                judge_model=judge_model,
                error="LLM batch judge omitted this claim; single-claim retry failed.",
            )


def claim_to_extracted_payload(claim: ClaimAudit) -> dict[str, Any]:
    return {
        "claim_text": claim.claim_text,
        "claim_type": claim.claim_type,
        "importance": claim.importance,
        "source_field": claim.source_field,
        "source_sentence": claim.source_sentence,
    }


def apply_judgement_to_claim(claim: ClaimAudit, judged: dict[str, Any], *, judge_model: str) -> None:
    claim.verdict = judged["verdict"]
    claim.audit_confidence = judged["confidence"]
    claim.evidence_support = judged["evidence_support"]
    claim.factual_alignment = judged["factual_alignment"]
    claim.severity_calibration = judged["severity_calibration"]
    claim.review_point_type = judged["review_point_type"]
    claim.stance = judged["stance"]
    claim.support_score = judged["support_score"]
    claim.answer_coverage_score = judged["answer_coverage_score"]
    claim.question_value_score = judged["question_value_score"]
    claim.second_opinion_take = judged["second_opinion_take"]
    claim.quoted_manuscript_evidence = judged["quoted_manuscript_evidence"]
    claim.reasoning_summary = judged["reasoning_summary"]
    claim.rebuttal_guidance = judged["rebuttal_guidance"]
    claim.professionalism_score = judged["professionalism_score"]
    claim.specificity_score = judged["specificity_score"]
    claim.helpfulness_score = judged["helpfulness_score"]
    claim.fairness_score = judged["fairness_score"]
    claim.judge_version = LLM_JUDGE_VERSION
    claim.judge_model = judge_model
    claim.judge_rationale = judged["rationale"]
    claim.requires_human_expert = claim.claim_type in EXPERT_REQUIRED_TYPES or claim.verdict == "needs_human_check"
    has_external_evidence = any(item.source_type in {"venue_guideline", "external_reference", "field_consensus"} for item in claim.evidence)
    claim.requires_external_knowledge = claim.claim_type in EXTERNAL_CLAIM_TYPES and not has_external_evidence
    claim.issue_flags = claim_issue_flags(
        verdict=claim.verdict,
        importance=claim.importance,
        specificity=claim.specificity,
        tone=claim.tone,
        actionability=claim.actionability,
        requires_human_expert=claim.requires_human_expert,
    )
    apply_reliability_gate(claim)


def mark_claim_judge_failure(claim: ClaimAudit, *, judge_model: str, error: str) -> None:
    claim.judge_version = f"{LLM_JUDGE_VERSION}+fallback"
    claim.judge_model = judge_model
    claim.judge_rationale = "LLM batch judge failed; retained rule baseline verdict."
    claim.reasoning_summary = claim.judge_rationale
    _append_flag(claim.issue_flags, "llm-judge-failed")
    if error:
        _append_flag(claim.issue_flags, "llm-batch-judge-incomplete")
    apply_reliability_gate(claim)


def build_judge_messages(
    paper: dict[str, Any],
    review: dict[str, Any],
    claim: dict[str, Any],
    evidence: list[Evidence],
) -> list[dict[str, str]]:
    payload = {
        "paper": {
            "paper_id": paper.get("paper_id"),
            "title": clean_text(paper.get("title")),
            "abstract": clean_text(paper.get("abstract")),
        },
        "review": {
            "review_id": review.get("review_id"),
            "rating_raw": clean_text(review.get("rating_raw")),
            "rating_normalized": review.get("rating_normalized"),
            "confidence_raw": clean_text(review.get("confidence_raw")),
        },
        "claim": {
            "claim_text": clean_text(claim.get("claim_text")),
            "claim_type": clean_text(claim.get("claim_type")),
            "importance": clean_text(claim.get("importance")),
            "source_field": clean_text(claim.get("source_field")),
            "source_sentence": clean_text(claim.get("source_sentence")),
        },
        "retrieved_evidence": [
            {
                "evidence_id": item.evidence_id,
                "source_type": item.source_type,
                "section": item.section,
                "page": item.page,
                "retrieval_score": item.score,
                "matched_terms": item.matched_terms,
                "text": item.text,
            }
            for item in evidence
        ],
    }
    return [
        {
            "role": "system",
            "content": load_prompt("single_judge_system_v0.4.md"),
        },
        {
            "role": "user",
            "content": load_prompt(
                "single_judge_user_v0.4.md",
                audit_input_json=json.dumps(payload, ensure_ascii=False, indent=2),
            ),
        },
    ]


def build_batch_judge_messages(
    paper: dict[str, Any],
    review: dict[str, Any],
    claims: list[ClaimAudit],
) -> list[dict[str, str]]:
    payload = {
        "paper": {
            "paper_id": paper.get("paper_id"),
            "title": clean_text(paper.get("title")),
            "abstract": clean_text(paper.get("abstract")),
            "decision": clean_text(paper.get("decision")),
        },
        "review": {
            "review_id": review.get("review_id"),
            "rating_raw": clean_text(review.get("rating_raw")),
            "rating_normalized": review.get("rating_normalized"),
            "confidence_raw": clean_text(review.get("confidence_raw")),
        },
        "review_points": [
            {
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "claim_type": claim.claim_type,
                "importance": claim.importance,
                "source_field": claim.source_field,
                "source_sentence": claim.source_sentence,
                "baseline_verdict": claim.verdict,
                "retrieved_evidence": [
                    {
                        "evidence_id": item.evidence_id,
                        "source_type": item.source_type,
                        "section": item.section,
                        "page": item.page,
                        "retrieval_score": item.score,
                        "matched_terms": item.matched_terms,
                        "text": item.text,
                    }
                    for item in claim.evidence
                ],
            }
            for claim in claims
        ],
    }
    return [
        {
            "role": "system",
            "content": load_prompt("batch_judge_system_v0.4.md"),
        },
        {
            "role": "user",
            "content": load_prompt(
                "batch_judge_user_v0.4.md",
                batch_audit_input_json=json.dumps(payload, ensure_ascii=False, indent=2),
            ),
        },
    ]


def batch_judge_schema() -> dict[str, Any]:
    claim_schema = judge_claim_schema()
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "claim_judgements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "claim_id": {"type": "string"},
                        **claim_schema["properties"],
                    },
                    "required": ["claim_id", *claim_schema["required"]],
                },
            }
        },
        "required": ["claim_judgements"],
    }


def validate_batch_judge_payload(payload: dict[str, Any], claims: list[ClaimAudit]) -> dict[str, dict[str, Any]] | None:
    raw_judgements = payload.get("claim_judgements", [])
    if not isinstance(raw_judgements, list):
        return None
    by_id = {claim.claim_id: claim for claim in claims}
    judgements = {}
    for raw in raw_judgements:
        if not isinstance(raw, dict):
            continue
        claim_id = clean_text(raw.get("claim_id"))
        claim = by_id.get(claim_id)
        if claim is None:
            continue
        judged = validate_judge_payload(raw, claim.evidence)
        if judged is None:
            continue
        judgements[claim_id] = judged
    return judgements


def judge_claim_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "review_point_type": {"type": "string", "enum": list(REVIEW_POINT_TYPES)},
            "stance": {"type": "string", "enum": list(SECONDOPINION_STANCES)},
            "support_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "answer_coverage_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "question_value_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "verdict": {"type": "string", "enum": list(CLAIM_VERDICTS)},
            "confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES)},
            "evidence_support": {"type": ["integer", "null"], "minimum": 0, "maximum": 3},
            "factual_alignment": {"type": ["integer", "null"], "minimum": 0, "maximum": 3},
            "severity_calibration": {"type": ["integer", "null"], "minimum": 1, "maximum": 4},
            "second_opinion_take": {"type": "string"},
            "quoted_manuscript_evidence": {"type": "string"},
            "reasoning_summary": {"type": "string"},
            "rebuttal_guidance": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "priority": {"type": "string", "enum": list(REBUTTAL_PRIORITIES)},
                    "strategy": {"type": "string", "enum": list(REBUTTAL_STRATEGIES)},
                    "suggested_response": {"type": "string"},
                    "evidence_to_cite": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "risks_to_avoid": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "priority",
                    "strategy",
                    "suggested_response",
                    "evidence_to_cite",
                    "risks_to_avoid",
                ],
            },
            "professionalism_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "specificity_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "helpfulness_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "fairness_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "rationale": {"type": "string"},
            "evidence_assessments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "evidence_id": {"type": "string"},
                        "verdict": {"type": "string", "enum": list(EVIDENCE_VERDICTS)},
                        "confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES)},
                    },
                    "required": ["evidence_id", "verdict", "confidence"],
                },
            },
        },
        "required": [
            "review_point_type",
            "stance",
            "support_score",
            "answer_coverage_score",
            "question_value_score",
            "verdict",
            "confidence",
            "evidence_support",
            "factual_alignment",
            "severity_calibration",
            "second_opinion_take",
            "quoted_manuscript_evidence",
            "reasoning_summary",
            "rebuttal_guidance",
            "professionalism_score",
            "specificity_score",
            "helpfulness_score",
            "fairness_score",
            "rationale",
            "evidence_assessments",
        ],
    }


def validate_judge_payload(payload: dict[str, Any], evidence: list[Evidence]) -> dict[str, Any] | None:
    verdict = clean_text(payload.get("verdict"))
    if verdict not in CLAIM_VERDICTS:
        return None
    review_point_type = clean_text(payload.get("review_point_type"))
    if review_point_type not in REVIEW_POINT_TYPES:
        review_point_type = "comment"
    confidence = clean_text(payload.get("confidence"))
    if confidence not in CONFIDENCE_VALUES:
        confidence = "low"
    evidence_support = bounded_int(payload.get("evidence_support"), 0, 3)
    factual_alignment = bounded_int(payload.get("factual_alignment"), 0, 3)
    severity = bounded_int(payload.get("severity_calibration"), 1, 4)
    support_score = bounded_int(payload.get("support_score"), 0, 100)
    answer_coverage_score = bounded_int(payload.get("answer_coverage_score"), 0, 100)
    question_value_score = bounded_int(payload.get("question_value_score"), 0, 100)
    if evidence_support is None:
        evidence_support = default_evidence_support(verdict)
    if factual_alignment is None:
        factual_alignment = evidence_support
    if severity is None:
        severity = default_severity(verdict)
    if support_score is None:
        support_score = default_support_score(verdict, evidence_support)
    stance = normalize_stance(payload.get("stance"), verdict=verdict, support_score=support_score)
    if answer_coverage_score is None:
        answer_coverage_score = default_answer_coverage_score(review_point_type, verdict, support_score)
    if question_value_score is None:
        question_value_score = default_question_value_score(review_point_type, 2, 2)

    second_opinion_take = clean_text(payload.get("second_opinion_take"))
    quoted_manuscript_evidence = clean_text(payload.get("quoted_manuscript_evidence"))
    reasoning_summary = clean_text(payload.get("reasoning_summary"))
    rationale = clean_text(payload.get("rationale"))
    if not rationale:
        rationale = reasoning_summary or "The assessment is based on the retrieved manuscript evidence."
    if not reasoning_summary:
        reasoning_summary = rationale
    if not quoted_manuscript_evidence:
        quoted_manuscript_evidence = best_evidence_quote(evidence)
    if not second_opinion_take:
        second_opinion_take = default_second_opinion_take("", verdict, quoted_manuscript_evidence)
    rebuttal_guidance = validate_rebuttal_guidance(
        payload.get("rebuttal_guidance"),
        verdict=verdict,
        stance=stance,
        evidence=evidence,
    )

    professionalism_score = bounded_int(payload.get("professionalism_score"), 0, 100)
    specificity_score = bounded_int(payload.get("specificity_score"), 0, 100)
    helpfulness_score = bounded_int(payload.get("helpfulness_score"), 0, 100)
    fairness_score = bounded_int(payload.get("fairness_score"), 0, 100)

    by_id = {item.evidence_id: item for item in evidence}
    for assessment in payload.get("evidence_assessments", []):
        if not isinstance(assessment, dict):
            continue
        item = by_id.get(clean_text(assessment.get("evidence_id")))
        if item is None:
            continue
        evidence_verdict = clean_text(assessment.get("verdict"))
        evidence_confidence = clean_text(assessment.get("confidence"))
        if evidence_verdict in EVIDENCE_VERDICTS:
            item.verdict = evidence_verdict
        if evidence_confidence in CONFIDENCE_VALUES:
            item.confidence = evidence_confidence

    return {
        "review_point_type": review_point_type,
        "stance": stance,
        "support_score": support_score,
        "answer_coverage_score": answer_coverage_score,
        "question_value_score": question_value_score,
        "verdict": verdict,
        "confidence": confidence,
        "evidence_support": evidence_support,
        "factual_alignment": factual_alignment,
        "severity_calibration": severity,
        "second_opinion_take": second_opinion_take,
        "quoted_manuscript_evidence": quoted_manuscript_evidence,
        "reasoning_summary": reasoning_summary,
        "rebuttal_guidance": rebuttal_guidance,
        "professionalism_score": professionalism_score,
        "specificity_score": specificity_score,
        "helpfulness_score": helpfulness_score,
        "fairness_score": fairness_score,
        "rationale": rationale,
    }


def bounded_int(value: Any, minimum: int, maximum: int) -> int | None:
    if value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return min(max(number, minimum), maximum)


def default_evidence_support(verdict: str) -> int | None:
    if verdict == "supported":
        return 3
    if verdict == "partially_supported":
        return 2
    if verdict in {"insufficient", "vague_or_not_checkable"}:
        return 1
    if verdict == "possibly_contradicted":
        return 0
    return None


def default_severity(verdict: str) -> int | None:
    if verdict == "possibly_contradicted":
        return 1
    if verdict == "needs_human_check":
        return 2
    if verdict == "supported":
        return 4
    return 3


def default_review_point_type(claim: dict[str, Any], claim_text: str) -> str:
    importance = clean_text(claim.get("importance")).lower()
    source_field = clean_text(claim.get("source_field")).lower()
    lowered = claim_text.lower().strip()
    if importance == "question" or source_field == "questions" or lowered.endswith("?"):
        return "question"
    if any(phrase in lowered for phrase in ("i rate", "my score", "i give", "rating", "score is")):
        return "score_justification"
    if any(word in lowered for word in ("should", "could", "recommend", "suggest")):
        return "suggestion"
    if source_field == "summary":
        return "summary"
    return "comment"


def normalize_stance(value: Any, *, verdict: str, support_score: int | None = None) -> str:
    stance = clean_text(value)
    if stance in SECONDOPINION_STANCES:
        return stance
    if stance in LEGACY_STANCE_MAP:
        return LEGACY_STANCE_MAP[stance]
    return default_stance(verdict, support_score)


def default_stance(verdict: str, support_score: int | None = None) -> str:
    if isinstance(support_score, int):
        if support_score >= 82:
            return "strongly_agree"
        if support_score >= 62:
            return "agree"
        if support_score >= 40:
            return "mixed"
        if support_score >= 20:
            return "disagree"
        return "strongly_disagree"
    if verdict == "supported":
        return "agree"
    if verdict == "partially_supported":
        return "mixed"
    if verdict == "possibly_contradicted":
        return "strongly_disagree"
    if verdict in {"insufficient", "vague_or_not_checkable", "needs_human_check"}:
        return "mixed"
    return "mixed"


def default_support_score(verdict: str, evidence_support: int | None) -> int:
    if verdict == "supported":
        base = 85
    elif verdict == "partially_supported":
        base = 58
    elif verdict == "insufficient":
        base = 30
    elif verdict == "possibly_contradicted":
        base = 18
    elif verdict == "vague_or_not_checkable":
        base = 40
    else:
        base = 50
    if verdict in {"supported", "partially_supported", "insufficient"} and isinstance(evidence_support, int):
        base = round((base + max(0, min(3, evidence_support)) / 3 * 100) / 2)
    return int(max(0, min(100, base)))


def default_fairness_score(verdict: str) -> int:
    if verdict == "supported":
        return 80
    if verdict == "partially_supported":
        return 60
    if verdict == "possibly_contradicted":
        return 35
    if verdict == "vague_or_not_checkable":
        return 45
    return 50


def default_answer_coverage_score(review_point_type: str, verdict: str, support_score: int) -> int:
    if review_point_type != "question":
        return 0
    if verdict == "possibly_contradicted":
        return 80
    if verdict == "supported":
        return 70
    if verdict == "partially_supported":
        return 50
    if verdict == "insufficient":
        return 20
    return support_score


def default_question_value_score(review_point_type: str, specificity: int, actionability: int) -> int:
    if review_point_type != "question":
        return 0
    return int(max(0, min(100, round(((specificity + actionability) / 8) * 100))))


def best_evidence_quote(evidence: list[Evidence], max_chars: int = 240) -> str:
    if not evidence:
        return ""
    text = clean_text(evidence[0].text)
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{clipped}..."


def default_second_opinion_take(review_point: str, verdict: str, quote: str) -> str:
    prefix = f'Reviewer argues: "{review_point}". ' if review_point else ""
    evidence = f'The manuscript states: "{quote}". ' if quote else ""
    if verdict == "supported":
        return f"{prefix}{evidence}SecondOpinion concludes that this review point is well supported."
    if verdict == "partially_supported":
        return f"{prefix}{evidence}SecondOpinion concludes that this review point is only partly supported."
    if verdict == "possibly_contradicted":
        return f"{prefix}{evidence}SecondOpinion concludes that this review point is weakly supported because the manuscript appears to address it."
    if verdict == "insufficient":
        return f"{prefix}{evidence}SecondOpinion concludes that there is too little manuscript support for this review point."
    if verdict == "vague_or_not_checkable":
        return f"{prefix}{evidence}SecondOpinion concludes that this review point is too broad to evaluate cleanly from the manuscript."
    return f"{prefix}{evidence}SecondOpinion cannot make a strong support judgment from the available manuscript evidence."


def apply_reliability_gate(claim: ClaimAudit) -> None:
    copy_changed = sanitize_user_facing_fields(claim)
    quote_changed = verify_claim_quote(claim)
    confidence_changed = downgrade_evidence_limited_confidence(claim)
    stance_changed = normalize_claim_stance_consistency(claim)
    if quote_changed:
        _append_flag(claim.issue_flags, "unverified-quoted-evidence")
    if confidence_changed:
        _append_flag(claim.issue_flags, "confidence-downgraded-evidence-limited")
    if stance_changed:
        _append_flag(claim.issue_flags, "stance-corrected-by-reliability-gate")


def verify_claim_quote(claim: ClaimAudit) -> bool:
    quote = clean_text(claim.quoted_manuscript_evidence)
    if not quote:
        return False
    if quote_in_evidence(quote, claim.evidence):
        return False
    replacement = best_evidence_quote(claim.evidence)
    claim.quoted_manuscript_evidence = replacement
    claim.second_opinion_take = default_second_opinion_take(claim.claim_text, claim.verdict, replacement)
    return True


def quote_in_evidence(quote: str, evidence: list[Evidence]) -> bool:
    normalized_quote = normalize_for_evidence_match(quote)
    if not normalized_quote:
        return False
    for item in evidence:
        normalized_text = normalize_for_evidence_match(item.text)
        if normalized_quote and normalized_quote in normalized_text:
            return True
    return False


def normalize_for_evidence_match(text: str) -> str:
    text = clean_text(text).lower()
    return " ".join(tokens(text))


def downgrade_evidence_limited_confidence(claim: ClaimAudit) -> bool:
    if claim.audit_confidence != "high":
        return False
    limited_verdict = claim.verdict in {"insufficient", "vague_or_not_checkable", "needs_human_check"}
    weak_evidence = claim.evidence_support is None or claim.evidence_support <= 1 or not claim.evidence
    if not (limited_verdict or weak_evidence):
        return False
    claim.audit_confidence = "low" if claim.verdict in {"insufficient", "needs_human_check"} or not claim.evidence else "medium"
    return True


def normalize_claim_stance_consistency(claim: ClaimAudit) -> bool:
    expected = reliability_stance_for_verdict(claim.verdict)
    changed = False
    if claim.verdict in {"insufficient", "vague_or_not_checkable", "needs_human_check"} and (
        claim.support_score is not None and claim.support_score > 60
    ):
        claim.support_score = 40 if claim.verdict == "vague_or_not_checkable" else 30
        changed = True
    incompatible = {
        "supported": {"disagree", "strongly_disagree"},
        "partially_supported": {"strongly_agree", "strongly_disagree"},
        "possibly_contradicted": {"agree", "strongly_agree"},
        "insufficient": {"strongly_agree"},
        "vague_or_not_checkable": {"strongly_agree"},
        "needs_human_check": {"strongly_agree"},
    }
    if claim.stance not in SECONDOPINION_STANCES:
        claim.stance = expected
        return True
    if claim.stance in incompatible.get(claim.verdict, set()):
        claim.stance = expected
        return True
    return changed


def reliability_stance_for_verdict(verdict: str) -> str:
    if verdict == "supported":
        return "agree"
    if verdict == "partially_supported":
        return "mixed"
    if verdict == "possibly_contradicted":
        return "strongly_disagree"
    if verdict in {"insufficient", "vague_or_not_checkable", "needs_human_check"}:
        return "mixed"
    return "mixed"


def sanitize_user_facing_fields(claim: ClaimAudit) -> bool:
    changed = sanitize_user_facing_take(claim)
    for attribute in ("second_opinion_take", "reasoning_summary", "judge_rationale"):
        original = clean_text(getattr(claim, attribute))
        cleaned = scrub_internal_references(original)
        if cleaned != original:
            setattr(claim, attribute, cleaned)
            changed = True
    return changed


def sanitize_user_facing_take(claim: ClaimAudit) -> bool:
    take = clean_text(claim.second_opinion_take)
    developer_terms = (
        "prompt",
        "schema",
        "fallback",
        "rebuttal guidance",
        "llm",
        "json",
        "retrieval score",
        "human check",
        "internal",
        "reviewer point:",
        "manuscript evidence:",
        "conclusion:",
    )
    if take and not any(term in take.lower() for term in developer_terms):
        return False
    claim.second_opinion_take = default_second_opinion_take(
        claim.claim_text,
        claim.verdict,
        claim.quoted_manuscript_evidence,
    )
    return True


def scrub_internal_references(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    cleaned = re.sub(
        r"\bsimilar to\s+claim_[a-z0-9]+(?:_ev\d+)?\b",
        "similar to another extracted review point",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bclaim_[a-z0-9]+_ev\d+\b",
        "the cited evidence",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bclaim_[a-z0-9]+\b",
        "another extracted review point",
        cleaned,
        flags=re.IGNORECASE,
    )
    return clean_text(cleaned)


def default_rebuttal_guidance(
    *,
    claim: dict[str, Any],
    review_point_type: str,
    verdict: str,
    stance: str,
    evidence: list[Evidence],
) -> dict[str, Any]:
    importance = clean_text(claim.get("importance")).lower()
    claim_type = clean_text(claim.get("claim_type")).lower()
    citations = evidence_citation_labels(evidence)
    citation_text = ", ".join(citations) if citations else "the most relevant manuscript passage"

    if importance == "major" or stance in {"strongly_agree", "strongly_disagree"}:
        priority = "high"
    elif importance in {"minor", "tone-only"} and verdict not in {"possibly_contradicted", "supported"}:
        priority = "low"
    else:
        priority = "medium"

    if verdict == "possibly_contradicted":
        strategy = "cite_existing_evidence"
        suggested_response = (
            f"Politely point to {citation_text}, quote the relevant text, and add a short clarification so the answer is easier to find."
        )
        risks = [
            "Do not simply say the reviewer is wrong.",
            "Do not cite a passage unless it directly answers the reviewer wording.",
        ]
    elif verdict == "supported":
        strategy = "concede_and_fix" if review_point_type != "question" else "acknowledge_and_clarify"
        suggested_response = (
            "Acknowledge the concern, describe the concrete revision or clarification, and name where it will appear in the manuscript."
        )
        risks = [
            "Do not over-defend a point that the evidence supports.",
            "Do not promise experiments or edits that cannot be completed.",
        ]
    elif verdict == "partially_supported":
        strategy = "acknowledge_and_clarify"
        suggested_response = (
            f"Acknowledge the valid part, cite {citation_text}, and clarify what the manuscript already covers versus what you will improve."
        )
        risks = [
            "Do not treat partial evidence as a complete answer.",
            "Do not ignore the actionable part of the reviewer point.",
        ]
    elif verdict == "needs_human_check" or claim_type in EXPERT_REQUIRED_TYPES:
        strategy = "seek_expert_context"
        suggested_response = (
            "Use field-specific evidence or an expert citation, and frame the response cautiously because this point needs specialist judgment."
        )
        risks = [
            "Do not rely only on the retrieved passage for a specialist claim.",
            "Do not make broad novelty or theory claims without support.",
        ]
    elif verdict == "vague_or_not_checkable":
        strategy = "explain_scope"
        suggested_response = (
            "Respond narrowly: state what the manuscript does cover, add a clarifying sentence if useful, and avoid expanding beyond the reviewer's wording."
        )
        risks = [
            "Do not answer a broader critique than the reviewer actually made.",
            "Do not escalate a vague point into an unnecessary major revision.",
        ]
    elif verdict == "insufficient":
        strategy = "challenge_politely"
        suggested_response = (
            f"Give a brief, respectful response grounded in {citation_text}, and add stronger evidence only if the point is decision-relevant."
        )
        risks = [
            "Do not claim the manuscript fully resolves the point without direct evidence.",
            "Do not spend too much space on a low-specificity issue.",
        ]
    else:
        strategy = "acknowledge_and_clarify"
        suggested_response = (
            "Acknowledge the reviewer point, cite the strongest available evidence, and state the narrow clarification or revision you can make."
        )
        risks = ["Do not overstate what the current manuscript evidence proves."]

    if review_point_type == "suggestion" and verdict in {"supported", "partially_supported"}:
        strategy = "add_experiment_or_analysis"
        suggested_response = (
            "Acknowledge the suggestion and, if feasible, add the requested experiment or analysis; otherwise explain the scope limit and cite existing evidence."
        )

    return {
        "priority": priority,
        "strategy": strategy,
        "suggested_response": suggested_response,
        "evidence_to_cite": citations,
        "risks_to_avoid": risks,
    }


def validate_rebuttal_guidance(
    value: Any,
    *,
    verdict: str,
    stance: str,
    evidence: list[Evidence],
) -> dict[str, Any]:
    default = default_rebuttal_guidance(
        claim={},
        review_point_type="",
        verdict=verdict,
        stance=stance,
        evidence=evidence,
    )
    if not isinstance(value, dict):
        return default

    priority = clean_text(value.get("priority")).lower()
    if priority not in REBUTTAL_PRIORITIES:
        priority = default["priority"]

    strategy = clean_text(value.get("strategy")).lower()
    if strategy not in REBUTTAL_STRATEGIES:
        strategy = default["strategy"]

    suggested_response = clean_text(value.get("suggested_response")) or default["suggested_response"]
    evidence_to_cite = humanize_evidence_citations(value.get("evidence_to_cite"), evidence) or default[
        "evidence_to_cite"
    ]
    risks_to_avoid = clean_string_list(value.get("risks_to_avoid")) or default["risks_to_avoid"]

    return {
        "priority": priority,
        "strategy": strategy,
        "suggested_response": suggested_response,
        "evidence_to_cite": evidence_to_cite[:4],
        "risks_to_avoid": risks_to_avoid[:4],
    }


def clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        text = clean_text(item)
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def humanize_evidence_citations(value: Any, evidence: list[Evidence]) -> list[str]:
    raw_items = clean_string_list(value)
    if not raw_items:
        return []
    by_id = {item.evidence_id: evidence_citation_label(item) for item in evidence}
    cleaned = []
    for item in raw_items:
        label = by_id.get(item, item)
        if label.startswith("claim_") and "_ev" in label:
            continue
        if label and label not in cleaned:
            cleaned.append(label)
    return cleaned


def evidence_citation_labels(evidence: list[Evidence], limit: int = 2) -> list[str]:
    labels = []
    for item in evidence[:limit]:
        label = evidence_citation_label(item)
        if label not in labels:
            labels.append(label)
    return labels


def evidence_citation_label(item: Evidence) -> str:
    if item.source_type == "rebuttal":
        label = "Author response"
    elif item.source_type == "venue_guideline":
        venue = item.metadata.get("venue") or "Venue"
        label = f"{venue} guideline"
    elif item.source_type == "external_reference":
        title = item.metadata.get("title") or item.section
        year = item.metadata.get("publication_year")
        label = f"External reference: {title}"
        if year:
            label = f"{label} ({year})"
    elif item.source_type == "field_consensus":
        label = "Field context"
    elif item.section == "title":
        label = "Paper title"
    elif item.section == "abstract":
        label = "Paper abstract"
    elif item.section:
        label = f"Section {item.section}"
    else:
        label = "Manuscript"
    if item.page:
        label = f"{label} p.{item.page}"
    return label


def score_review_text_consistency(review: dict[str, Any], claims: list[ClaimAudit]) -> tuple[int, bool]:
    rating = review.get("rating_normalized")
    if rating is None:
        return 3, False
    issue_count = sum(1 for claim in claims if claim.importance in {"major", "medium"})
    severe_issue_count = sum(
        1 for claim in claims if claim.verdict in {"possibly_contradicted", "insufficient"} and claim.importance == "major"
    )
    if rating <= 4 and issue_count == 0:
        return 1, True
    if rating >= 8 and severe_issue_count >= 2:
        return 1, True
    if rating >= 7 and severe_issue_count >= 1:
        return 2, True
    return 4, False


def dimension_average(claims: list[ClaimAudit], attribute: str, default: float = 2.5) -> float:
    values = [getattr(claim, attribute) for claim in claims if getattr(claim, attribute) is not None]
    return float(statistics.mean(values)) if values else default


def audit_review(
    paper: dict[str, Any],
    review: dict[str, Any],
    *,
    claim_llm_client: StructuredLLMClient | None = None,
    claim_model: str = DEFAULT_CLAIM_MODEL,
    judge_llm_client: StructuredLLMClient | None = None,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    auditor_version: str = RULE_MODEL_VERSION,
    use_external_evidence: bool = False,
    external_providers: str | list[str] | tuple[str, ...] | None = None,
    external_llm_client: StructuredLLMClient | None = None,
    external_model: str = DEFAULT_COLLECTOR_MODEL,
    openalex_client: OpenAlexClient | None = None,
) -> ReviewAudit:
    extracted = extract_claims(review, llm_client=claim_llm_client, model=claim_model)
    paper_for_audit = paper
    if use_external_evidence and extracted:
        external_records, _ = collect_external_evidence_for_claims(
            paper,
            extracted,
            review=review,
            providers=external_providers,
            llm_client=external_llm_client,
            model=external_model,
            openalex_client=openalex_client,
        )
        paper_for_audit = attach_external_evidence_to_paper(paper, external_records)
    claims = [
        audit_claim(
            paper_for_audit,
            review,
            claim,
        )
        for claim in extracted
    ]
    if judge_llm_client is not None and claims:
        batch_result = judge_review_claims_with_llm(
            paper_for_audit,
            review,
            claims,
            llm_client=judge_llm_client,
            model=judge_model,
        )
        apply_batch_judgements_with_single_retry(
            paper_for_audit,
            review,
            claims,
            batch_result,
            judge_llm_client=judge_llm_client,
            judge_model=judge_model,
        )
    review_text = review.get("review_text") or ""
    lowered = review_text.lower()

    evidence_grounded = dimension_average(claims, "evidence_support", default=2.0)
    specificity = dimension_average(claims, "specificity")
    constructiveness = dimension_average(claims, "actionability")
    professionalism = dimension_average(claims, "tone", default=4.0)
    score_consistency, mismatch = score_review_text_consistency(review, claims)
    technical_hits = sum(1 for word in TECHNICAL_WORDS if word in lowered)
    technical_substance = min(4, max(1, technical_hits // 2 + (1 if len(tokens(review_text)) > 35 else 0)))
    balance = 4 if review.get("strengths") and review.get("weaknesses") else 2.5
    guideline = 3 if review_text else 1

    dimensions = {
        "claim_accuracy_and_evidence": evidence_grounded,
        "technical_substance": float(technical_substance),
        "specificity": specificity,
        "constructiveness": constructiveness,
        "balance_and_fairness": float(balance),
        "professional_tone": professionalism,
        "score_text_consistency": float(score_consistency),
        "venue_guideline_compliance": float(guideline),
    }
    weighted = (
        dimensions["claim_accuracy_and_evidence"] / 4 * 30
        + dimensions["technical_substance"] / 4 * 15
        + dimensions["specificity"] / 4 * 12
        + dimensions["constructiveness"] / 4 * 12
        + dimensions["balance_and_fairness"] / 4 * 10
        + dimensions["professional_tone"] / 4 * 8
        + dimensions["score_text_consistency"] / 4 * 8
        + dimensions["venue_guideline_compliance"] / 4 * 5
    )
    rqs = max(0, min(100, round(weighted)))

    flags = sorted({flag for claim in claims for flag in claim.issue_flags})
    if mismatch:
        _append_flag(flags, "score-text-mismatch")
    if constructiveness <= 1.5:
        _append_flag(flags, "missing-actionable-suggestions")
    if not claims:
        _append_flag(flags, "no-auditable-claims-found")

    confidence_values = [claim.audit_confidence for claim in claims]
    if any(value == "high" for value in confidence_values) and not any(value == "low" for value in confidence_values):
        audit_confidence = "high"
    elif any(value == "medium" for value in confidence_values):
        audit_confidence = "medium"
    else:
        audit_confidence = "low"

    summary = summarize_review_audit(rqs, flags, claims)

    return ReviewAudit(
        audit_id=_id("audit", paper.get("paper_id", ""), review.get("review_id", "")),
        review_id=review.get("review_id", ""),
        paper_id=paper.get("paper_id", ""),
        paper_title=clean_text(paper.get("title")),
        decision=clean_text(paper.get("decision")) or "Unknown",
        rating_raw=clean_text(review.get("rating_raw")),
        rating_normalized=review.get("rating_normalized"),
        reviewer_confidence_raw=clean_text(review.get("confidence_raw")),
        reviewer_confidence_normalized=review.get("confidence_normalized"),
        model_version=auditor_version,
        rubric_version=RUBRIC_VERSION,
        claim_extraction_version=CLAIM_EXTRACTION_VERSION,
        retrieval_version=RETRIEVAL_VERSION,
        judge_version=LLM_JUDGE_VERSION if judge_llm_client is not None else RULE_MODEL_VERSION,
        judge_model=judge_model if judge_llm_client is not None else "",
        rqs_score=rqs,
        audit_confidence=audit_confidence,
        issue_flags=flags,
        summary=summary,
        dimensions={key: round(value, 2) for key, value in dimensions.items()},
        claims=claims,
    )


def summarize_review_audit(rqs: int, flags: list[str], claims: list[ClaimAudit]) -> str:
    if not claims:
        return "No auditable claims were extracted from this review."
    if rqs >= 75 and not flags:
        return "The review appears specific, professional, and broadly supported by available evidence."
    if "possibly-contradicted-by-paper" in flags:
        return "At least one critique appears weakened by evidence already present in the manuscript."
    if "unsupported-major-claim" in flags:
        return "Some major criticisms currently lack supporting evidence in the available materials."
    if "unprofessional-tone" in flags:
        return "The review contains language that may fall below a professional tone standard."
    return "The review has mixed evidence support and may benefit from sharper, more actionable reasoning."


def _append_flag(flags: list[str], flag: str) -> None:
    if flag not in flags:
        flags.append(flag)


def audit_dataset(
    dataset: dict[str, Any],
    *,
    claim_llm_client: StructuredLLMClient | None = None,
    claim_model: str = DEFAULT_CLAIM_MODEL,
    judge_llm_client: StructuredLLMClient | None = None,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    use_llm_judge: bool = False,
    use_external_evidence: bool = False,
    external_providers: str | list[str] | tuple[str, ...] | None = None,
    external_llm_client: StructuredLLMClient | None = None,
    external_model: str = DEFAULT_COLLECTOR_MODEL,
    openalex_client: OpenAlexClient | None = None,
) -> dict[str, Any]:
    audits = []
    review_count = sum(len(paper.get("reviews", [])) for paper in dataset.get("papers", []))
    if review_count and claim_llm_client is None:
        from .llm_client import OpenAIChatClient

        claim_llm_client = OpenAIChatClient.from_env()
    if use_llm_judge and judge_llm_client is None:
        judge_llm_client = claim_llm_client
    auditor_version = LLM_JUDGE_VERSION if use_llm_judge else RULE_MODEL_VERSION

    for paper in dataset.get("papers", []):
        for review in paper.get("reviews", []):
            audits.append(
                audit_review(
                    paper,
                    review,
                    claim_llm_client=claim_llm_client,
                    claim_model=claim_model,
                    judge_llm_client=judge_llm_client if use_llm_judge else None,
                    judge_model=judge_model,
                    auditor_version=auditor_version,
                    use_external_evidence=use_external_evidence,
                    external_providers=external_providers,
                    external_llm_client=external_llm_client or claim_llm_client,
                    external_model=external_model,
                    openalex_client=openalex_client,
                ).to_dict()
            )
    return {
        "schema_version": "0.1",
        "dataset": dataset.get("dataset", "unknown"),
        "paper_count": len(dataset.get("papers", [])),
        "review_count": review_count,
        "audit_count": len(audits),
        "model_version": auditor_version,
        "rubric_version": RUBRIC_VERSION,
        "claim_extraction_version": CLAIM_EXTRACTION_VERSION,
        "claim_model": claim_model,
        "judge_version": LLM_JUDGE_VERSION if use_llm_judge else RULE_MODEL_VERSION,
        "judge_model": judge_model if use_llm_judge else "",
        "retrieval_version": RETRIEVAL_VERSION,
        "external_evidence_version": EXTERNAL_EVIDENCE_VERSION if use_external_evidence else "",
        "openalex_stats": openalex_client.stats_dict() if openalex_client is not None else {},
        "audits": audits,
    }
