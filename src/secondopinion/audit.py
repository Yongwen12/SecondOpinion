from __future__ import annotations

import hashlib
import json
import statistics
from typing import Any

from .claim_extraction import (
    CLAIM_EXTRACTION_VERSION,
    DEFAULT_CLAIM_MODEL,
    TONE_PROBLEM_WORDS,
    StructuredLLMClient,
    extract_claims,
)
from .model_config import DEFAULT_CHEAP_MODEL
from .models import ClaimAudit, Evidence, ReviewAudit
from .retrieval import RETRIEVAL_VERSION, retrieve_evidence
from .text import clean_text, tokens


RULE_MODEL_VERSION = "rule-baseline-v0.1"
LLM_JUDGE_VERSION = "review-point-judge-v0.2"
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
    requires_external = claim_type in {"novelty", "theory"}

    flags = []
    if verdict == "possibly_contradicted":
        flags.append("possibly-contradicted-by-paper")
    if verdict == "insufficient" and claim["importance"] in {"major", "medium"}:
        flags.append("unsupported-major-claim")
    if verdict == "vague_or_not_checkable":
        flags.append("vague-or-not-checkable")
    if specificity <= 1:
        flags.append("vague-criticism")
    if tone <= 2:
        flags.append("unprofessional-tone")
    if actionability <= 1 and claim["importance"] not in {"tone-only", "question"}:
        flags.append("missing-actionable-suggestions")
    if requires_human_expert:
        flags.append("requires-human-expert-check")
    if judge_error:
        flags.append("llm-judge-failed")

    return ClaimAudit(
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
        professionalism_score=professionalism_score,
        specificity_score=specificity_score,
        helpfulness_score=helpfulness_score,
        fairness_score=fairness_score,
        judge_version=judge_version,
        judge_model=judge_model_used,
        judge_rationale=judge_rationale,
        issue_flags=flags,
        evidence=evidence,
    )


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
            "content": (
                "You are SecondOpinion, an expert auditor of peer review quality. "
                "Evaluate one reviewer point against the manuscript evidence like a careful senior researcher. "
                "Do not decide whether the paper should be accepted. "
                "Use only the supplied paper, review, and retrieved review-time evidence. "
                "Do not use author responses, final decisions, or later revisions to score the reviewer point. "
                "Your core job is to decide whether the reviewer point is well supported, weakly supported, "
                "answered by the manuscript, or impossible to judge from the supplied evidence. "
                "Classify the review point as comment, question, suggestion, score_justification, summary, or other. "
                "For questions, judge whether the manuscript already answers the question and whether the question is useful. "
                "For suggestions, judge whether the suggestion is reasonable, actionable, and in scope. "
                "For score_justification, judge whether the stated reasons support the reviewer's rating. "
                "For comments, judge whether the critique is technically fair and manuscript-grounded. "
                "Use stance as SecondOpinion's single attitude toward the reviewer point: "
                "strongly_agree means the reviewer point is clearly valid and important; agree means mostly valid; "
                "mixed means partly valid, unclear, or evidence-limited; disagree means overstated or weakly supported; "
                "strongly_disagree means the manuscript evidence clearly answers or undermines the reviewer point. "
                "Return a direct SecondOpinion take for the end user; do not mention internal tools, prompts, or fallback logic. "
                "The take should be persuasive by juxtaposing the reviewer wording with manuscript evidence. "
                "Write the take in this order: first name the reviewer point, then quote the manuscript evidence, then state the conclusion. "
                "Use phrasing like: Reviewer argues that ...; the manuscript states ...; SecondOpinion concludes ..."
            ),
        },
        {
            "role": "user",
            "content": (
                "Return a structured expert assessment for this reviewer point. "
                "For comments, suggestions, and score justifications, support_score is 0-100: 0 means the reviewer point is not supported "
                "by the supplied manuscript evidence, and 100 means it is strongly supported. "
                "For questions, support_score should summarize overall usefulness, while answer_coverage_score says how much the manuscript "
                "already answers the question and question_value_score says how valuable the question is as a review point. "
                "stance is the primary user-facing judgment and must use one of: strongly_disagree, disagree, mixed, agree, strongly_agree. "
                "second_opinion_take should be one clear paragraph for a nontechnical user interface. "
                "It must explicitly refer to the reviewer point and quote manuscript evidence before giving the conclusion. "
                "quoted_manuscript_evidence should be a short exact quote or close excerpt from the retrieved evidence when available. "
                "Keep reasoning_summary concise and evidence-grounded.\n\n"
                f"Audit input JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


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
) -> ReviewAudit:
    extracted = extract_claims(review, llm_client=claim_llm_client, model=claim_model)
    claims = [
        audit_claim(
            paper,
            review,
            claim,
            judge_llm_client=judge_llm_client,
            judge_model=judge_model,
        )
        for claim in extracted
    ]
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
        "audits": audits,
    }
