from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Evidence:
    evidence_id: str
    claim_id: str
    source_type: str
    section: str
    page: int | None
    text: str
    verdict: str
    confidence: str
    score: float
    raw_score: float | None = None
    matched_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimAudit:
    claim_id: str
    review_id: str
    claim_text: str
    claim_type: str
    importance: str
    source_field: str
    source_sentence_index: int | None
    source_sentence: str
    extraction_reason: str
    extraction_version: str
    auditability: int
    specificity: int
    evidence_support: int | None
    factual_alignment: int | None
    severity_calibration: int | None
    actionability: int
    tone: int
    verdict: str
    audit_confidence: str
    requires_external_knowledge: bool
    requires_human_expert: bool
    review_point_type: str = ""
    stance: str = ""
    support_score: int | None = None
    answer_coverage_score: int | None = None
    question_value_score: int | None = None
    second_opinion_take: str = ""
    quoted_manuscript_evidence: str = ""
    reasoning_summary: str = ""
    rebuttal_guidance: dict[str, Any] = field(default_factory=dict)
    professionalism_score: int | None = None
    specificity_score: int | None = None
    helpfulness_score: int | None = None
    fairness_score: int | None = None
    judge_version: str = ""
    judge_model: str = ""
    judge_rationale: str = ""
    issue_flags: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence"] = [item.to_dict() for item in self.evidence]
        return result


@dataclass
class ReviewAudit:
    audit_id: str
    review_id: str
    paper_id: str
    paper_title: str
    decision: str
    rating_raw: str
    rating_normalized: float | None
    reviewer_confidence_raw: str
    reviewer_confidence_normalized: float | None
    model_version: str
    rubric_version: str
    claim_extraction_version: str
    retrieval_version: str
    judge_version: str
    judge_model: str
    rqs_score: int
    audit_confidence: str
    issue_flags: list[str]
    summary: str
    dimensions: dict[str, float]
    claims: list[ClaimAudit]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["claims"] = [claim.to_dict() for claim in self.claims]
        return result
