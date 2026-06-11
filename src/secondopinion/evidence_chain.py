from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .text import clean_text


EVIDENCE_CHAIN_DEMO_VERSION = "evidence-chain-demo-v0.1"
EVIDENCE_CHAIN_BENCHMARK_VERSION = "evidence-chain-benchmark-v0.1"
EVIDENCE_CHAIN_PSEUDO_EXPERT_VERSION = "evidence-chain-pseudo-expert-v0.1"
EXTERNAL_SOURCE_TYPES = {"venue_guideline", "external_reference", "field_consensus"}
PRIORITY_ORDER = {"low": 1, "medium": 2, "high": 3, "must": 4}


def build_evidence_chain_demo(
    audit_result: dict[str, Any],
    *,
    reviewer_calibration: dict[str, Any] | None = None,
    paper_id: str | None = None,
) -> dict[str, Any]:
    audits = [audit for audit in audit_result.get("audits", []) if not paper_id or audit.get("paper_id") == paper_id]
    if not audits:
        audits = list(audit_result.get("audits", []))
    selected_paper_id = paper_id or next((audit.get("paper_id", "") for audit in audits if audit.get("paper_id")), "")
    if selected_paper_id:
        audits = [audit for audit in audits if audit.get("paper_id") == selected_paper_id]
    calibration_by_review = index_calibration_reviews(reviewer_calibration or {})

    reviewers = []
    for review_index, audit in enumerate(audits, start=1):
        calibration_review = calibration_by_review.get((audit.get("paper_id", ""), audit.get("review_id", "")), {})
        claims = build_frontend_claims(audit, calibration_review)
        claims.sort(key=claim_sort_key)
        reviewers.append(
            {
                "review_id": audit.get("review_id", f"review-{review_index}"),
                "display_id": f"R{review_index}",
                "rating": audit.get("rating_raw") or audit.get("rating_normalized"),
                "confidence": audit.get("reviewer_confidence_raw") or audit.get("reviewer_confidence_normalized"),
                "review_reliability_score": round_score(
                    calibration_review.get("llm_calibrated_review_reliability_score")
                    or calibration_review.get("review_reliability_score")
                    or normalize_score(audit.get("rqs_score"), max_value=100)
                ),
                "mean_lifecycle_robustness": round_score(calibration_review.get("mean_lifecycle_robustness_score")),
                "high_risk_claim_count": sum(1 for claim in claims if claim["rebuttal_guidance"]["priority"] in {"must", "high"}),
                "summary": audit.get("summary", ""),
                "rating_calibration_label": calibration_review.get("rating_calibration_label", ""),
                "confidence_calibration_label": calibration_review.get("confidence_calibration_label", ""),
                "claims": claims,
            }
        )

    all_claims = [claim for reviewer in reviewers for claim in reviewer.get("claims", [])]
    return {
        "schema_version": EVIDENCE_CHAIN_DEMO_VERSION,
        "source": {
            "audit_schema_version": audit_result.get("schema_version", ""),
            "reviewer_calibration_version": (reviewer_calibration or {}).get("calibration_version", ""),
        },
        "paper": {
            "paper_id": selected_paper_id,
            "title": next((audit.get("paper_title", "") for audit in audits if audit.get("paper_title")), ""),
            "venue": "ICLR",
            "year": 2024,
            "decision": next((audit.get("decision", "") for audit in audits if audit.get("decision")), ""),
        },
        "summary": {
            "review_count": len(reviewers),
            "claim_count": len(all_claims),
            "high_priority_claim_count": sum(
                1 for claim in all_claims if claim["rebuttal_guidance"]["priority"] in {"must", "high"}
            ),
            "mean_reviewer_reliability": mean_score(reviewer.get("review_reliability_score") for reviewer in reviewers),
            "mean_lifecycle_robustness": mean_score(claim["scores"].get("lifecycle_robustness") for claim in all_claims),
            "priority_counts": dict(Counter(claim["rebuttal_guidance"]["priority"] for claim in all_claims)),
            "claim_type_counts": dict(Counter(claim.get("claim_type", "") for claim in all_claims)),
        },
        "reviewers": reviewers,
        "rebuttal_workspace": sorted(
            [
                {
                    "claim_id": claim["claim_id"],
                    "review_id": reviewer["review_id"],
                    "display_id": reviewer["display_id"],
                    "claim_text": claim["claim_text"],
                    "priority": claim["rebuttal_guidance"]["priority"],
                    "strategy": claim["rebuttal_guidance"]["strategy"],
                    "suggested_response": claim["rebuttal_guidance"]["suggested_response"],
                    "lifecycle_robustness": claim["scores"]["lifecycle_robustness"],
                    "scores": claim["scores"],
                    "evidence_chain": claim["evidence_chain"],
                    "evidence_to_cite": claim["rebuttal_guidance"]["evidence_to_cite"],
                }
                for reviewer in reviewers
                for claim in reviewer.get("claims", [])
            ],
            key=lambda item: (-PRIORITY_ORDER.get(item["priority"], 0), -float(item.get("lifecycle_robustness") or 0.0)),
        ),
    }


