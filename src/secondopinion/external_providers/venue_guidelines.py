from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..text import clean_text


@dataclass(frozen=True)
class VenueGuideline:
    venue: str
    section: str
    claim_types: tuple[str, ...]
    text: str
    url: str = ""


GUIDELINES: tuple[VenueGuideline, ...] = (
    VenueGuideline(
        venue="ICLR",
        section="ICLR review criteria: empirical validation",
        claim_types=("baseline", "experiment", "ablation", "methodology"),
        text=(
            "ICLR-style reviews should evaluate whether empirical claims are supported by appropriate experiments, "
            "comparisons, ablations, and analysis. For baseline or ablation critiques, the reviewer point is more "
            "grounded when it identifies missing comparisons that are standard for the task or necessary for the "
            "paper's central claim."
        ),
    ),
    VenueGuideline(
        venue="ICLR",
        section="ICLR review criteria: novelty and significance",
        claim_types=("novelty", "theory", "general"),
        text=(
            "ICLR-style reviews should assess originality, significance, and relationship to prior work. Novelty "
            "critiques usually require field context, related papers, or benchmark conventions beyond the submitted "
            "manuscript alone."
        ),
    ),
    VenueGuideline(
        venue="ICLR",
        section="ICLR review criteria: clarity and reproducibility",
        claim_types=("clarity", "writing", "methodology"),
        text=(
            "ICLR-style reviews should consider whether the submission is clear, reproducible, and specific enough "
            "for readers to understand the method, experimental setup, and limitations."
        ),
    ),
    VenueGuideline(
        venue="NeurIPS",
        section="NeurIPS review criteria: empirical support",
        claim_types=("baseline", "experiment", "ablation", "methodology"),
        text=(
            "NeurIPS-style reviews should evaluate technical soundness, empirical validation, reproducibility, and "
            "whether comparisons are sufficient for the claims being made."
        ),
    ),
    VenueGuideline(
        venue="NeurIPS",
        section="NeurIPS review criteria: broader context",
        claim_types=("novelty", "theory", "ethics", "general"),
        text=(
            "NeurIPS-style reviews should consider novelty, relevance, limitations, and broader context. Claims "
            "about field standards or significance often need external literature or accepted community practice."
        ),
    ),
)


def collect_venue_guidelines(
    *,
    venue: Any,
    year: Any,
    claim_types: set[str],
    limit: int = 3,
) -> list[dict[str, Any]]:
    venue_text = clean_text(venue).upper()
    if not venue_text:
        return []
    records = []
    for guideline in GUIDELINES:
        if guideline.venue.upper() != venue_text:
            continue
        if claim_types and not claim_types.intersection(guideline.claim_types):
            continue
        records.append(
            {
                "source_type": "venue_guideline",
                "section": guideline.section,
                "page": None,
                "text": guideline.text,
                "metadata": {
                    "provider": "local_venue_guidelines",
                    "venue": guideline.venue,
                    "year": year,
                    "claim_types": list(guideline.claim_types),
                    "stable_id": f"venue-guideline:{guideline.venue.lower()}:{guideline.section.lower().replace(' ', '-')}",
                    "url": guideline.url,
                    "available_at_review_time": True,
                },
            }
        )
        if len(records) >= limit:
            break
    return records
