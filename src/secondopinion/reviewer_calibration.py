from __future__ import annotations

import json
import math
import random
import re
from collections import Counter
import hashlib
from pathlib import Path
from typing import Any

from .concern_survival import concern_tokens, overlap_score, split_meta_review_segments
from .data_inventory import classify_reply
from .model_config import DEFAULT_CHEAP_MODEL
from .normalize import get_replies
from .snapshot import load_snapshot_notes, read_json
from .text import clean_text, text_from_content


REVIEWER_CALIBRATION_VERSION = "reviewer-calibration-v0.1"
REBUTTAL_RESOLUTION_LABEL_VERSION = "rebuttal-resolution-label-v0.1"
INTER_REVIEWER_CONSENSUS_LABEL_VERSION = "inter-reviewer-consensus-label-v0.1"
DEFAULT_REBUTTAL_RESOLUTION_CALIBRATION_MODEL = DEFAULT_CHEAP_MODEL
DEFAULT_CONSENSUS_CALIBRATION_MODEL = DEFAULT_CHEAP_MODEL

CONSENSUS_STRONG_THRESHOLD = 0.34
CONSENSUS_PARTIAL_THRESHOLD = 0.2
REBUTTAL_ADDRESSED_THRESHOLD = 0.2
REBUTTAL_RESOLVED_THRESHOLD = 0.3
DISCUSSION_FOLLOWUP_THRESHOLD = 0.2

RESOLUTION_CUES = {
    "address",
    "addressed",
    "added",
    "clarified",
    "clarify",
    "fixed",
    "include",
    "included",
    "now",
    "revised",
    "thank",
    "thanks",
    "we",
}

REBUTTAL_RESPONSE_LABELS = (
    "not_addressed",
    "generic_or_unclear",
    "specifically_addressed",
    "likely_resolved",
)
REBUTTAL_EFFECT_LABELS = (
    "resolved_or_weakened",
    "partially_addresses",
    "does_not_address",
    "unclear",
)
RESPONSE_SPECIFICITY_LABELS = ("specific", "generic", "none", "unclear")
CONFIDENCE_LABELS = ("high", "medium", "low")
TRAINING_USE_LABELS = ("include", "exclude")
CONSENSUS_RESPONSE_LABELS = ("same_concern", "related_but_different", "not_same_concern", "unsure")
CONSENSUS_RELATION_LABELS = ("supports", "overlaps", "contradicts", "unclear")