def build_frontend_claims(audit: dict[str, Any], calibration_review: dict[str, Any]) -> list[dict[str, Any]]:
    calibration_claims = calibration_review.get("claims", []) if calibration_review else []
    claims = []
    for index, audit_claim in enumerate(audit.get("claims", [])):
        calibration_claim = match_calibration_claim(audit_claim, calibration_claims, index)
        scores = claim_scores(audit_claim, calibration_claim)
        scores["reviewer_reliability"] = round_score(
            calibration_review.get("llm_calibrated_review_reliability_score")
            or calibration_review.get("review_reliability_score")
            or normalize_score(audit.get("rqs_score"), max_value=100)
        )
        evidence_chain = build_evidence_chain(audit_claim, calibration_claim)
        guidance = derive_rebuttal_guidance(audit_claim, calibration_claim, scores, evidence_chain)
        claims.append(
            {
                "claim_id": audit_claim.get("claim_id") or f"{audit.get('review_id', '')}:{index}",
                "claim_index": index + 1,
                "claim_text": audit_claim.get("claim_text", ""),
                "source_sentence": audit_claim.get("source_sentence", ""),
                "claim_type": audit_claim.get("claim_type", ""),
                "importance": audit_claim.get("importance", ""),
                "stance": audit_claim.get("stance", ""),
                "verdict": audit_claim.get("verdict", ""),
                "audit_confidence": audit_claim.get("audit_confidence", ""),
                "scores": scores,
                "score_explanations": score_explanations(audit_claim, calibration_claim),
                "evidence_chain": evidence_chain,
                "rebuttal_guidance": guidance,
                "system_judgment": {
                    "second_opinion_take": audit_claim.get("second_opinion_take", ""),
                    "reasoning_summary": audit_claim.get("reasoning_summary", ""),
                    "issue_flags": audit_claim.get("issue_flags", []),
                    "requires_external_knowledge": bool(audit_claim.get("requires_external_knowledge")),
                    "requires_human_expert": bool(audit_claim.get("requires_human_expert")),
                },
            }
        )
    return claims


def build_evidence_chain(audit_claim: dict[str, Any], calibration_claim: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    evidence = audit_claim.get("evidence") or []
    manuscript = [evidence_record(item) for item in evidence if item.get("source_type") not in EXTERNAL_SOURCE_TYPES]
    external = [evidence_record(item) for item in evidence if item.get("source_type") in EXTERNAL_SOURCE_TYPES]
    rebuttal = []
    rebuttal_segment = calibration_claim.get("rebuttal_resolution", {}).get("matched_segment", "")
    if clean_text(rebuttal_segment):
        rebuttal.append(
            {
                "source_type": "author_rebuttal",
                "label": calibration_claim.get("rebuttal_resolution", {}).get("label", ""),
                "score": calibration_claim.get("rebuttal_resolution", {}).get("score", 0.0),
                "text": rebuttal_segment,
            }
        )
    meta_review = []
    meta_segment = calibration_claim.get("meta_review_uptake", {}).get("matched_segment", "")
    if clean_text(meta_segment):
        meta_review.append(
            {
                "source_type": "meta_review",
                "label": calibration_claim.get("meta_review_uptake", {}).get("label", ""),
                "score": calibration_claim.get("meta_review_uptake", {}).get("score", 0.0),
                "text": meta_segment,
            }
        )
    discussion = []
    discussion_segment = calibration_claim.get("discussion_followup", {}).get("matched_segment", "")
    if clean_text(discussion_segment):
        discussion.append(
            {
                "source_type": "post_rebuttal_discussion",
                "label": calibration_claim.get("discussion_followup", {}).get("label", ""),
                "score": calibration_claim.get("discussion_followup", {}).get("score", 0.0),
                "text": discussion_segment,
            }
        )
    consensus = []
    matched_claim = calibration_claim.get("consensus", {}).get("matched_claim_text", "")
    if clean_text(matched_claim):
        consensus.append(
            {
                "source_type": "inter_reviewer_consensus",
                "label": calibration_claim.get("consensus", {}).get("label", ""),
                "score": calibration_claim.get("consensus", {}).get("score", 0.0),
                "text": matched_claim,
                "matched_review_id": calibration_claim.get("consensus", {}).get("matched_review_id", ""),
            }
        )
    return {
        "manuscript": manuscript,
        "external": external,
        "rebuttal": rebuttal,
        "meta_review": meta_review,
        "discussion": discussion,
        "consensus": consensus,
    }


def evidence_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": item.get("evidence_id", ""),
        "source_type": item.get("source_type", ""),
        "label": item.get("section") or item.get("title") or item.get("source_type", ""),
        "page": item.get("page"),
        "score": item.get("score", 0.0),
        "confidence": item.get("confidence", ""),
        "text": item.get("text", ""),
        "metadata": item.get("metadata", {}),
    }


def claim_scores(audit_claim: dict[str, Any], calibration_claim: dict[str, Any]) -> dict[str, float]:
    lifecycle = calibration_claim.get("lifecycle_robustness", {})
    signal_scores = lifecycle.get("signal_scores", {})
    rebuttal_robustness = signal_scores.get("rebuttal_robustness")
    rebuttal_resolution = 1.0 - float(rebuttal_robustness) if rebuttal_robustness is not None else proxy_rebuttal_resolution_score(audit_claim)
    return {
        "grounding": round_score(signal_scores.get("grounding", 1.0 if clean_text(audit_claim.get("source_sentence", "")) else 0.0)),
        "specificity": round_score(signal_scores.get("specificity", normalize_score(audit_claim.get("specificity_score", audit_claim.get("specificity")), max_value=100))),
        "evidence_support": round_score(normalize_score(audit_claim.get("support_score", audit_claim.get("evidence_support")), max_value=100)),
        "consensus": round_score(signal_scores.get("consensus", 0.0)),
        "rebuttal_resolution": round_score(rebuttal_resolution),
        "lifecycle_robustness": round_score(lifecycle.get("score", 0.0)),
        "reviewer_reliability": round_score(calibration_claim.get("review_reliability_score", 0.0)),
    }


