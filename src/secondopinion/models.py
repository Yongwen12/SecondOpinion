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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimAudit:
    claim_id: str
    review_id: str
    claim_text: str
    claim_type: str
    importance: str
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
    model_version: str
    rubric_version: str
    retrieval_version: str
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

