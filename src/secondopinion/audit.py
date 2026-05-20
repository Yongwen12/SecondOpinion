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
from .models import ClaimAudit, Evidence, ReviewAudit
from .retrieval import RETRIEVAL_VERSION, retrieve_evidence
from .text import clean_text, tokens


RULE_MODEL_VERSION = "rule-baseline-v0.1"
LLM_JUDGE_VERSION = "llm-rag-judge-v0.1"
DEFAULT_JUDGE_MODEL = "gpt-4o-mini"
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
EVIDENCE_VERDICTS = (
    "supporting_candidate",
    "partial_candidate",
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
    evidence = retrieve_evidence(claim_id, claim_text, paper, claim_type=claim_type)
    verdict, confidence, evidence_score = classify_evidence_verdict(claim_text, evidence, claim_type)
    factual_alignment = evidence_score
    judge_version = RULE_MODEL_VERSION
    judge_model_used = ""
    judge_rationale = "Rule baseline verdict."
    judge_error = ""

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
        else:
            severity = 2 if claim_type in EXPERT_REQUIRED_TYPES or verdict == "needs_human_check" else (
                1 if verdict == "possibly_contradicted" else 3
            )
            judge_version = f"{LLM_JUDGE_VERSION}+fallback"
            judge_model_used = judge_model
            judge_rationale = "LLM judge failed; retained rule baseline verdict."
            judge_error = judged["error"]
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
            schema_name="review_claim_verdict_judgement",
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
            "decision": clean_text(paper.get("decision")),
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
                "You are auditing the quality of a peer review claim. "
                "Judge whether the review claim is grounded in the supplied paper evidence. "
                "Do not decide whether the paper should be accepted. "
                "Use only the supplied paper, review, and retrieved evidence. "
                "For claims that something is missing, mark possibly_contradicted when the evidence shows it exists. "
                "Mark needs_human_check when the claim requires field consensus, novelty judgement, or expert theory review. "
                "Mark vague_or_not_checkable when the claim is too broad to verify against paper evidence."
            ),
        },
        {
            "role": "user",
            "content": (
                "Return a structured verdict for this review claim. "
                "supported means the review criticism is supported by the evidence. "
                "possibly_contradicted means the criticism may be false or overstated given the evidence. "
                "Keep the rationale short and evidence-grounded.\n\n"
                f"Audit input JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def judge_claim_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verdict": {"type": "string", "enum": list(CLAIM_VERDICTS)},
            "confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES)},
            "evidence_support": {"type": ["integer", "null"], "minimum": 0, "maximum": 3},
            "factual_alignment": {"type": ["integer", "null"], "minimum": 0, "maximum": 3},
            "severity_calibration": {"type": ["integer", "null"], "minimum": 1, "maximum": 4},
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
            "verdict",
            "confidence",
            "evidence_support",
            "factual_alignment",
            "severity_calibration",
            "rationale",
            "evidence_assessments",
        ],
    }


def validate_judge_payload(payload: dict[str, Any], evidence: list[Evidence]) -> dict[str, Any] | None:
    verdict = clean_text(payload.get("verdict"))
    if verdict not in CLAIM_VERDICTS:
        return None
    confidence = clean_text(payload.get("confidence"))
    if confidence not in CONFIDENCE_VALUES:
        confidence = "low"
    evidence_support = bounded_int(payload.get("evidence_support"), 0, 3)
    factual_alignment = bounded_int(payload.get("factual_alignment"), 0, 3)
    severity = bounded_int(payload.get("severity_calibration"), 1, 4)
    if evidence_support is None:
        evidence_support = default_evidence_support(verdict)
    if factual_alignment is None:
        factual_alignment = evidence_support
    if severity is None:
        severity = default_severity(verdict)

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
        "verdict": verdict,
        "confidence": confidence,
        "evidence_support": evidence_support,
        "factual_alignment": factual_alignment,
        "severity_calibration": severity,
        "rationale": clean_text(payload.get("rationale")) or "LLM judge returned no rationale.",
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
        return "At least one criticism may be contradicted by available paper evidence; human verification is recommended."
    if "unsupported-major-claim" in flags:
        return "Some major criticisms currently lack supporting evidence in the available materials."
    if "unprofessional-tone" in flags:
        return "The review contains language that may fall below a professional tone standard."
    return "The review is partially auditable, with mixed evidence and room for calibration."


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