def score_explanations(audit_claim: dict[str, Any], calibration_claim: dict[str, Any]) -> dict[str, str]:
    lifecycle = calibration_claim.get("lifecycle_robustness", {})
    return {
        "grounding": "Claim has a source sentence in the original review." if audit_claim.get("source_sentence") else "No original review source sentence was recorded.",
        "specificity": "Specificity is normalized from claim extraction / reviewer calibration.",
        "evidence_support": "Evidence support is normalized from the audit judge support score or rule baseline.",
        "consensus": calibration_claim.get("consensus", {}).get("label", "No inter-reviewer consensus signal available."),
        "rebuttal_resolution": calibration_claim.get("rebuttal_resolution", {}).get("label", "No author rebuttal match available."),
        "lifecycle_robustness": ", ".join(lifecycle.get("supporting_factors", [])) or "No strong lifecycle support factors recorded.",
    }


def derive_rebuttal_guidance(
    audit_claim: dict[str, Any],
    calibration_claim: dict[str, Any],
    scores: dict[str, float],
    evidence_chain: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    original = audit_claim.get("rebuttal_guidance") or {}
    priority = normalize_priority(original.get("priority", "medium"))
    strategy = normalize_strategy(original.get("strategy", "cite_existing_evidence"))
    risks = list(original.get("risks_to_avoid", []))
    evidence_to_cite = list(original.get("evidence_to_cite", []))

    if scores["grounding"] <= 0.0:
        priority = stronger_priority(priority, "medium")
        strategy = "clarify_misunderstanding"
        risks.append("Do not overstate reviewer error without quoting the review and manuscript evidence.")
    elif scores["lifecycle_robustness"] >= 0.72:
        priority = stronger_priority(priority, "must")
        strategy = "acknowledge_and_fix" if audit_claim.get("claim_type") in {"ablation", "experiment", "baseline"} else "cite_existing_evidence"
        risks.append("Do not dismiss this point; it is supported by lifecycle signals.")

    if scores["evidence_support"] <= 0.35 and scores["grounding"] > 0:
        priority = stronger_priority(priority, "high")
        strategy = "clarify_misunderstanding"
        risks.append("Avoid sounding defensive; explain the exact mismatch between the claim and evidence.")

    if scores["rebuttal_resolution"] >= 0.85:
        priority = "low"
        strategy = "de_emphasize"
        risks.append("Do not spend too much rebuttal budget on a point already resolved.")

    if calibration_claim.get("meta_review_uptake", {}).get("label") == "survived":
        priority = stronger_priority(priority, "must")
        risks.append("AC/meta-review appears to have adopted this concern.")

    if audit_claim.get("requires_external_knowledge") or evidence_chain.get("external"):
        priority = stronger_priority(priority, "high")
        strategy = "cite_existing_evidence"
        evidence_to_cite.extend(record.get("label") or record.get("text", "")[:80] for record in evidence_chain.get("external", [])[:2])
        risks.append("Cite external references or venue norms only when they directly support the response.")

    if not evidence_to_cite:
        evidence_to_cite.extend(record.get("label") or record.get("text", "")[:80] for record in evidence_chain.get("manuscript", [])[:2])

    return {
        "priority": priority,
        "strategy": strategy,
        "suggested_response": original.get("suggested_response") or suggested_response(audit_claim, strategy),
        "evidence_to_cite": dedupe_text(evidence_to_cite),
        "risks_to_avoid": dedupe_text(risks),
    }


def suggested_response(claim: dict[str, Any], strategy: str) -> str:
    if strategy == "acknowledge_and_fix":
        return "Acknowledge the concern, state the concrete revision or experiment, and cite the strongest supporting evidence."
    if strategy == "clarify_misunderstanding":
        return "Clarify the mismatch between the reviewer claim and the manuscript evidence, using a neutral tone and exact citations."
    if strategy == "add_experiment":
        return "State the additional experiment or ablation that can be added, and explain what claim it tests."
    if strategy == "de_emphasize":
        return "Answer briefly and avoid spending too much rebuttal space unless the AC also raises this point."
    return "Use the strongest available evidence to answer this reviewer point directly."


def build_evidence_chain_benchmark(
    audit_result: dict[str, Any],
    *,
    reviewer_calibration: dict[str, Any] | None = None,
    paper_limit: int = 50,
    claims_per_paper: int = 8,
    sample_size: int = 300,
) -> dict[str, Any]:
    paper_ids = []
    for audit in audit_result.get("audits", []):
        paper_id = audit.get("paper_id", "")
        if paper_id and paper_id not in paper_ids:
            paper_ids.append(paper_id)
    selected_ids = paper_ids[: max(0, paper_limit)]
    items = []
    for paper_id in selected_ids:
        demo = build_evidence_chain_demo(audit_result, reviewer_calibration=reviewer_calibration, paper_id=paper_id)
        paper_claims = [
            (reviewer, claim)
            for reviewer in demo.get("reviewers", [])
            for claim in reviewer.get("claims", [])
        ][: max(0, claims_per_paper)]
        for reviewer, claim in paper_claims:
            items.append(benchmark_item(demo["paper"], reviewer, claim))
            if len(items) >= sample_size:
                break
        if len(items) >= sample_size:
            break
    return {
        "schema_version": EVIDENCE_CHAIN_BENCHMARK_VERSION,
        "summary": {
            "paper_count": len(selected_ids),
            "item_count": len(items),
            "variant_count": 3,
            "priority_counts": dict(Counter(item["expected"]["recommended_action"] for item in items)),
            "claim_type_counts": dict(Counter(item["claim_type"] for item in items)),
        },
        "items": items,
    }


def build_evidence_chain_benchmark_from_calibration(
    reviewer_calibration: dict[str, Any],
    *,
    normalized_dataset: dict[str, Any] | None = None,
    paper_limit: int = 50,
    claims_per_paper: int = 5,
    sample_size: int = 150,
) -> dict[str, Any]:
    paper_index = index_normalized_papers(normalized_dataset or {})
    selected_papers = list(reviewer_calibration.get("papers", []))[: max(0, paper_limit)]
    items = []
    for calibration_paper in selected_papers:
        paper = calibration_paper_metadata(calibration_paper, paper_index)
        paper_claims = []
        for reviewer_index, review in enumerate(calibration_paper.get("reviews", []), start=1):
            reviewer = calibration_reviewer_payload(review, reviewer_index)
            for claim_index, calibration_claim in enumerate(review.get("claims", []), start=1):
                claim = frontend_claim_from_calibration(review, calibration_claim, claim_index)
                paper_claims.append((reviewer, claim))
        paper_claims.sort(key=lambda row: claim_sort_key(row[1]))
        for reviewer, claim in paper_claims[: max(0, claims_per_paper)]:
            items.append(benchmark_item(paper, reviewer, claim))
            if len(items) >= sample_size:
                break
        if len(items) >= sample_size:
            break
    return {
        "schema_version": EVIDENCE_CHAIN_BENCHMARK_VERSION,
        "source": {
            "mode": "reviewer_calibration",
            "reviewer_calibration_version": reviewer_calibration.get("calibration_version", ""),
            "normalized_dataset": (normalized_dataset or {}).get("dataset", ""),
        },
        "summary": {
            "paper_count": len({item["paper"].get("paper_id", "") for item in items}),
            "available_paper_count": len(selected_papers),
            "item_count": len(items),
            "variant_count": 3,
            "priority_counts": dict(Counter(item["expected"]["recommended_action"] for item in items)),
            "claim_type_counts": dict(Counter(item["claim_type"] for item in items)),
            "limitations": [
                "Derived from reviewer calibration, so manuscript and external evidence coverage may be sparse.",
                "Best used for lifecycle, rebuttal, consensus, and meta-review annotation before full PDF evidence expansion.",
            ],
        },
        "items": items,
    }


def frontend_claim_from_calibration(
    review: dict[str, Any],
    calibration_claim: dict[str, Any],
    claim_index: int,
) -> dict[str, Any]:
    audit_claim = {
        "claim_id": calibration_claim.get("claim_id") or f"{review.get('review_id', 'review')}:claim-{claim_index}",
        "claim_text": calibration_claim.get("claim_text", ""),
        "source_sentence": calibration_claim.get("source_sentence", ""),
        "claim_type": calibration_claim.get("claim_type", ""),
        "importance": calibration_claim.get("importance", ""),
        "specificity_score": calibration_claim.get("specificity_score", 0.0),
        "stance": calibration_claim.get("stance", ""),
        "verdict": calibration_claim.get("verdict", ""),
        "evidence": [],
    }
    scores = claim_scores(audit_claim, calibration_claim)
    scores["reviewer_reliability"] = round_score(
        review.get("llm_calibrated_review_reliability_score") or review.get("review_reliability_score")
    )
    evidence_chain = build_evidence_chain(audit_claim, calibration_claim)
    guidance = derive_rebuttal_guidance(audit_claim, calibration_claim, scores, evidence_chain)
    return {
        "claim_id": audit_claim["claim_id"],
        "claim_index": claim_index,
        "claim_text": audit_claim["claim_text"],
        "source_sentence": audit_claim["source_sentence"],
        "claim_type": audit_claim["claim_type"],
        "importance": audit_claim["importance"],
        "stance": audit_claim["stance"],
        "verdict": audit_claim["verdict"],
        "audit_confidence": "",
        "scores": scores,
        "score_explanations": score_explanations(audit_claim, calibration_claim),
        "evidence_chain": evidence_chain,
        "rebuttal_guidance": guidance,
        "system_judgment": {
            "second_opinion_take": "",
            "reasoning_summary": "Calibration-derived lifecycle evidence chain.",
            "issue_flags": [],
            "requires_external_knowledge": False,
            "requires_human_expert": False,
        },
    }


def calibration_reviewer_payload(review: dict[str, Any], reviewer_index: int) -> dict[str, Any]:
    return {
        "review_id": review.get("review_id", f"review-{reviewer_index}"),
        "display_id": f"R{reviewer_index}",
        "rating": review.get("rating_raw") or review.get("rating_normalized"),
        "confidence": review.get("confidence_raw") or review.get("confidence_normalized"),
        "review_reliability_score": round_score(
            review.get("llm_calibrated_review_reliability_score") or review.get("review_reliability_score")
        ),
    }


def calibration_paper_metadata(calibration_paper: dict[str, Any], paper_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    paper_id = calibration_paper.get("paper_id", "")
    source = paper_index.get(paper_id, {})
    return {
        "paper_id": paper_id,
        "title": source.get("title", ""),
        "abstract": source.get("abstract", ""),
        "venue": source.get("venue", "ICLR"),
        "year": source.get("year", 2024),
        "decision": source.get("decision", ""),
    }


def index_normalized_papers(dataset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {paper.get("paper_id", ""): paper for paper in dataset.get("papers", []) if paper.get("paper_id")}


def benchmark_item(paper: dict[str, Any], reviewer: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    base = {
        "paper": paper,
        "review_id": reviewer.get("review_id", ""),
        "claim_id": claim.get("claim_id", ""),
        "claim_text": claim.get("claim_text", ""),
        "source_sentence": claim.get("source_sentence", ""),
        "claim_type": claim.get("claim_type", ""),
        "importance": claim.get("importance", ""),
    }
    return {
        "task_id": f"{paper.get('paper_id', '')}:{reviewer.get('review_id', '')}:{claim.get('claim_id', '')}",
        **base,
        "variants": {
            "review_only": {
                **base,
            },
            "review_manuscript": {
                **base,
                "manuscript_evidence": claim.get("evidence_chain", {}).get("manuscript", []),
            },
            "full_evidence_chain": {
                **base,
                "rating": reviewer.get("rating"),
                "confidence": reviewer.get("confidence"),
                "scores": claim.get("scores", {}),
                "evidence_chain": claim.get("evidence_chain", {}),
                "rebuttal_guidance": claim.get("rebuttal_guidance", {}),
            },
        },
        "expected": {
            "stance": claim.get("stance", ""),
            "evidence_support_bucket": score_bucket(claim.get("scores", {}).get("evidence_support", 0.0)),
            "rebuttal_resolution_bucket": score_bucket(claim.get("scores", {}).get("rebuttal_resolution", 0.0)),
            "lifecycle_robustness_bucket": score_bucket(claim.get("scores", {}).get("lifecycle_robustness", 0.0)),
            "recommended_action": priority_to_action(claim.get("rebuttal_guidance", {}).get("priority", "medium")),
        },
    }


def build_benchmark_validation_report(benchmark: dict[str, Any]) -> dict[str, Any]:
    items = benchmark.get("items", [])
    variant_names = ("review_only", "review_manuscript", "full_evidence_chain")
    summary = {
        "paper_count": benchmark.get("summary", {}).get("paper_count", 0),
        "item_count": len(items),
        "variant_count": len(variant_names),
        "variants": {},
    }
    for variant in variant_names:
        coverage = []
        for item in items:
            payload = item.get("variants", {}).get(variant, {})
            coverage.append(
                {
                    "has_manuscript": bool(payload.get("manuscript_evidence") or payload.get("evidence_chain", {}).get("manuscript")),
                    "has_external": bool(payload.get("evidence_chain", {}).get("external")),
                    "has_rebuttal": bool(payload.get("evidence_chain", {}).get("rebuttal")),
                    "has_scores": bool(payload.get("scores")),
                }
            )
        summary["variants"][variant] = {
            "manuscript_evidence_coverage": mean_bool(row["has_manuscript"] for row in coverage),
            "external_evidence_coverage": mean_bool(row["has_external"] for row in coverage),
            "rebuttal_evidence_coverage": mean_bool(row["has_rebuttal"] for row in coverage),
            "score_coverage": mean_bool(row["has_scores"] for row in coverage),
        }
    return {
        "schema_version": "evidence-chain-benchmark-validation-v0.1",
        "summary": summary,
        "notes": list(benchmark.get("summary", {}).get("limitations", [])) + [
            "This v0 report validates benchmark packet coverage. Accuracy fields are filled after expert or LLM labels are compared.",
            "Expected labels are proxy labels derived from the current evidence-chain system, not gold labels.",
        ],
    }


def build_pseudo_expert_labels(tasks: list[dict[str, Any]], *, annotator_id: str = "pseudo-expert:v0.1") -> list[dict[str, Any]]:
    labels = []
    for task in tasks:
        if task.get("task_type") != "evidence_chain_quality":
            continue
        labels.append(
            {
                "annotation_id": f"ann_{task.get('task_id', '')}_{annotator_id.replace(':', '_')}",
                "task_id": task.get("task_id", ""),
                "run_id": task.get("run_id", ""),
                "task_type": task.get("task_type", ""),
                "annotator_type": "llm",
                "annotator_id": annotator_id,
                "label_schema_version": "annotation-label-v0.1",
                "labels": pseudo_expert_label_payload(task),
                "notes": "Rule-based pseudo-expert label derived from evidence-chain signals for v0 calibration.",
                "created_at": "2026-05-29T00:00:00+00:00",
                "llm_label_visible": False,
                "provenance": {
                    "pseudo_expert_version": EVIDENCE_CHAIN_PSEUDO_EXPERT_VERSION,
                    "input_task_version": task.get("provenance", {}).get("annotation_task_version", ""),
                },
            }
        )
    return labels


def build_pseudo_expert_report(tasks: list[dict[str, Any]], labels: list[dict[str, Any]]) -> dict[str, Any]:
    task_by_id = {task.get("task_id", ""): task for task in tasks}
    rows = []
    field_matches = Counter()
    field_totals = Counter()
    for label in labels:
        task = task_by_id.get(label.get("task_id", ""), {})
        expected = system_expected_label_payload(task)
        actual = label.get("labels", {})
        row_matches = {}
        for field, expected_value in expected.items():
            field_totals[field] += 1
            match = actual.get(field) == expected_value
            row_matches[field] = match
            if match:
                field_matches[field] += 1
        rows.append(
            {
                "task_id": label.get("task_id", ""),
                "paper_id": task.get("paper_id", ""),
                "review_id": task.get("review_id", ""),
                "claim_id": task.get("claim_id", ""),
                "system_expected": expected,
                "pseudo_expert": actual,
                "field_matches": row_matches,
            }
        )
    field_match_rates = {
        field: round(field_matches[field] / total, 4) if total else 0.0
        for field, total in sorted(field_totals.items())
    }
    exact_matches = sum(1 for row in rows if all(row.get("field_matches", {}).values()))
    return {
        "schema_version": "evidence-chain-pseudo-expert-report-v0.1",
        "pseudo_expert_version": EVIDENCE_CHAIN_PSEUDO_EXPERT_VERSION,
        "summary": {
            "task_count": len(tasks),
            "label_count": len(labels),
            "exact_match_count": exact_matches,
            "exact_match_rate": round(exact_matches / len(rows), 4) if rows else 0.0,
            "field_match_rates": field_match_rates,
            "recommended_action_counts": dict(Counter(label.get("labels", {}).get("recommended_action", "") for label in labels)),
            "rebuttal_address_counts": dict(Counter(label.get("labels", {}).get("rebuttal_addresses_claim", "") for label in labels)),
            "evidence_support_counts": dict(Counter(label.get("labels", {}).get("evidence_supports_claim", "") for label in labels)),
        },
        "rows": rows,
    }


def pseudo_expert_label_payload(task: dict[str, Any]) -> dict[str, str]:
    context = task.get("context", {})
    output = task.get("system_output", {})
    scores = output.get("scores", {})
    guidance = output.get("rebuttal_guidance", {})
    chain = context.get("evidence_chain", {})
    source_sentence = context.get("source_sentence", "")
    claim_text = context.get("claim_text", "")
    return {
        "claim_extraction_correct": "yes" if clean_text(claim_text) and clean_text(source_sentence) else "partial",
        "claim_grounded": triage_from_score(scores.get("grounding", 0.0)),
        "evidence_supports_claim": evidence_support_label(scores.get("evidence_support", 0.0), chain),
        "claim_importance": importance_label(output.get("importance", "")),
        "rebuttal_addresses_claim": rebuttal_address_label(scores.get("rebuttal_resolution", 0.0), chain),
        "recommended_action": action_label(guidance, scores, output, chain),
        "expert_confidence": expert_confidence_label(scores, chain),
    }


def system_expected_label_payload(task: dict[str, Any]) -> dict[str, str]:
    output = task.get("system_output", {})
    scores = output.get("scores", {})
    guidance = output.get("rebuttal_guidance", {})
    priority = normalize_priority(guidance.get("priority", "medium"))
    return {
        "claim_extraction_correct": "yes" if scores.get("grounding", 0.0) >= 0.95 else "partial",
        "claim_grounded": triage_from_score(scores.get("grounding", 0.0)),
        "evidence_supports_claim": system_evidence_support_label(output),
        "claim_importance": importance_label(output.get("importance", "")),
        "rebuttal_addresses_claim": system_rebuttal_address_label(priority),
        "recommended_action": priority_to_action(priority),
        "expert_confidence": "high" if scores.get("grounding", 0.0) >= 0.85 and scores.get("evidence_support", 0.0) >= 0.65 else "medium",
    }


def system_evidence_support_label(output: dict[str, Any]) -> str:
    stance = str(output.get("stance", "")).lower()
    verdict = str(output.get("verdict", "")).lower()
    if stance in {"strongly_agree", "agree"} or verdict == "supported":
        return "supports"
    if stance == "mixed" or verdict == "partially_supported":
        return "mixed"
    if stance in {"disagree", "strongly_disagree"} or verdict == "possibly_contradicted":
        return "contradicts"
    return "insufficient"


def system_rebuttal_address_label(priority: str) -> str:
    if priority == "low":
        return "resolved"
    if priority == "medium":
        return "partially_addressed"
    if priority == "high":
        return "generic_or_unclear"
    return "not_addressed"


def triage_from_score(value: Any) -> str:
    score = round_score(value)
    if score >= 0.85:
        return "yes"
    if score >= 0.35:
        return "partial"
    return "no"


def evidence_support_label(value: Any, chain: dict[str, Any]) -> str:
    score = round_score(value)
    if score >= 0.68:
        return "supports"
    if score >= 0.35:
        return "mixed"
    if chain.get("manuscript"):
        return "contradicts"
    return "insufficient"


def importance_label(value: Any) -> str:
    text = str(value or "").lower()
    if text == "major":
        return "high"
    if text in {"medium", "minor"}:
        return "medium"
    return "low"


def rebuttal_address_label(value: Any, chain: dict[str, Any]) -> str:
    score = round_score(value)
    if score >= 0.75:
        return "resolved"
    if score >= 0.45:
        return "partially_addressed"
    if chain.get("rebuttal"):
        return "generic_or_unclear"
    return "not_addressed"


def action_label(guidance: dict[str, Any], scores: dict[str, Any], output: dict[str, Any], chain: dict[str, Any]) -> str:
    priority = normalize_priority(guidance.get("priority", "medium"))
    strategy = normalize_strategy(guidance.get("strategy", ""))
    if priority == "must":
        return "must_address"
    if priority == "low":
        return "deprioritize"
    if strategy == "clarify_misunderstanding":
        return "clarify"
    if output.get("system_judgment", {}).get("requires_external_knowledge") or chain.get("external"):
        return "provide_evidence"
    if priority == "high":
        return "provide_evidence"
    return "clarify"


def expert_confidence_label(scores: dict[str, Any], chain: dict[str, Any]) -> str:
    has_evidence = bool(chain.get("manuscript") or chain.get("external"))
    if scores.get("grounding", 0.0) >= 0.85 and has_evidence:
        return "high"
    if scores.get("grounding", 0.0) >= 0.35:
        return "medium"
    return "low"


def write_pseudo_expert_markdown(report: dict[str, Any], path: str | Path) -> None:
    summary = report.get("summary", {})
    lines = [
        "# Evidence Chain Pseudo-Expert Calibration",
        "",
        f"- Tasks: {summary.get('task_count', 0)}",
        f"- Labels: {summary.get('label_count', 0)}",
        f"- Exact match rate: {summary.get('exact_match_rate', 0.0):.1%}",
        "",
        "## Field Match Rates",
        "",
        "| Field | Match rate |",
        "| --- | ---: |",
    ]
    for field, rate in summary.get("field_match_rates", {}).items():
        lines.append(f"| {field} | {rate:.1%} |")
    lines.extend(["", "## Label Counts", ""])
    for key in ("recommended_action_counts", "rebuttal_address_counts", "evidence_support_counts"):
        lines.append(f"- `{key}`: `{json.dumps(summary.get(key, {}), ensure_ascii=False, sort_keys=True)}`")
    lines.extend(["", "## Example Disagreements", ""])
    disagreements = [
        row for row in report.get("rows", [])
        if not all(row.get("field_matches", {}).values())
    ][:10]
    if not disagreements:
        lines.append("No disagreements.")
    for row in disagreements:
        lines.append(
            f"- `{row.get('task_id', '')}` system={json.dumps(row.get('system_expected', {}), ensure_ascii=False, sort_keys=True)} "
            f"pseudo={json.dumps(row.get('pseudo_expert', {}), ensure_ascii=False, sort_keys=True)}"
        )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_validation_story(
    demo: dict[str, Any],
    benchmark: dict[str, Any],
    pseudo_report: dict[str, Any],
) -> str:
    demo_summary = demo.get("summary", {})
    benchmark_summary = benchmark.get("summary", {})
    benchmark_source = benchmark.get("source", {}).get("mode", "audit")
    pseudo_summary = pseudo_report.get("summary", {})
    priority_counts = demo_summary.get("priority_counts", {})
    field_rates = pseudo_summary.get("field_match_rates", {})
    benchmark_scope = "reviewer-calibration-derived papers" if benchmark_source == "reviewer_calibration" else "available audited papers"
    benchmark_limitation = (
        "This calibration-derived benchmark is strong for lifecycle, rebuttal, consensus, and meta-review validation; "
        "manuscript/external evidence ablations still require more PDF-backed audit runs."
        if benchmark_source == "reviewer_calibration"
        else "This is enough to test the benchmark machinery and small-sample trends. Reaching 30-50 papers requires running the audit pipeline on more papers with manuscript evidence."
    )
    lines = [
        "# Evidence Chain Validation Story",
        "",
        "## Product Demo Readiness",
        "",
        (
            f"The current evidence-chain demo covers {demo_summary.get('review_count', 0)} reviews and "
            f"{demo_summary.get('claim_count', 0)} reviewer claims for one representative ICLR paper. "
            f"{demo_summary.get('high_priority_claim_count', 0)} claims are high-priority or must-address rebuttal items."
        ),
        "",
        f"- Priority mix: `{json.dumps(priority_counts, ensure_ascii=False, sort_keys=True)}`",
        f"- Mean reviewer reliability: {demo_summary.get('mean_reviewer_reliability', 0.0):.1%}",
        f"- Mean lifecycle robustness: {demo_summary.get('mean_lifecycle_robustness', 0.0):.1%}",
        "",
        "## Benchmark Status",
        "",
        (
            f"The current benchmark packet contains {benchmark_summary.get('item_count', 0)} claim items "
            f"across {benchmark_summary.get('paper_count', 0)} {benchmark_scope}, with three ablation views: "
            "`review_only`, `review_manuscript`, and `full_evidence_chain`."
        ),
        "",
        benchmark_limitation,
        "",
        "## Pseudo-Expert Calibration",
        "",
        f"- Pseudo-expert labels: {pseudo_summary.get('label_count', 0)}",
        f"- Exact agreement with system-derived expected labels: {pseudo_summary.get('exact_match_rate', 0.0):.1%}",
        f"- Recommended-action agreement: {field_rates.get('recommended_action', 0.0):.1%}",
        f"- Rebuttal-resolution agreement: {field_rates.get('rebuttal_addresses_claim', 0.0):.1%}",
        f"- Evidence-support agreement: {field_rates.get('evidence_supports_claim', 0.0):.1%}",
        "",
        "## Interpretation",
        "",
        "- The UI now supports the product story: identify dangerous reviewer claims, explain the evidence chain, and recommend response strategy.",
        "- The benchmark packet now makes evidence-chain ablations explicit, so future LLM or human labels can measure whether added evidence improves judgment.",
        "- Pseudo-expert labels are not gold labels; they are a calibration harness and sanity check before spending money on experts.",
        "- Current pseudo-expert disagreement on evidence support is useful: it shows where stance-based system outputs and evidence-score-based review differ, which is exactly the calibration target for expert labels.",
        "- The next real validation step is to replace pseudo-expert labels with 200-300 human/expert labels on the same schema.",
        "",
        "## Recommended Investor Demo Script",
        "",
        "1. Open the evidence-chain reader and select the demo paper.",
        "2. Show the top high-priority claim and its score breakdown.",
        "3. Expand the evidence chain: reviewer wording, manuscript evidence, rebuttal, consensus, and meta-review uptake.",
        "4. Switch to the rebuttal workspace and show how SecondOpinion prioritizes what the author should answer first.",
        "5. Close with the validation path: benchmark ablations and expert labels.",
    ]
    return "\n".join(lines) + "\n"


def write_validation_story(path: str | Path, demo: dict[str, Any], benchmark: dict[str, Any], pseudo_report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_validation_story(demo, benchmark, pseudo_report), encoding="utf-8")


def write_benchmark_markdown(report: dict[str, Any], path: str | Path) -> None:
    summary = report.get("summary", {})
    lines = [
        "# Evidence Chain Benchmark Validation",
        "",
        f"- Papers: {summary.get('paper_count', 0)}",
        f"- Items: {summary.get('item_count', 0)}",
        f"- Variants: {summary.get('variant_count', 0)}",
        "",
        "| Variant | Manuscript coverage | External coverage | Rebuttal coverage | Score coverage |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for variant, row in summary.get("variants", {}).items():
        lines.append(
            f"| {variant} | {row.get('manuscript_evidence_coverage', 0.0):.1%} | "
            f"{row.get('external_evidence_coverage', 0.0):.1%} | "
            f"{row.get('rebuttal_evidence_coverage', 0.0):.1%} | "
            f"{row.get('score_coverage', 0.0):.1%} |"
        )
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in report.get("notes", []))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def index_calibration_reviews(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed = {}
    for paper in report.get("papers", []):
        for review in paper.get("reviews", []):
            indexed[(paper.get("paper_id", ""), review.get("review_id", ""))] = review
    return indexed


def match_calibration_claim(audit_claim: dict[str, Any], calibration_claims: list[dict[str, Any]], index: int) -> dict[str, Any]:
    claim_text = clean_text(audit_claim.get("claim_text", "")).lower()
    source = clean_text(audit_claim.get("source_sentence", "")).lower()
    for candidate in calibration_claims:
        if clean_text(candidate.get("claim_text", "")).lower() == claim_text:
            return candidate
        if source and clean_text(candidate.get("source_sentence", "")).lower() == source:
            return candidate
    if index < len(calibration_claims):
        return calibration_claims[index]
    return {}


def claim_sort_key(claim: dict[str, Any]) -> tuple[int, float]:
    priority = claim.get("rebuttal_guidance", {}).get("priority", "medium")
    robustness = float(claim.get("scores", {}).get("lifecycle_robustness", 0.0) or 0.0)
    return (-PRIORITY_ORDER.get(priority, 2), -robustness)


def normalize_score(value: Any, *, max_value: float) -> float:
    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric <= 1.0:
        return max(0.0, min(1.0, numeric))
    if max_value == 100 and numeric <= 4.0:
        return max(0.0, min(1.0, numeric / 4.0))
    return max(0.0, min(1.0, numeric / max_value))


def round_score(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value or 0.0))), 4)
    except (TypeError, ValueError):
        return 0.0


def proxy_rebuttal_resolution_score(claim: dict[str, Any]) -> float:
    guidance = claim.get("rebuttal_guidance") or {}
    if guidance.get("priority") == "low":
        return 0.75
    if claim.get("verdict") == "possibly_contradicted":
        return 0.35
    return 0.0


def normalize_priority(value: Any) -> str:
    text = str(value or "medium").lower()
    if text in PRIORITY_ORDER:
        return text
    return "medium"


def stronger_priority(left: str, right: str) -> str:
    return left if PRIORITY_ORDER.get(left, 0) >= PRIORITY_ORDER.get(right, 0) else right


def normalize_strategy(value: Any) -> str:
    text = str(value or "").lower()
    allowed = {"acknowledge_and_fix", "clarify_misunderstanding", "cite_existing_evidence", "add_experiment", "de_emphasize"}
    if text in allowed:
        return text
    if text in {"acknowledge_and_clarify", "concede_and_fix"}:
        return "acknowledge_and_fix"
    return "cite_existing_evidence"


def dedupe_text(values: list[Any]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def mean_score(values: Any) -> float:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return 0.0
    return round(sum(numeric) / len(numeric), 4)


def mean_bool(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(1 for item in items if item) / len(items), 4)


def score_bucket(value: Any) -> str:
    score = round_score(value)
    if score >= 0.72:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def priority_to_action(priority: str) -> str:
    if priority == "must":
        return "must_address"
    if priority == "high":
        return "provide_evidence"
    if priority == "low":
        return "deprioritize"
    return "clarify"


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
