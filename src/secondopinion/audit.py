from __future__ import annotations

import hashlib
import statistics
from typing import Any

from .models import ClaimAudit, Evidence, ReviewAudit
from .text import clean_text, split_review_sentences, tokens


MODEL_VERSION = "rule-baseline-v0.1"
RUBRIC_VERSION = "iclr-review-audit-rubric-v0.1"
RETRIEVAL_VERSION = "lexical-evidence-v0.1"

NEGATION_WORDS = ("no ", "not ", "lack", "lacks", "lacking", "missing", "insufficient", "without", "fails to")
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
TONE_PROBLEM_WORDS = (
    "nonsense",
    "ridiculous",
    "lazy",
    "obviously bad",
    "do not understand",
    "no idea",
    "terrible",
    "worthless",
)

CLAIM_TYPES = {
    "experiment": ("experiment", "evaluation", "empirical", "result", "metric"),
    "baseline": ("baseline", "compare", "comparison", "sota", "state-of-the-art"),
    "ablation": ("ablation", "component removal", "component study"),
    "methodology": ("method", "approach", "algorithm", "architecture", "assumption"),
    "theory": ("theorem", "proof", "lemma", "theory"),
    "novelty": ("novel", "novelty", "original", "incremental"),
    "clarity": ("clarity", "unclear", "notation", "explain", "presentation"),
    "writing": ("writing", "grammar", "typo", "readability"),
    "ethics": ("ethic", "privacy", "harm", "safety"),
    "tone": TONE_PROBLEM_WORDS,
}

EXPERT_REQUIRED_TYPES = {"novelty", "theory"}


def _id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def classify_claim_type(text: str) -> str:
    lowered = text.lower()
    for claim_type, keywords in CLAIM_TYPES.items():
        if any(keyword in lowered for keyword in keywords):
            return claim_type
    return "general"


def infer_importance(text: str, claim_type: str) -> str:
    lowered = text.lower()
    if claim_type == "tone":
        return "tone-only"
    if any(word in lowered for word in ("fatal", "major", "central", "main", "critical", "core")):
        return "major"
    if any(word in lowered for word in ("minor", "small", "typo", "detail")):
        return "minor"
    if lowered.endswith("?"):
        return "question"
    if claim_type in {"baseline", "ablation", "methodology", "experiment", "theory", "novelty"}:
        return "major"
    return "medium"


def extract_claims(review: dict[str, Any], max_claims: int = 8) -> list[dict[str, str]]:
    source = review.get("weaknesses") or review.get("review_text") or ""
    sentences = split_review_sentences(source)
    selected: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(word in lowered for word in NEGATION_WORDS + SPECIFICITY_WORDS + TONE_PROBLEM_WORDS):
            selected.append(sentence)
        if len(selected) >= max_claims:
            break
    if not selected:
        selected = sentences[: min(3, len(sentences))]

    claims = []
    seen = set()
    for text in selected:
        normalized = " ".join(text.lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        claim_type = classify_claim_type(text)
        claims.append(
            {
                "claim_text": clean_text(text),
                "claim_type": claim_type,
                "importance": infer_importance(text, claim_type),
            }
        )
    return claims


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


def build_evidence_sources(paper: dict[str, Any]) -> list[dict[str, Any]]:
    sources = []
    if paper.get("title"):
        sources.append({"source_type": "paper", "section": "title", "page": None, "text": paper["title"]})
    if paper.get("abstract"):
        sources.append({"source_type": "paper", "section": "abstract", "page": None, "text": paper["abstract"]})
    for idx, rebuttal in enumerate(paper.get("rebuttals", []), start=1):
        if rebuttal.get("text"):
            sources.append(
                {
                    "source_type": "rebuttal",
                    "section": f"author_response_{idx}",
                    "page": None,
                    "text": rebuttal["text"],
                }
            )
    for idx, section in enumerate(paper.get("paper_sections", []), start=1):
        if section.get("text"):
            sources.append(
                {
                    "source_type": section.get("source_type", "paper"),
                    "section": section.get("section") or f"section_{idx}",
                    "page": section.get("page"),
                    "text": section["text"],
                }
            )
    return sources


def retrieve_evidence(claim_id: str, claim_text: str, paper: dict[str, Any], top_k: int = 3) -> list[Evidence]:
    claim_tokens = tokens(claim_text)
    scored = []
    for source in build_evidence_sources(paper):
        source_tokens = tokens(source.get("text", ""))
        if not source_tokens:
            continue
        overlap = len(claim_tokens & source_tokens)
        score = overlap / max(len(claim_tokens), 1)
        if overlap:
            scored.append((score, source))
    scored.sort(key=lambda item: item[0], reverse=True)

    evidence_items: list[Evidence] = []
    for idx, (score, source) in enumerate(scored[:top_k], start=1):
        verdict = "partial" if score >= 0.16 else "insufficient"
        confidence = "medium" if score >= 0.22 else "low"
        evidence_items.append(
            Evidence(
                evidence_id=f"{claim_id}_ev{idx}",
                claim_id=claim_id,
                source_type=source["source_type"],
                section=source["section"],
                page=source.get("page"),
                text=clean_text(source["text"])[:700],
                verdict=verdict,
                confidence=confidence,
                score=round(score, 3),
            )
        )
    return evidence_items


def classify_evidence_verdict(claim_text: str, evidence: list[Evidence], claim_type: str) -> tuple[str, str, int | None]:
    if claim_type in EXPERT_REQUIRED_TYPES:
        return "expert_required", "low", None
    if not evidence:
        return "insufficient", "low", 1

    best = evidence[0]
    lowered_claim = claim_text.lower()
    absence_claim = any(word in lowered_claim for word in ABSENCE_CLAIM_WORDS)
    if absence_claim and best.section != "title" and best.score >= 0.2:
        for item in evidence:
            item.verdict = "contradict"
            item.confidence = "medium" if item.score < 0.28 else "high"
        return "contradicted_by_paper", evidence[0].confidence, 0
    if best.score >= 0.28:
        for item in evidence:
            item.verdict = "support"
        return "supported_by_available_evidence", "medium", 3
    if best.score >= 0.16:
        return "partially_supported", "low", 2
    return "insufficient", "low", 1


def audit_claim(paper: dict[str, Any], review: dict[str, Any], claim: dict[str, str]) -> ClaimAudit:
    review_id = review.get("review_id", "review")
    claim_text = claim["claim_text"]
    claim_id = _id("claim", review_id, claim_text)
    claim_type = claim["claim_type"]
    auditability = score_auditability(claim_text, claim_type)
    specificity = score_specificity(claim_text)
    actionability = score_actionability(claim_text)
    tone = score_tone(claim_text)
    evidence = retrieve_evidence(claim_id, claim_text, paper)
    verdict, confidence, evidence_score = classify_evidence_verdict(claim_text, evidence, claim_type)

    requires_human_expert = claim_type in EXPERT_REQUIRED_TYPES or verdict == "expert_required"
    requires_external = claim_type in {"novelty", "theory"}
    factual_alignment = evidence_score
    severity = 2 if requires_human_expert else (1 if verdict == "contradicted_by_paper" else 3)

    flags = []
    if verdict == "contradicted_by_paper":
        flags.append("contradicted-by-paper")
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
        1 for claim in claims if claim.verdict in {"contradicted_by_paper", "insufficient"} and claim.importance == "major"
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
    if "contradicted-by-paper" in flags:
        return "At least one major criticism appears contradicted by available paper evidence; human verification is recommended."
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
        "retrieval_version": RETRIEVAL_VERSION,
        "audits": audits,
    }