def calibrate_reviewer_reliability(
    concern_report: dict[str, Any],
    *,
    snapshot_dir: str | Path | None = None,
    rebuttal_labels: list[dict[str, Any]] | None = None,
    consensus_labels: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    paper_aux = load_paper_auxiliary(snapshot_dir) if snapshot_dir else {}
    rebuttal_labels_by_task = index_rebuttal_resolution_labels(rebuttal_labels or [])
    consensus_labels_by_task = index_consensus_labels(consensus_labels or [])
    papers = [
        calibrate_paper(
            paper,
            paper_aux.get(paper.get("paper_id", ""), {}),
            rebuttal_labels_by_task=rebuttal_labels_by_task,
            consensus_labels_by_task=consensus_labels_by_task,
        )
        for paper in concern_report.get("papers", [])
    ]
    return build_reviewer_calibration_report(
        papers,
        source={
            "survival_version": concern_report.get("survival_version", ""),
            "snapshot": concern_report.get("snapshot", {}),
            "snapshot_dir": str(snapshot_dir or ""),
            "llm_rebuttal_label_count": len(rebuttal_labels_by_task),
            "llm_consensus_label_count": len(consensus_labels_by_task),
        },
    )


def calibrate_paper(
    paper: dict[str, Any],
    aux: dict[str, Any],
    *,
    rebuttal_labels_by_task: dict[str, dict[str, Any]] | None = None,
    consensus_labels_by_task: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rebuttal_labels_by_task = rebuttal_labels_by_task or {}
    consensus_labels_by_task = consensus_labels_by_task or {}
    reviews = [review for review in paper.get("reviews", []) if review.get("status", "ok") == "ok"]
    all_claims = [
        {**claim, "_review_id": review.get("review_id", ""), "_paper_id": paper.get("paper_id", "")}
        for review in reviews
        for claim in review.get("claims", [])
    ]
    author_segments = split_meta_review_segments("\n\n".join(aux.get("author_responses", [])))
    discussion_segments = split_meta_review_segments("\n\n".join(aux.get("reviewer_or_ac_discussions", [])))

    calibrated_reviews = []
    for review in reviews:
        calibrated_claims = []
        for claim_index, claim in enumerate(review.get("claims", [])):
            task_id = f"{paper.get('paper_id', '')}:{review.get('review_id', '')}:{claim_index}"
            calibrated_claims.append(
                calibrate_claim(
                    {**claim, "_paper_id": paper.get("paper_id", ""), "_task_id": task_id},
                    review_id=review.get("review_id", ""),
                    all_claims=all_claims,
                    author_segments=author_segments,
                    discussion_segments=discussion_segments,
                    llm_rebuttal_label=rebuttal_labels_by_task.get(task_id),
                    llm_consensus_label=consensus_labels_by_task.get(task_id),
                )
            )
        calibrated_reviews.append(
            calibrate_review(
                review,
                calibrated_claims,
                paper_id=paper.get("paper_id", ""),
                reviewer_identity=aux.get("reviewer_identities", {}).get(review.get("review_id", ""), {}),
            )
        )

    return {
        "paper_id": paper.get("paper_id", ""),
        "forum_id": paper.get("forum_id", paper.get("paper_id", "")),
        "title": paper.get("title", ""),
        "decision": paper.get("decision", ""),
        "decision_label": paper.get("decision_label", ""),
        "author_response_count": len(aux.get("author_responses", [])),
        "discussion_count": len(aux.get("reviewer_or_ac_discussions", [])),
        "review_count": len(calibrated_reviews),
        "claim_count": sum(review.get("claim_count", 0) for review in calibrated_reviews),
        "reviews": calibrated_reviews,
    }


def calibrate_claim(
    claim: dict[str, Any],
    *,
    review_id: str,
    all_claims: list[dict[str, Any]],
    author_segments: list[str],
    discussion_segments: list[str],
    llm_rebuttal_label: dict[str, Any] | None = None,
    llm_consensus_label: dict[str, Any] | None = None,
) -> dict[str, Any]:
    public_claim = {key: value for key, value in claim.items() if not key.startswith("_")}
    consensus = best_consensus_match(claim, review_id=review_id, all_claims=all_claims)
    rebuttal = best_text_match(claim, author_segments)
    discussion = best_text_match(claim, discussion_segments)
    rebuttal_resolution_payload = rebuttal_resolution(claim, rebuttal)
    if llm_rebuttal_label:
        rebuttal_resolution_payload["llm_calibration"] = llm_rebuttal_calibration_payload(llm_rebuttal_label)
    consensus_payload = {
        "label": consensus_label(consensus["score"]),
        "score": round(consensus["score"], 4),
        "matched_review_id": consensus["matched_review_id"],
        "matched_claim_text": consensus["matched_claim_text"],
        "matched_terms": consensus["matched_terms"],
    }
    if llm_consensus_label:
        consensus_payload["llm_calibration"] = llm_consensus_calibration_payload(llm_consensus_label)
    calibrated_claim = {
        **public_claim,
        "grounded": bool(clean_text(claim.get("source_sentence", ""))),
        "specificity_score": specificity_score(claim),
        "consensus": consensus_payload,
        "rebuttal_resolution": rebuttal_resolution_payload,
        "discussion_followup": {
            "label": "followed_up" if discussion["score"] >= DISCUSSION_FOLLOWUP_THRESHOLD else "not_found",
            "score": round(discussion["score"], 4),
            "matched_segment": discussion["segment"],
            "matched_terms": discussion["matched_terms"],
        },
        "meta_review_uptake": {
            "label": claim.get("survival_label", ""),
            "score": claim.get("survival_score", 0.0),
            "matched_segment": claim.get("matched_meta_segment", ""),
        },
    }
    calibrated_claim["lifecycle_robustness"] = claim_lifecycle_robustness(calibrated_claim)
    return calibrated_claim


def best_consensus_match(claim: dict[str, Any], *, review_id: str, all_claims: list[dict[str, Any]]) -> dict[str, Any]:
    query_tokens = concern_tokens(claim_text(claim))
    best = {
        "score": 0.0,
        "matched_review_id": "",
        "matched_claim_text": "",
        "matched_terms": [],
    }
    if not query_tokens:
        return best
    for other in all_claims:
        other_review_id = other.get("_review_id", other.get("review_id", ""))
        if other_review_id == review_id:
            continue
        score, matched_terms = overlap_score(query_tokens, concern_tokens(claim_text(other)))
        type_bonus = 0.05 if claim.get("claim_type") and claim.get("claim_type") == other.get("claim_type") else 0.0
        score = min(1.0, score + type_bonus)
        if score > best["score"]:
            best = {
                "score": score,
                "matched_review_id": other_review_id,
                "matched_claim_text": other.get("claim_text", ""),
                "matched_terms": sorted(matched_terms),
            }
    return best


def best_text_match(claim: dict[str, Any], segments: list[str]) -> dict[str, Any]:
    query_tokens = concern_tokens(claim_text(claim))
    best = {"score": 0.0, "segment": "", "matched_terms": []}
    if not query_tokens:
        return best
    for segment in segments:
        score, matched_terms = overlap_score(query_tokens, concern_tokens(segment))
        if score > best["score"]:
            best = {"score": score, "segment": segment, "matched_terms": sorted(matched_terms)}
    return best


def rebuttal_resolution(claim: dict[str, Any], match: dict[str, Any]) -> dict[str, Any]:
    score = match["score"]
    segment = match["segment"]
    if score < REBUTTAL_ADDRESSED_THRESHOLD:
        label = "not_addressed"
    elif score >= REBUTTAL_RESOLVED_THRESHOLD and has_resolution_cue(segment):
        label = "likely_resolved_or_answered"
    else:
        label = "addressed_unclear_resolution"
    return {
        "label": label,
        "score": round(score, 4),
        "matched_segment": segment,
        "matched_terms": match["matched_terms"],
        "has_resolution_cue": has_resolution_cue(segment),
    }


def claim_lifecycle_robustness(claim: dict[str, Any]) -> dict[str, Any]:
    signal_scores = {
        "grounding": 1.0 if claim.get("grounded") else 0.0,
        "specificity": float(claim.get("specificity_score", 0.0) or 0.0),
        "consensus": lifecycle_consensus_score(claim),
        "rebuttal_robustness": lifecycle_rebuttal_score(claim),
        "discussion_followup": lifecycle_discussion_score(claim),
        "meta_review_uptake": lifecycle_meta_review_score(claim),
    }
    score = round(
        max(
            0.0,
            min(
                1.0,
                0.15 * signal_scores["grounding"]
                + 0.15 * signal_scores["specificity"]
                + 0.18 * signal_scores["consensus"]
                + 0.25 * signal_scores["rebuttal_robustness"]
                + 0.07 * signal_scores["discussion_followup"]
                + 0.20 * signal_scores["meta_review_uptake"],
            ),
        ),
        4,
    )
    return {
        "score": score,
        "label": lifecycle_robustness_label(score),
        "signal_scores": {key: round(value, 4) for key, value in signal_scores.items()},
        "supporting_factors": lifecycle_supporting_factors(claim),
        "weakening_factors": lifecycle_weakening_factors(claim),
        "source": lifecycle_robustness_source(claim),
    }


def lifecycle_robustness_label(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def lifecycle_consensus_score(claim: dict[str, Any]) -> float:
    llm_label = llm_consensus_label(claim)
    if llm_label:
        return {
            "same_concern": 1.0,
            "related_but_different": 0.55,
            "not_same_concern": 0.0,
            "unsure": 0.25,
        }.get(llm_label, 0.25)
    proxy_label = claim.get("consensus", {}).get("label", "")
    return {"strong": 1.0, "partial": 0.55, "none": 0.0}.get(proxy_label, 0.0)


def lifecycle_rebuttal_score(claim: dict[str, Any]) -> float:
    response_label = llm_rebuttal_label(claim)
    effect_label = llm_rebuttal_effect(claim)
    if response_label or effect_label:
        if effect_label == "resolved_or_weakened" or response_label == "likely_resolved":
            return 0.0
        if response_label == "specifically_addressed" or effect_label == "partially_addresses":
            return 0.55
        if response_label == "generic_or_unclear" or effect_label == "unclear":
            return 0.75 if response_label == "generic_or_unclear" else 0.45
        if response_label == "not_addressed" or effect_label == "does_not_address":
            return 0.85
        return 0.45
    proxy_label = claim.get("rebuttal_resolution", {}).get("label", "")
    if proxy_label == "likely_resolved_or_answered":
        return 0.15
    if proxy_label == "addressed_unclear_resolution":
        return 0.55
    if proxy_label == "not_addressed":
        return 0.70
    return 0.45


def lifecycle_discussion_score(claim: dict[str, Any]) -> float:
    return 0.70 if claim.get("discussion_followup", {}).get("label") == "followed_up" else 0.0


def lifecycle_meta_review_score(claim: dict[str, Any]) -> float:
    return {
        "survived": 1.0,
        "partial": 0.60,
        "not_found": 0.0,
    }.get(claim.get("meta_review_uptake", {}).get("label", ""), 0.0)


def lifecycle_supporting_factors(claim: dict[str, Any]) -> list[str]:
    factors = []
    if claim.get("grounded"):
        factors.append("grounded_in_original_review")
    if lifecycle_consensus_score(claim) >= 0.55:
        factors.append("supported_or_overlapped_by_other_reviewers")
    if lifecycle_rebuttal_score(claim) >= 0.70:
        factors.append("not_resolved_by_author_response")
    if claim.get("discussion_followup", {}).get("label") == "followed_up":
        factors.append("followed_up_after_rebuttal")
    if lifecycle_meta_review_score(claim) >= 0.60:
        factors.append("taken_up_in_meta_review")
    return factors


def lifecycle_weakening_factors(claim: dict[str, Any]) -> list[str]:
    factors = []
    if not claim.get("grounded"):
        factors.append("not_grounded_in_original_review")
    if lifecycle_consensus_score(claim) == 0.0:
        factors.append("no_inter_reviewer_support_found")
    if lifecycle_rebuttal_score(claim) <= 0.15:
        factors.append("author_response_likely_resolved_or_weakened_claim")
    if lifecycle_meta_review_score(claim) == 0.0:
        factors.append("not_found_in_meta_review")
    return factors


def lifecycle_robustness_source(claim: dict[str, Any]) -> str:
    if llm_consensus_label(claim) or llm_rebuttal_label(claim) or llm_rebuttal_effect(claim):
        return "llm_calibrated_when_available"
    return "deterministic_proxy"


def calibrate_review(
    review: dict[str, Any],
    claims: list[dict[str, Any]],
    *,
    paper_id: str = "",
    reviewer_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reviewer_identity = reviewer_identity or {}
    claim_count = len(claims)
    grounded_rate = rate_value(claim.get("grounded") for claim in claims)
    specificity = mean_value(claim.get("specificity_score", 0.0) for claim in claims)
    consensus_rate = rate_value(claim["consensus"]["label"] in {"strong", "partial"} for claim in claims)
    llm_consensus_labeled_claim_count = sum(1 for claim in claims if claim.get("consensus", {}).get("llm_calibration"))
    llm_consensus_same_rate = rate_value(
        llm_consensus_label(claim) == "same_concern"
        for claim in claims
        if claim.get("consensus", {}).get("llm_calibration")
    )
    llm_consensus_related_or_same_rate = rate_value(
        llm_consensus_label(claim) in {"same_concern", "related_but_different"}
        for claim in claims
        if claim.get("consensus", {}).get("llm_calibration")
    )
    calibrated_consensus_rate = llm_consensus_related_or_same_rate if llm_consensus_labeled_claim_count else consensus_rate
    meta_uptake_rate = rate_value(claim["meta_review_uptake"]["label"] in {"survived", "partial"} for claim in claims)
    rebuttal_addressed_rate = rate_value(
        claim["rebuttal_resolution"]["label"] in {"addressed_unclear_resolution", "likely_resolved_or_answered"}
        for claim in claims
    )
    rebuttal_resolved_rate = rate_value(
        claim["rebuttal_resolution"]["label"] == "likely_resolved_or_answered"
        for claim in claims
    )
    llm_rebuttal_labeled_claim_count = sum(1 for claim in claims if claim.get("rebuttal_resolution", {}).get("llm_calibration"))
    llm_rebuttal_addressed_rate = rate_value(
        llm_rebuttal_label(claim) in {"specifically_addressed", "likely_resolved"}
        for claim in claims
        if claim.get("rebuttal_resolution", {}).get("llm_calibration")
    )
    llm_rebuttal_resolved_rate = rate_value(
        llm_rebuttal_effect(claim) == "resolved_or_weakened"
        for claim in claims
        if claim.get("rebuttal_resolution", {}).get("llm_calibration")
    )
    calibrated_rebuttal_resolved_rate = llm_rebuttal_resolved_rate if llm_rebuttal_labeled_claim_count else rebuttal_resolved_rate
    discussion_followup_rate = rate_value(
        claim["discussion_followup"]["label"] == "followed_up"
        for claim in claims
    )
    mean_lifecycle_robustness_score = mean_value(
        claim.get("lifecycle_robustness", {}).get("score", 0.0)
        for claim in claims
    )
    lifecycle_labels = Counter(claim.get("lifecycle_robustness", {}).get("label", "") for claim in claims)
    severity = review_concern_severity(claims)
    expected_rating = expected_rating_from_severity(severity)
    actual_rating = review.get("rating_normalized")
    rating_gap = None if actual_rating is None else round(float(actual_rating) - expected_rating, 3)
    reviewer_confidence = review.get("confidence_normalized")
    reliability_score = review_reliability_score(
        grounded_rate=grounded_rate,
        specificity=specificity,
        consensus_rate=consensus_rate,
        meta_uptake_rate=meta_uptake_rate,
        rebuttal_resolved_rate=rebuttal_resolved_rate,
        rating_gap=rating_gap,
        reviewer_confidence=reviewer_confidence,
    )
    llm_calibrated_reliability_score = review_reliability_score(
        grounded_rate=grounded_rate,
        specificity=specificity,
        consensus_rate=calibrated_consensus_rate,
        meta_uptake_rate=meta_uptake_rate,
        rebuttal_resolved_rate=calibrated_rebuttal_resolved_rate,
        rating_gap=rating_gap,
        reviewer_confidence=reviewer_confidence,
    ) if (llm_rebuttal_labeled_claim_count or llm_consensus_labeled_claim_count) else reliability_score
    return {
        "paper_id": paper_id,
        "review_id": review.get("review_id", ""),
        "reviewer_identity_hash": reviewer_identity.get("reviewer_identity_hash", ""),
        "reviewer_signature_role": reviewer_identity.get("signer_role", ""),
        "rating_raw": review.get("rating_raw", ""),
        "rating_normalized": actual_rating,
        "confidence_raw": review.get("confidence_raw", ""),
        "confidence_normalized": reviewer_confidence,
        "claim_count": claim_count,
        "grounded_claim_rate": grounded_rate,
        "claim_specificity_score": specificity,
        "inter_review_consensus_rate": consensus_rate,
        "llm_consensus_labeled_claim_count": llm_consensus_labeled_claim_count,
        "llm_consensus_label_coverage": safe_rate(llm_consensus_labeled_claim_count, claim_count),
        "llm_consensus_same_rate": llm_consensus_same_rate,
        "llm_consensus_related_or_same_rate": llm_consensus_related_or_same_rate,
        "meta_review_uptake_rate": meta_uptake_rate,
        "rebuttal_addressed_rate": rebuttal_addressed_rate,
        "rebuttal_resolved_rate": rebuttal_resolved_rate,
        "llm_rebuttal_labeled_claim_count": llm_rebuttal_labeled_claim_count,
        "llm_rebuttal_label_coverage": safe_rate(llm_rebuttal_labeled_claim_count, claim_count),
        "llm_rebuttal_addressed_rate": llm_rebuttal_addressed_rate,
        "llm_rebuttal_resolved_rate": llm_rebuttal_resolved_rate,
        "discussion_followup_rate": discussion_followup_rate,
        "mean_lifecycle_robustness_score": mean_lifecycle_robustness_score,
        "high_robustness_claim_rate": rate_value(
            claim.get("lifecycle_robustness", {}).get("label") == "high"
            for claim in claims
        ),
        "medium_or_high_robustness_claim_rate": rate_value(
            claim.get("lifecycle_robustness", {}).get("label") in {"high", "medium"}
            for claim in claims
        ),
        "lifecycle_robustness_counts": dict(lifecycle_labels),
        "concern_severity_score": severity,
        "expected_rating": expected_rating,
        "rating_gap": rating_gap,
        "rating_calibration_label": rating_calibration_label(rating_gap),
        "confidence_calibration_label": confidence_calibration_label(reviewer_confidence, reliability_score),
        "review_reliability_score": reliability_score,
        "llm_calibrated_review_reliability_score": llm_calibrated_reliability_score,
        "llm_calibrated_reliability_delta": round(llm_calibrated_reliability_score - reliability_score, 4),
        "reviewer_style_label": reviewer_style_label(rating_gap, reviewer_confidence, reliability_score),
        "claims": claims,
    }


def build_reviewer_calibration_report(papers: list[dict[str, Any]], *, source: dict[str, Any]) -> dict[str, Any]:
    reviews = [review for paper in papers for review in paper.get("reviews", [])]
    claims = [claim for review in reviews for claim in review.get("claims", [])]
    summary = {
        "paper_count": len(papers),
        "review_count": len(reviews),
        "claim_count": len(claims),
        "paper_with_author_response_count": sum(1 for paper in papers if paper.get("author_response_count", 0) > 0),
        "paper_with_discussion_count": sum(1 for paper in papers if paper.get("discussion_count", 0) > 0),
        "mean_review_reliability_score": mean_value(review.get("review_reliability_score", 0.0) for review in reviews),
        "mean_llm_calibrated_review_reliability_score": mean_value(
            review.get("llm_calibrated_review_reliability_score", review.get("review_reliability_score", 0.0))
            for review in reviews
        ),
        "mean_llm_calibrated_reliability_delta": mean_value(
            review.get("llm_calibrated_reliability_delta", 0.0)
            for review in reviews
        ),
        "mean_inter_review_consensus_rate": mean_value(review.get("inter_review_consensus_rate", 0.0) for review in reviews),
        "mean_llm_consensus_label_coverage": mean_value(review.get("llm_consensus_label_coverage", 0.0) for review in reviews),
        "mean_llm_consensus_same_rate": mean_value(review.get("llm_consensus_same_rate", 0.0) for review in reviews),
        "mean_llm_consensus_related_or_same_rate": mean_value(review.get("llm_consensus_related_or_same_rate", 0.0) for review in reviews),
        "mean_rebuttal_addressed_rate": mean_value(review.get("rebuttal_addressed_rate", 0.0) for review in reviews),
        "mean_llm_rebuttal_label_coverage": mean_value(review.get("llm_rebuttal_label_coverage", 0.0) for review in reviews),
        "mean_llm_rebuttal_addressed_rate": mean_value(review.get("llm_rebuttal_addressed_rate", 0.0) for review in reviews),
        "mean_llm_rebuttal_resolved_rate": mean_value(review.get("llm_rebuttal_resolved_rate", 0.0) for review in reviews),
        "mean_meta_review_uptake_rate": mean_value(review.get("meta_review_uptake_rate", 0.0) for review in reviews),
        "mean_claim_lifecycle_robustness_score": mean_value(
            claim.get("lifecycle_robustness", {}).get("score", 0.0)
            for claim in claims
        ),
        "mean_review_lifecycle_robustness_score": mean_value(
            review.get("mean_lifecycle_robustness_score", 0.0)
            for review in reviews
        ),
        "mean_high_robustness_claim_rate": mean_value(review.get("high_robustness_claim_rate", 0.0) for review in reviews),
        "mean_medium_or_high_robustness_claim_rate": mean_value(
            review.get("medium_or_high_robustness_claim_rate", 0.0)
            for review in reviews
        ),
        "rating_calibration_counts": dict(Counter(review.get("rating_calibration_label", "") for review in reviews)),
        "confidence_calibration_counts": dict(Counter(review.get("confidence_calibration_label", "") for review in reviews)),
        "reviewer_style_counts": dict(Counter(review.get("reviewer_style_label", "") for review in reviews)),
        "claim_lifecycle_robustness_counts": dict(
            Counter(claim.get("lifecycle_robustness", {}).get("label", "") for claim in claims)
        ),
        "claim_consensus_counts": dict(Counter(claim.get("consensus", {}).get("label", "") for claim in claims)),
        "claim_llm_consensus_response_counts": dict(
            Counter(
                claim.get("consensus", {}).get("llm_calibration", {}).get("consensus_label", "")
                for claim in claims
                if claim.get("consensus", {}).get("llm_calibration")
            )
        ),
        "claim_llm_consensus_relation_counts": dict(
            Counter(
                claim.get("consensus", {}).get("llm_calibration", {}).get("relation", "")
                for claim in claims
                if claim.get("consensus", {}).get("llm_calibration")
            )
        ),
        "claim_rebuttal_resolution_counts": dict(Counter(claim.get("rebuttal_resolution", {}).get("label", "") for claim in claims)),
        "claim_llm_rebuttal_response_counts": dict(
            Counter(
                claim.get("rebuttal_resolution", {}).get("llm_calibration", {}).get("rebuttal_response_label", "")
                for claim in claims
                if claim.get("rebuttal_resolution", {}).get("llm_calibration")
            )
        ),
        "claim_llm_rebuttal_effect_counts": dict(
            Counter(
                claim.get("rebuttal_resolution", {}).get("llm_calibration", {}).get("rebuttal_effect_on_claim", "")
                for claim in claims
                if claim.get("rebuttal_resolution", {}).get("llm_calibration")
            )
        ),
        "reviewer_identity_summary": reviewer_identity_summary(reviews),
    }
    return {
        "schema_version": "0.1",
        "calibration_version": REVIEWER_CALIBRATION_VERSION,
        "source": source,
        "summary": summary,
        "examples": {
            "high_reliability_reviews": sorted(review_examples(reviews), key=lambda item: item["review_reliability_score"], reverse=True)[:8],
            "low_reliability_reviews": sorted(review_examples(reviews), key=lambda item: item["review_reliability_score"])[:8],
            "rebuttal_resolved_claims": claim_examples(
                claim for claim in claims if claim.get("rebuttal_resolution", {}).get("label") == "likely_resolved_or_answered"
            )[:8],
            "consensus_claims": claim_examples(
                claim for claim in claims if claim.get("consensus", {}).get("label") in {"strong", "partial"}
            )[:8],
            "high_robustness_claims": claim_examples(
                claim for claim in claims if claim.get("lifecycle_robustness", {}).get("label") == "high"
            )[:8],
            "low_robustness_claims": claim_examples(
                claim for claim in claims if claim.get("lifecycle_robustness", {}).get("label") == "low"
            )[:8],
        },
        "papers": papers,
    }


def build_rebuttal_resolution_calibration_sample(
    reviewer_calibration_report: dict[str, Any],
    *,
    sample_size: int = 120,
    seed: int = 43,
) -> dict[str, Any]:
    claims = list(iter_reviewer_calibration_claims(reviewer_calibration_report))
    sampled = targeted_rebuttal_sample(claims, sample_size=sample_size, seed=seed)
    return {
        "schema_version": "0.1",
        "sample_type": "rebuttal_resolution_calibration",
        "sample_size_requested": max(0, sample_size),
        "sample_size": len(sampled),
        "seed": seed,
        "source": {
            "calibration_version": reviewer_calibration_report.get("calibration_version", ""),
            "snapshot": reviewer_calibration_report.get("source", {}).get("snapshot", {}),
        },
        "summary": {
            "candidate_count": len(claims),
            "sample_proxy_label_counts": dict(Counter(item.get("proxy_rebuttal_label", "") for item in sampled)),
            "sample_reason_counts": dict(Counter(item.get("sampling_reason", "") for item in sampled)),
        },
        "items": sampled,
    }


def build_consensus_calibration_sample(
    reviewer_calibration_report: dict[str, Any],
    *,
    sample_size: int = 120,
    seed: int = 59,
) -> dict[str, Any]:
    claims = list(iter_consensus_calibration_claims(reviewer_calibration_report))
    sampled = targeted_consensus_sample(claims, sample_size=sample_size, seed=seed)
    return {
        "schema_version": "0.1",
        "sample_type": "inter_reviewer_consensus_calibration",
        "sample_size_requested": max(0, sample_size),
        "sample_size": len(sampled),
        "seed": seed,
        "source": {
            "calibration_version": reviewer_calibration_report.get("calibration_version", ""),
            "snapshot": reviewer_calibration_report.get("source", {}).get("snapshot", {}),
        },
        "summary": {
            "candidate_count": len(claims),
            "sample_proxy_label_counts": dict(Counter(item.get("proxy_consensus_label", "") for item in sampled)),
            "sample_reason_counts": dict(Counter(item.get("sampling_reason", "") for item in sampled)),
        },
        "items": sampled,
    }


def iter_consensus_calibration_claims(report: dict[str, Any]):
    for paper in report.get("papers", []):
        for review in paper.get("reviews", []):
            for index, claim in enumerate(review.get("claims", [])):
                consensus = claim.get("consensus", {})
                yield {
                    "task_id": f"{paper.get('paper_id', '')}:{review.get('review_id', '')}:{index}",
                    "paper_id": paper.get("paper_id", ""),
                    "review_id": review.get("review_id", ""),
                    "claim_index": index,
                    "title": paper.get("title", ""),
                    "decision_label": paper.get("decision_label", ""),
                    "claim_text": claim.get("claim_text", ""),
                    "claim_type": claim.get("claim_type", ""),
                    "importance": claim.get("importance", ""),
                    "source_sentence": claim.get("source_sentence", ""),
                    "proxy_consensus_label": consensus.get("label", ""),
                    "proxy_consensus_score": consensus.get("score", 0.0),
                    "matched_review_id": consensus.get("matched_review_id", ""),
                    "matched_claim_text": consensus.get("matched_claim_text", ""),
                    "matched_terms": consensus.get("matched_terms", []),
                    "meta_review_uptake_label": claim.get("meta_review_uptake", {}).get("label", ""),
                    "rebuttal_proxy_label": claim.get("rebuttal_resolution", {}).get("label", ""),
                }


def targeted_consensus_sample(claims: list[dict[str, Any]], *, sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size <= 0 or not claims:
        return []
    rng = random.Random(seed)
    buckets = [
        ("proxy_partial", 0.45, lambda item: item.get("proxy_consensus_label") == "partial"),
        ("proxy_strong", 0.30, lambda item: item.get("proxy_consensus_label") == "strong"),
        ("proxy_none", 0.20, lambda item: item.get("proxy_consensus_label") == "none"),
        ("high_score", 0.05, lambda item: item.get("proxy_consensus_score", 0.0) >= 0.45),
    ]
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for index, (reason, ratio, predicate) in enumerate(buckets):
        target = int(sample_size * ratio)
        if index == len(buckets) - 1:
            target = sample_size - len(selected)
        candidates = [item for item in claims if item["task_id"] not in selected_ids and predicate(item)]
        rng.shuffle(candidates)
        for item in candidates[: max(0, target)]:
            selected.append(with_sampling_reason(item, reason))
            selected_ids.add(item["task_id"])
    leftovers = [item for item in claims if item["task_id"] not in selected_ids]
    rng.shuffle(leftovers)
    for item in leftovers:
        if len(selected) >= sample_size:
            break
        selected.append(with_sampling_reason(item, "fill_remaining"))
        selected_ids.add(item["task_id"])
    rng.shuffle(selected)
    return selected[:sample_size]


def iter_reviewer_calibration_claims(report: dict[str, Any]):
    for paper in report.get("papers", []):
        for review in paper.get("reviews", []):
            for index, claim in enumerate(review.get("claims", [])):
                rebuttal = claim.get("rebuttal_resolution", {})
                yield {
                    "task_id": f"{paper.get('paper_id', '')}:{review.get('review_id', '')}:{index}",
                    "paper_id": paper.get("paper_id", ""),
                    "review_id": review.get("review_id", ""),
                    "claim_index": index,
                    "title": paper.get("title", ""),
                    "decision_label": paper.get("decision_label", ""),
                    "review_rating_raw": review.get("rating_raw", ""),
                    "review_rating_normalized": review.get("rating_normalized"),
                    "claim_text": claim.get("claim_text", ""),
                    "claim_type": claim.get("claim_type", ""),
                    "importance": claim.get("importance", ""),
                    "source_sentence": claim.get("source_sentence", ""),
                    "proxy_rebuttal_label": rebuttal.get("label", ""),
                    "proxy_rebuttal_score": rebuttal.get("score", 0.0),
                    "author_response_segment": rebuttal.get("matched_segment", ""),
                    "matched_terms": rebuttal.get("matched_terms", []),
                    "has_resolution_cue": rebuttal.get("has_resolution_cue", False),
                    "consensus_label": claim.get("consensus", {}).get("label", ""),
                    "meta_review_uptake_label": claim.get("meta_review_uptake", {}).get("label", ""),
                    "discussion_followup_label": claim.get("discussion_followup", {}).get("label", ""),
                }


def targeted_rebuttal_sample(claims: list[dict[str, Any]], *, sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size <= 0 or not claims:
        return []
    rng = random.Random(seed)
    buckets = [
        ("proxy_addressed_unclear", 0.45, lambda item: item.get("proxy_rebuttal_label") == "addressed_unclear_resolution"),
        ("proxy_likely_resolved", 0.25, lambda item: item.get("proxy_rebuttal_label") == "likely_resolved_or_answered"),
        ("proxy_not_addressed", 0.20, lambda item: item.get("proxy_rebuttal_label") == "not_addressed"),
        ("high_score_unclear", 0.10, lambda item: item.get("proxy_rebuttal_score", 0.0) >= 0.35),
    ]
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for index, (reason, ratio, predicate) in enumerate(buckets):
        target = int(sample_size * ratio)
        if index == len(buckets) - 1:
            target = sample_size - len(selected)
        candidates = [item for item in claims if item["task_id"] not in selected_ids and predicate(item)]
        rng.shuffle(candidates)
        for item in candidates[: max(0, target)]:
            selected.append(with_sampling_reason(item, reason))
            selected_ids.add(item["task_id"])
    leftovers = [item for item in claims if item["task_id"] not in selected_ids]
    rng.shuffle(leftovers)
    for item in leftovers:
        if len(selected) >= sample_size:
            break
        selected.append(with_sampling_reason(item, "fill_remaining"))
        selected_ids.add(item["task_id"])
    rng.shuffle(selected)
    return selected[:sample_size]


def label_rebuttal_resolution_item(
    item: dict[str, Any],
    *,
    llm_client: Any,
    model: str = DEFAULT_REBUTTAL_RESOLUTION_CALIBRATION_MODEL,
    annotator_id: str | None = None,
) -> dict[str, Any]:
    annotator_id = annotator_id or f"llm:{model}"
    payload = llm_client.complete_json(
        model=model,
        messages=rebuttal_resolution_messages(item),
        schema_name="rebuttal_resolution_calibration_label",
        schema=rebuttal_resolution_schema(),
    )
    label = {
        "label_id": stable_label_id(item.get("task_id", ""), annotator_id),
        "task_id": item.get("task_id", ""),
        "paper_id": item.get("paper_id", ""),
        "review_id": item.get("review_id", ""),
        "label_schema_version": REBUTTAL_RESOLUTION_LABEL_VERSION,
        "annotator_type": "llm",
        "annotator_id": annotator_id,
        "model": model,
        "proxy_rebuttal_label": item.get("proxy_rebuttal_label", ""),
        "proxy_rebuttal_score": item.get("proxy_rebuttal_score", 0.0),
        "labels": payload.get("labels", {}),
        "notes": str(payload.get("notes", "")),
        "created_at": utc_now(),
    }
    errors = validate_rebuttal_resolution_label(label)
    if errors:
        raise ValueError(f"Invalid rebuttal resolution label for {label['task_id']}: {errors}")
    return label


def label_consensus_item(
    item: dict[str, Any],
    *,
    llm_client: Any,
    model: str = DEFAULT_CONSENSUS_CALIBRATION_MODEL,
    annotator_id: str | None = None,
) -> dict[str, Any]:
    annotator_id = annotator_id or f"llm:{model}"
    payload = llm_client.complete_json(
        model=model,
        messages=consensus_messages(item),
        schema_name="inter_reviewer_consensus_calibration_label",
        schema=consensus_schema(),
    )
    label = {
        "label_id": stable_label_id(item.get("task_id", ""), annotator_id, version=INTER_REVIEWER_CONSENSUS_LABEL_VERSION),
        "task_id": item.get("task_id", ""),
        "paper_id": item.get("paper_id", ""),
        "review_id": item.get("review_id", ""),
        "label_schema_version": INTER_REVIEWER_CONSENSUS_LABEL_VERSION,
        "annotator_type": "llm",
        "annotator_id": annotator_id,
        "model": model,
        "proxy_consensus_label": item.get("proxy_consensus_label", ""),
        "proxy_consensus_score": item.get("proxy_consensus_score", 0.0),
        "labels": payload.get("labels", {}),
        "notes": str(payload.get("notes", "")),
        "created_at": utc_now(),
    }
    errors = validate_consensus_label(label)
    if errors:
        raise ValueError(f"Invalid consensus label for {label['task_id']}: {errors}")
    return label


def consensus_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    compact = {
        "task_id": item.get("task_id", ""),
        "title": truncate(item.get("title", ""), 220),
        "reviewer_claim": item.get("claim_text", ""),
        "claim_type": item.get("claim_type", ""),
        "importance": item.get("importance", ""),
        "matched_other_reviewer_claim": item.get("matched_claim_text", ""),
        "matched_other_review_id": item.get("matched_review_id", ""),
        "proxy_consensus_label": item.get("proxy_consensus_label", ""),
        "proxy_consensus_score": item.get("proxy_consensus_score", 0.0),
        "matched_terms": item.get("matched_terms", []),
    }
    return [
        {
            "role": "system",
            "content": (
                "You calibrate whether two reviewer claims from the same paper express the same concern. "
                "Judge semantic equivalence, not keyword overlap. Return JSON matching the schema."
            ),
        },
        {
            "role": "user",
            "content": (
                "Label this pair of reviewer claims.\n\n"
                "Definitions:\n"
                "- same_concern: both claims raise substantially the same issue.\n"
                "- related_but_different: claims are in a related area but differ in the concrete concern.\n"
                "- not_same_concern: claims are not meaningfully the same issue.\n"
                "- unsure: insufficient context.\n\n"
                "Set training_use=include for reliable labels, including reliable negatives.\n\n"
                f"Item JSON:\n{json.dumps(compact, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def consensus_schema() -> dict[str, Any]:
    labels_properties = {
        "consensus_label": {"type": "string", "enum": list(CONSENSUS_RESPONSE_LABELS)},
        "relation": {"type": "string", "enum": list(CONSENSUS_RELATION_LABELS)},
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


def validate_consensus_label(label: dict[str, Any]) -> list[str]:
    errors = []
    for key in ("label_id", "task_id", "label_schema_version", "labels", "created_at"):
        if key not in label:
            errors.append(f"missing:{key}")
    if errors:
        return errors
    if label.get("label_schema_version") != INTER_REVIEWER_CONSENSUS_LABEL_VERSION:
        errors.append("invalid:label_schema_version")
    labels = label.get("labels")
    if not isinstance(labels, dict):
        return [*errors, "invalid:labels"]
    errors.extend(require_enum(labels, "consensus_label", CONSENSUS_RESPONSE_LABELS))
    errors.extend(require_enum(labels, "relation", CONSENSUS_RELATION_LABELS))
    errors.extend(require_enum(labels, "confidence", CONFIDENCE_LABELS))
    errors.extend(require_enum(labels, "training_use", TRAINING_USE_LABELS))
    if not isinstance(labels.get("rationale"), str):
        errors.append("invalid:labels.rationale")
    return errors


def merge_consensus_labels(items: list[dict[str, Any]], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels_by_task = {label["task_id"]: label for label in labels}
    merged = []
    for item in items:
        label = labels_by_task.get(item.get("task_id", ""))
        if not label:
            continue
        payload = label.get("labels", {})
        record = dict(item)
        record.update(
            {
                "llm_label_id": label.get("label_id", ""),
                "llm_consensus_label": payload.get("consensus_label", ""),
                "llm_consensus_relation": payload.get("relation", ""),
                "llm_confidence": payload.get("confidence", ""),
                "llm_training_use": payload.get("training_use", ""),
                "llm_rationale": payload.get("rationale", ""),
                "llm_notes": label.get("notes", ""),
            }
        )
        record["high_confidence_training_candidate"] = (
            record["llm_confidence"] == "high"
            and record["llm_training_use"] == "include"
            and record["llm_consensus_label"] != "unsure"
        )
        merged.append(record)
    return merged


def rebuttal_resolution_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    compact = {
        "task_id": item.get("task_id", ""),
        "title": truncate(item.get("title", ""), 220),
        "decision_label": item.get("decision_label", ""),
        "review_rating_raw": item.get("review_rating_raw", ""),
        "reviewer_claim": item.get("claim_text", ""),
        "claim_type": item.get("claim_type", ""),
        "importance": item.get("importance", ""),
        "source_sentence": item.get("source_sentence", ""),
        "author_response_segment": item.get("author_response_segment", ""),
        "proxy_rebuttal_label": item.get("proxy_rebuttal_label", ""),
        "proxy_rebuttal_score": item.get("proxy_rebuttal_score", 0.0),
        "matched_terms": item.get("matched_terms", []),
        "has_resolution_cue": item.get("has_resolution_cue", False),
        "consensus_label": item.get("consensus_label", ""),
        "meta_review_uptake_label": item.get("meta_review_uptake_label", ""),
        "discussion_followup_label": item.get("discussion_followup_label", ""),
    }
    return [
        {
            "role": "system",
            "content": (
                "You calibrate whether an author rebuttal actually addresses a reviewer claim. "
                "Judge semantic relevance and resolution, not keyword overlap. "
                "A polite generic response is not enough. Return JSON matching the schema."
            ),
        },
        {
            "role": "user",
            "content": (
                "Label this reviewer-claim / author-response pair.\n\n"
                "Definitions:\n"
                "- not_addressed: the response segment does not discuss the reviewer claim.\n"
                "- generic_or_unclear: the response uses broad language or overlapping words but does not specifically answer the claim.\n"
                "- specifically_addressed: the response directly discusses the claim, but it is unclear whether the concern is resolved.\n"
                "- likely_resolved: the response directly answers, weakens, fixes, or provides evidence against the concern.\n\n"
                "Use high confidence only when the claim and response segment make the label clear. "
                "Set training_use=include for reliable positive or negative labels; exclude ambiguous cases.\n\n"
                f"Item JSON:\n{json.dumps(compact, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def rebuttal_resolution_schema() -> dict[str, Any]:
    labels_properties = {
        "rebuttal_response_label": {"type": "string", "enum": list(REBUTTAL_RESPONSE_LABELS)},
        "rebuttal_effect_on_claim": {"type": "string", "enum": list(REBUTTAL_EFFECT_LABELS)},
        "response_specificity": {"type": "string", "enum": list(RESPONSE_SPECIFICITY_LABELS)},
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


def validate_rebuttal_resolution_label(label: dict[str, Any]) -> list[str]:
    errors = []
    for key in ("label_id", "task_id", "label_schema_version", "labels", "created_at"):
        if key not in label:
            errors.append(f"missing:{key}")
    if errors:
        return errors
    if label.get("label_schema_version") != REBUTTAL_RESOLUTION_LABEL_VERSION:
        errors.append("invalid:label_schema_version")
    labels = label.get("labels")
    if not isinstance(labels, dict):
        return [*errors, "invalid:labels"]
    errors.extend(require_enum(labels, "rebuttal_response_label", REBUTTAL_RESPONSE_LABELS))
    errors.extend(require_enum(labels, "rebuttal_effect_on_claim", REBUTTAL_EFFECT_LABELS))
    errors.extend(require_enum(labels, "response_specificity", RESPONSE_SPECIFICITY_LABELS))
    errors.extend(require_enum(labels, "confidence", CONFIDENCE_LABELS))
    errors.extend(require_enum(labels, "training_use", TRAINING_USE_LABELS))
    if not isinstance(labels.get("rationale"), str):
        errors.append("invalid:labels.rationale")
    return errors


def merge_rebuttal_resolution_labels(items: list[dict[str, Any]], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels_by_task = {label["task_id"]: label for label in labels}
    merged = []
    for item in items:
        label = labels_by_task.get(item.get("task_id", ""))
        if not label:
            continue
        payload = label.get("labels", {})
        record = dict(item)
        record.update(
            {
                "llm_label_id": label.get("label_id", ""),
                "llm_rebuttal_response_label": payload.get("rebuttal_response_label", ""),
                "llm_rebuttal_effect_on_claim": payload.get("rebuttal_effect_on_claim", ""),
                "llm_response_specificity": payload.get("response_specificity", ""),
                "llm_confidence": payload.get("confidence", ""),
                "llm_training_use": payload.get("training_use", ""),
                "llm_rationale": payload.get("rationale", ""),
                "llm_notes": label.get("notes", ""),
            }
        )
        record["high_confidence_training_candidate"] = (
            record["llm_confidence"] == "high"
            and record["llm_training_use"] == "include"
            and record["llm_rebuttal_response_label"] != "generic_or_unclear"
        )
        merged.append(record)
    return merged


def build_rebuttal_resolution_calibration_report(
    *,
    items: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    merged: list[dict[str, Any]],
) -> dict[str, Any]:
    high_confidence = [item for item in merged if item.get("high_confidence_training_candidate")]
    agreement_count = sum(
        1
        for item in merged
        if proxy_to_llm_label(item.get("proxy_rebuttal_label", "")) == item.get("llm_rebuttal_response_label", "")
    )
    return {
        "schema_version": "rebuttal-resolution-calibration-report-v0.1",
        "label_schema_version": REBUTTAL_RESOLUTION_LABEL_VERSION,
        "input_item_count": len(items),
        "label_count": len(labels),
        "merged_count": len(merged),
        "high_confidence_count": len(high_confidence),
        "proxy_llm_agreement_count": agreement_count,
        "proxy_llm_agreement_rate": round(agreement_count / max(len(merged), 1), 4),
        "proxy_label_counts": dict(Counter(item.get("proxy_rebuttal_label", "") for item in merged)),
        "llm_response_label_counts": dict(Counter(item.get("llm_rebuttal_response_label", "") for item in merged)),
        "llm_effect_counts": dict(Counter(item.get("llm_rebuttal_effect_on_claim", "") for item in merged)),
        "llm_specificity_counts": dict(Counter(item.get("llm_response_specificity", "") for item in merged)),
        "high_confidence_response_label_counts": dict(Counter(item.get("llm_rebuttal_response_label", "") for item in high_confidence)),
        "examples": {
            "high_confidence": [rebuttal_example(item) for item in high_confidence[:10]],
            "proxy_disagreement": [
                rebuttal_example(item)
                for item in merged
                if proxy_to_llm_label(item.get("proxy_rebuttal_label", "")) != item.get("llm_rebuttal_response_label", "")
            ][:10],
        },
    }


def build_consensus_calibration_report(
    *,
    items: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    merged: list[dict[str, Any]],
) -> dict[str, Any]:
    high_confidence = [item for item in merged if item.get("high_confidence_training_candidate")]
    agreement_count = sum(
        1
        for item in merged
        if proxy_to_consensus_llm_label(item.get("proxy_consensus_label", "")) == item.get("llm_consensus_label", "")
    )
    return {
        "schema_version": "inter-reviewer-consensus-calibration-report-v0.1",
        "label_schema_version": INTER_REVIEWER_CONSENSUS_LABEL_VERSION,
        "input_item_count": len(items),
        "label_count": len(labels),
        "merged_count": len(merged),
        "high_confidence_count": len(high_confidence),
        "proxy_llm_agreement_count": agreement_count,
        "proxy_llm_agreement_rate": round(agreement_count / max(len(merged), 1), 4),
        "proxy_label_counts": dict(Counter(item.get("proxy_consensus_label", "") for item in merged)),
        "llm_consensus_label_counts": dict(Counter(item.get("llm_consensus_label", "") for item in merged)),
        "llm_relation_counts": dict(Counter(item.get("llm_consensus_relation", "") for item in merged)),
        "high_confidence_consensus_label_counts": dict(Counter(item.get("llm_consensus_label", "") for item in high_confidence)),
        "examples": {
            "high_confidence": [consensus_example(item) for item in high_confidence[:10]],
            "proxy_disagreement": [
                consensus_example(item)
                for item in merged
                if proxy_to_consensus_llm_label(item.get("proxy_consensus_label", "")) != item.get("llm_consensus_label", "")
            ][:10],
        },
    }


def write_consensus_calibration_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_consensus_calibration_markdown(report), encoding="utf-8")


def render_consensus_calibration_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Inter-Reviewer Consensus LLM Calibration",
        "",
        f"- Input items: {report.get('input_item_count', 0)}",
        f"- Labels: {report.get('label_count', 0)}",
        f"- High-confidence training candidates: {report.get('high_confidence_count', 0)}",
        f"- Proxy/LLM agreement: {format_rate(report.get('proxy_llm_agreement_rate', 0.0))}",
        "",
        "## Label Counts",
        "",
    ]
    for key in (
        "proxy_label_counts",
        "llm_consensus_label_counts",
        "llm_relation_counts",
        "high_confidence_consensus_label_counts",
    ):
        lines.append(f"- `{key}`: `{json.dumps(report.get(key, {}), ensure_ascii=False, sort_keys=True)}`")
    return "\n".join(lines)


def index_rebuttal_resolution_labels(labels: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed = {}
    for label in labels:
        task_id = label.get("task_id", "")
        if task_id:
            indexed[task_id] = label
    return indexed


def index_consensus_labels(labels: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed = {}
    for label in labels:
        task_id = label.get("task_id", "")
        if task_id:
            indexed[task_id] = label
    return indexed


def llm_rebuttal_calibration_payload(label: dict[str, Any]) -> dict[str, Any]:
    return {
        "label_id": label.get("llm_label_id", label.get("label_id", "")),
        "rebuttal_response_label": label.get("llm_rebuttal_response_label", ""),
        "rebuttal_effect_on_claim": label.get("llm_rebuttal_effect_on_claim", ""),
        "response_specificity": label.get("llm_response_specificity", ""),
        "confidence": label.get("llm_confidence", ""),
        "training_use": label.get("llm_training_use", ""),
        "rationale": label.get("llm_rationale", ""),
        "high_confidence_training_candidate": bool(label.get("high_confidence_training_candidate")),
    }


def llm_rebuttal_label(claim: dict[str, Any]) -> str:
    return claim.get("rebuttal_resolution", {}).get("llm_calibration", {}).get("rebuttal_response_label", "")


def llm_rebuttal_effect(claim: dict[str, Any]) -> str:
    return claim.get("rebuttal_resolution", {}).get("llm_calibration", {}).get("rebuttal_effect_on_claim", "")


def llm_consensus_calibration_payload(label: dict[str, Any]) -> dict[str, Any]:
    return {
        "label_id": label.get("llm_label_id", label.get("label_id", "")),
        "consensus_label": label.get("llm_consensus_label", ""),
        "relation": label.get("llm_consensus_relation", ""),
        "confidence": label.get("llm_confidence", ""),
        "training_use": label.get("llm_training_use", ""),
        "rationale": label.get("llm_rationale", ""),
        "high_confidence_training_candidate": bool(label.get("high_confidence_training_candidate")),
    }


def llm_consensus_label(claim: dict[str, Any]) -> str:
    return claim.get("consensus", {}).get("llm_calibration", {}).get("consensus_label", "")


def write_rebuttal_resolution_calibration_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_rebuttal_resolution_calibration_markdown(report), encoding="utf-8")


def render_rebuttal_resolution_calibration_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Rebuttal Resolution LLM Calibration",
        "",
        f"- Input items: {report.get('input_item_count', 0)}",
        f"- Labels: {report.get('label_count', 0)}",
        f"- High-confidence training candidates: {report.get('high_confidence_count', 0)}",
        f"- Proxy/LLM agreement: {format_rate(report.get('proxy_llm_agreement_rate', 0.0))}",
        "",
        "## Label Counts",
        "",
    ]
    for key in (
        "proxy_label_counts",
        "llm_response_label_counts",
        "llm_effect_counts",
        "llm_specificity_counts",
        "high_confidence_response_label_counts",
    ):
        lines.append(f"- `{key}`: `{json.dumps(report.get(key, {}), ensure_ascii=False, sort_keys=True)}`")
    lines.extend(["", "## Examples", ""])
    for section, examples in report.get("examples", {}).items():
        lines.append(f"### {section.replace('_', ' ').title()}")
        if not examples:
            lines.append("No examples.")
            continue
        for example in examples:
            lines.append(
                f"- `{example['task_id']}` proxy=`{example['proxy_rebuttal_label']}` "
                f"llm=`{example['llm_rebuttal_response_label']}` confidence=`{example['llm_confidence']}`"
            )
            lines.append(f"  - Claim: {example['claim_text']}")
            lines.append(f"  - Response: {example['author_response_segment']}")
            lines.append(f"  - Rationale: {example['llm_rationale']}")
    return "\n".join(lines)


def load_paper_auxiliary(snapshot_dir: str | Path) -> dict[str, dict[str, Any]]:
    notes = load_snapshot_notes(snapshot_dir)
    indexed: dict[str, dict[str, Any]] = {}
    for note in notes:
        paper_id = str(note.get("id") or note.get("forum") or "")
        replies = get_replies(note)
        classified = [classify_reply(reply) for reply in replies]
        reviewer_identities = {}
        for reply, classified_reply in zip(replies, classified):
            if classified_reply["type"] != "official_review":
                continue
            reviewer_identities[classified_reply["id"]] = reviewer_identity_payload(classified_reply)
        aux = {
            "author_responses": [item["text"] for item in classified if item["type"] == "author_response" and item["text"]],
            "reviewer_or_ac_discussions": [
                item["text"]
                for item in classified
                if item["type"] == "official_comment"
                and item["signer_role"] in {"reviewer", "area_chair", "program_chair"}
                and item["text"]
            ],
            "reviewer_identities": reviewer_identities,
            "title": text_from_content(note.get("content") or {}, ["title"]),
        }
        indexed[paper_id] = aux
    return indexed


def reviewer_identity_payload(classified_reply: dict[str, Any]) -> dict[str, Any]:
    raw = "|".join(str(signature) for signature in classified_reply.get("signatures", []))
    return {
        "reviewer_identity_hash": stable_hash(raw) if raw else "",
        "signer_role": classified_reply.get("signer_role", ""),
    }


def stable_hash(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def write_reviewer_calibration_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_reviewer_calibration_markdown(report), encoding="utf-8")


def render_reviewer_calibration_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Reviewer Reliability Calibration",
        "",
        f"- Papers: {summary.get('paper_count', 0)}",
        f"- Reviews: {summary.get('review_count', 0)}",
        f"- Claims: {summary.get('claim_count', 0)}",
        f"- Mean review reliability: {format_rate(summary.get('mean_review_reliability_score', 0.0))}",
        f"- Mean LLM-calibrated reliability: {format_rate(summary.get('mean_llm_calibrated_review_reliability_score', summary.get('mean_review_reliability_score', 0.0)))}",
        f"- Mean LLM-calibrated delta: {summary.get('mean_llm_calibrated_reliability_delta', 0.0):+.3f}",
        "",
        "## Core Signals",
        "",
        "| Signal | Value |",
        "| --- | ---: |",
        f"| Mean inter-review consensus rate | {format_rate(summary.get('mean_inter_review_consensus_rate', 0.0))} |",
        f"| Mean LLM consensus label coverage | {format_rate(summary.get('mean_llm_consensus_label_coverage', 0.0))} |",
        f"| Mean LLM same-concern rate | {format_rate(summary.get('mean_llm_consensus_same_rate', 0.0))} |",
        f"| Mean LLM related-or-same rate | {format_rate(summary.get('mean_llm_consensus_related_or_same_rate', 0.0))} |",
        f"| Mean rebuttal addressed rate | {format_rate(summary.get('mean_rebuttal_addressed_rate', 0.0))} |",
        f"| Mean LLM rebuttal label coverage | {format_rate(summary.get('mean_llm_rebuttal_label_coverage', 0.0))} |",
        f"| Mean LLM rebuttal addressed rate | {format_rate(summary.get('mean_llm_rebuttal_addressed_rate', 0.0))} |",
        f"| Mean LLM rebuttal resolved rate | {format_rate(summary.get('mean_llm_rebuttal_resolved_rate', 0.0))} |",
        f"| Mean meta-review uptake rate | {format_rate(summary.get('mean_meta_review_uptake_rate', 0.0))} |",
        f"| Mean claim lifecycle robustness | {format_rate(summary.get('mean_claim_lifecycle_robustness_score', 0.0))} |",
        f"| Mean high-robustness claim rate | {format_rate(summary.get('mean_high_robustness_claim_rate', 0.0))} |",
        f"| Mean medium/high robustness claim rate | {format_rate(summary.get('mean_medium_or_high_robustness_claim_rate', 0.0))} |",
        "",
        "## Label Counts",
        "",
    ]
    for key in (
        "rating_calibration_counts",
        "confidence_calibration_counts",
        "reviewer_style_counts",
        "claim_lifecycle_robustness_counts",
        "claim_consensus_counts",
        "claim_llm_consensus_response_counts",
        "claim_llm_consensus_relation_counts",
        "claim_rebuttal_resolution_counts",
        "claim_llm_rebuttal_response_counts",
        "claim_llm_rebuttal_effect_counts",
        "reviewer_identity_summary",
    ):
        lines.append(f"- `{key}`: `{json.dumps(summary.get(key, {}), ensure_ascii=False, sort_keys=True)}`")
    lines.extend(["", "## Example Reviews", ""])
    for label in ("high_reliability_reviews", "low_reliability_reviews"):
        lines.append(f"### {label.replace('_', ' ').title()}")
        examples = report.get("examples", {}).get(label, [])
        if not examples:
            lines.append("No examples.")
            continue
        for item in examples:
            lines.append(
                f"- `{item['review_id']}` paper=`{item['paper_id']}` score={item['review_reliability_score']:.3f} "
                f"rating_gap={item['rating_gap']} style=`{item['reviewer_style_label']}`"
            )
    return "\n".join(lines)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def claim_text(claim: dict[str, Any]) -> str:
    return " ".join(
        clean_text(part)
        for part in (claim.get("claim_text", ""), claim.get("source_sentence", ""), claim.get("claim_type", ""))
        if clean_text(part)
    )


def specificity_score(claim: dict[str, Any]) -> float:
    text = clean_text(claim.get("claim_text", ""))
    tokens = concern_tokens(text)
    if not tokens:
        return 0.0
    length_score = min(1.0, len(tokens) / 18)
    anchor_bonus = 0.15 if tokens & {"ablation", "baseline", "dataset", "experiment", "theory", "result", "method"} else 0.0
    action_bonus = 0.15 if re.search(r"\b(lack|missing|unclear|should|need|compare|evaluate|ablation|baseline)\b", text.lower()) else 0.0
    vague_penalty = 0.2 if len(tokens) < 6 or text.lower() in {"unclear", "weakness", "minor issue"} else 0.0
    return round(max(0.0, min(1.0, length_score + anchor_bonus + action_bonus - vague_penalty)), 4)


def consensus_label(score: float) -> str:
    if score >= CONSENSUS_STRONG_THRESHOLD:
        return "strong"
    if score >= CONSENSUS_PARTIAL_THRESHOLD:
        return "partial"
    return "none"


def has_resolution_cue(text: str) -> bool:
    terms = set(clean_text(text).lower().split())
    return bool(terms & RESOLUTION_CUES)


def review_concern_severity(claims: list[dict[str, Any]]) -> float:
    if not claims:
        return 0.0
    scores = []
    for claim in claims:
        importance = importance_weight(claim.get("importance", ""))
        consensus = 1.0 if claim["consensus"]["label"] == "strong" else 0.65 if claim["consensus"]["label"] == "partial" else 0.0
        meta = 1.0 if claim["meta_review_uptake"]["label"] == "survived" else 0.65 if claim["meta_review_uptake"]["label"] == "partial" else 0.0
        unresolved = 0.0 if claim["rebuttal_resolution"]["label"] == "likely_resolved_or_answered" else 1.0
        score = importance * (
            0.25 * claim.get("specificity_score", 0.0)
            + 0.25 * consensus
            + 0.35 * meta
            + 0.15 * unresolved
        )
        scores.append(score)
    scores.sort(reverse=True)
    top = scores[: min(4, len(scores))]
    return round(sum(top) / len(top), 4)


def importance_weight(value: str) -> float:
    lowered = clean_text(value).lower()
    if lowered == "major":
        return 1.0
    if lowered == "medium":
        return 0.75
    if lowered == "minor":
        return 0.45
    if lowered == "question":
        return 0.35
    return 0.6


def expected_rating_from_severity(severity: float) -> float:
    return round(max(1.0, min(10.0, 8.5 - 6.0 * severity)), 3)


def review_reliability_score(
    *,
    grounded_rate: float,
    specificity: float,
    consensus_rate: float,
    meta_uptake_rate: float,
    rebuttal_resolved_rate: float,
    rating_gap: float | None,
    reviewer_confidence: float | None,
) -> float:
    rating_calibration = 0.5 if rating_gap is None else max(0.0, 1.0 - min(abs(rating_gap), 4.0) / 4.0)
    confidence_alignment = 0.5
    if reviewer_confidence is not None:
        normalized_conf = max(0.0, min(1.0, float(reviewer_confidence) / 10.0))
        confidence_alignment = 1.0 - abs(normalized_conf - (0.35 + 0.65 * ((specificity + consensus_rate + meta_uptake_rate) / 3)))
    score = (
        0.2 * grounded_rate
        + 0.2 * specificity
        + 0.2 * consensus_rate
        + 0.2 * meta_uptake_rate
        + 0.1 * (1.0 - rebuttal_resolved_rate)
        + 0.05 * rating_calibration
        + 0.05 * confidence_alignment
    )
    return round(max(0.0, min(1.0, score)), 4)


def rating_calibration_label(rating_gap: float | None) -> str:
    if rating_gap is None:
        return "rating_missing"
    if rating_gap <= -1.5:
        return "harsher_than_claim_signals"
    if rating_gap >= 1.5:
        return "more_lenient_than_claim_signals"
    return "calibrated_to_claim_signals"


def confidence_calibration_label(confidence: float | None, reliability: float) -> str:
    if confidence is None:
        return "confidence_missing"
    normalized = float(confidence) / 10.0
    if normalized >= 0.75 and reliability < 0.45:
        return "possibly_overconfident"
    if normalized <= 0.45 and reliability >= 0.65:
        return "possibly_underconfident"
    return "confidence_reasonable"


def reviewer_style_label(rating_gap: float | None, confidence: float | None, reliability: float) -> str:
    if rating_gap is not None and rating_gap <= -1.5:
        return "over_harsh_proxy"
    if rating_gap is not None and rating_gap >= 1.5:
        return "over_lenient_proxy"
    if confidence is not None and confidence >= 7.5 and reliability < 0.45:
        return "confident_but_low_signal_proxy"
    if reliability >= 0.65:
        return "high_signal_review"
    return "mixed_signal_review"


def review_examples(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples = []
    for review in reviews:
        examples.append(
            {
                "paper_id": review.get("paper_id", ""),
                "review_id": review.get("review_id", ""),
                "review_reliability_score": review.get("review_reliability_score", 0.0),
                "rating_gap": review.get("rating_gap"),
                "reviewer_style_label": review.get("reviewer_style_label", ""),
            }
        )
    return examples


def reviewer_identity_summary(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    hashes = [review.get("reviewer_identity_hash", "") for review in reviews if review.get("reviewer_identity_hash")]
    counts = Counter(hashes)
    repeated = {key: count for key, count in counts.items() if count > 1}
    return {
        "review_with_identity_count": len(hashes),
        "unique_identity_count": len(counts),
        "repeated_identity_count": len(repeated),
        "max_reviews_per_identity": max(counts.values(), default=0),
        "aggregation_status": "usable" if repeated else "not_available_or_anonymized_per_submission",
    }


def claim_examples(claims: Any) -> list[dict[str, Any]]:
    return [
        {
            "claim_text": truncate(claim.get("claim_text", ""), 220),
            "claim_type": claim.get("claim_type", ""),
            "lifecycle_robustness_label": claim.get("lifecycle_robustness", {}).get("label", ""),
            "lifecycle_robustness_score": claim.get("lifecycle_robustness", {}).get("score", 0.0),
            "consensus_label": claim.get("consensus", {}).get("label", ""),
            "rebuttal_label": claim.get("rebuttal_resolution", {}).get("label", ""),
            "meta_review_uptake": claim.get("meta_review_uptake", {}).get("label", ""),
        }
        for claim in claims
    ]


def rate_value(values: Any) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 4)


def safe_rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def mean_value(values: Any) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(float(value or 0.0) for value in values) / len(values), 4)


def format_rate(value: float) -> str:
    return f"{float(value):.1%}"


def truncate(value: Any, limit: int) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def with_sampling_reason(item: dict[str, Any], reason: str) -> dict[str, Any]:
    copied = dict(item)
    copied["sampling_reason"] = reason
    return copied


def stable_label_id(task_id: str, annotator_id: str, *, version: str = REBUTTAL_RESOLUTION_LABEL_VERSION) -> str:
    import hashlib

    digest = hashlib.sha1(f"{task_id}|{annotator_id}|{version}".encode("utf-8")).hexdigest()
    return f"rebuttal_res_{digest[:16]}"


def utc_now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def require_enum(labels: dict[str, Any], key: str, values: tuple[str, ...]) -> list[str]:
    if key not in labels:
        return [f"missing:labels.{key}"]
    if labels[key] not in values:
        return [f"invalid:labels.{key}"]
    return []


def proxy_to_consensus_llm_label(proxy_label: str) -> str:
    if proxy_label == "strong":
        return "same_concern"
    if proxy_label == "partial":
        return "related_but_different"
    if proxy_label == "none":
        return "not_same_concern"
    return "unsure"


def consensus_example(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": item.get("task_id", ""),
        "proxy_consensus_label": item.get("proxy_consensus_label", ""),
        "llm_consensus_label": item.get("llm_consensus_label", ""),
        "llm_confidence": item.get("llm_confidence", ""),
        "claim_text": truncate(item.get("claim_text", ""), 260),
        "matched_claim_text": truncate(item.get("matched_claim_text", ""), 260),
        "llm_rationale": truncate(item.get("llm_rationale", ""), 300),
    }


def proxy_to_llm_label(proxy_label: str) -> str:
    if proxy_label == "not_addressed":
        return "not_addressed"
    if proxy_label == "likely_resolved_or_answered":
        return "likely_resolved"
    if proxy_label == "addressed_unclear_resolution":
        return "specifically_addressed"
    return "generic_or_unclear"


def rebuttal_example(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": item.get("task_id", ""),
        "proxy_rebuttal_label": item.get("proxy_rebuttal_label", ""),
        "llm_rebuttal_response_label": item.get("llm_rebuttal_response_label", ""),
        "llm_confidence": item.get("llm_confidence", ""),
        "claim_text": truncate(item.get("claim_text", ""), 260),
        "author_response_segment": truncate(item.get("author_response_segment", ""), 300),
        "llm_rationale": truncate(item.get("llm_rationale", ""), 300),
    }
