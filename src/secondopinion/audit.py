from __future__ import annotations

import hashlib
import statistics
from typing import Any

from .claim_extraction import CLAIM_EXTRACTION_VERSION, TONE_PROBLEM_WORDS, extract_claims
from .models import ClaimAudit, Evidence, ReviewAudit
from .retrieval import RETRIEVAL_VERSION, retrieve_evidence
from .text import tokens


MODEL_VERSION = "rule-baseline-v0.1"
RUBRIC_VERSION = "iclr-review-audit-rubric-v0.1"

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


def audit_claim(paper: dict[str, Any], review: dict[str, Any], claim: dict[str, Any]) -> ClaimAudit:
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

    requires_human_expert = claim_type in EXPERT_REQUIRED_TYPES or verdict == "needs_human_check"
    requires_external = claim_type in {"novelty", "theory"}
    factual_alignment = evidence_score
    severity = 2 if requires_human_expert else (1 if verdict == "possibly_contradicted" else 3)

    flags = []
    if verdict == "possibly_contradicted":
        flags.append("possibly-contradicted-by-paper")
    if verdict == "insufficient" and claim["importance"] in {"major", "medium"}:
        flags.append("unsupported-major-claim")
    if specificity <= 1:
        flags.append("vague-criticism")
    if tone <= 2:
        flags.append("unprofessional-tone")
    if actionability <= 1 and claim["importance"] not in {"tone-only", "question"}:
        flags.append("missing-actionable-suggestions")
    if requires_human_expert:
        flags.append("requires-human-expert-check")

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
        issue_flags=flags,
        evidence=evidence,
    )


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


def audit_review(paper: dict[str, Any], review: dict[str, Any]) -> ReviewAudit:
    extracted = extract_claims(review)
    claims = [audit_claim(paper, review, claim) for claim in extracted]
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
        model_version=MODEL_VERSION,
        rubric_version=RUBRIC_VERSION,
        claim_extraction_version=CLAIM_EXTRACTION_VERSION,
        retrieval_version=RETRIEVAL_VERSION,
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


def audit_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    audits = []
    for paper in dataset.get("papers", []):
        for review in paper.get("reviews", []):
            audits.append(audit_review(paper, review).to_dict())
    return {
        "schema_version": "0.1",
        "dataset": dataset.get("dataset", "unknown"),
        "paper_count": len(dataset.get("papers", [])),
        "review_count": sum(len(paper.get("reviews", [])) for paper in dataset.get("papers", [])),
        "audit_count": len(audits),
        "model_version": MODEL_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "claim_extraction_version": CLAIM_EXTRACTION_VERSION,
        "retrieval_version": RETRIEVAL_VERSION,
        "audits": audits,
    }
