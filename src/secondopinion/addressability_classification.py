from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .llm_client import LLMClientError, OpenAIChatClient
from .model_config import DEFAULT_CHEAP_MODEL


ADDRESSABILITY_LABEL_VERSION = "addressability-label-v0.1"
ADDRESSABILITY_REPORT_VERSION = "addressability-report-v0.1"
DEFAULT_BASELINE_LABELS = "data/validation/addressability_test4_llm_labels_v0.1.jsonl"
ADDRESSABILITY_LABELS = (
    "answerable_fixable",
    "structurally_unresolvable",
    "requires_concession",
    "unclear",
)
CONFIDENCE_LABELS = ("high", "medium", "low")
TARGET_RESPONSES = {"not_addressed", "generic_or_unclear"}
TARGET_EFFECTS = {"does_not_address", "partially_addresses"}
CONTROL_EFFECTS = {"resolved_or_weakened"}
CONTROL_RESPONSES = {"specifically_addressed"}
NOT_FIXABLE = {"structurally_unresolvable", "requires_concession", "unclear"}


def build_addressability_items(
    candidates: list[dict[str, Any]],
    reviewer_calibration: dict[str, Any],
    normalized_papers: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    items_by_id: dict[str, dict[str, Any]] = {}
    for task in candidates:
        item = item_from_candidate(task, normalized_papers, roles=["main"])
        items_by_id[item["claim_id"]] = item

    for record in iter_claim_records(reviewer_calibration):
        claim = record["claim"]
        llm = current_llm_rebuttal(claim)
        response = llm.get("rebuttal_response_label", "")
        effect = llm.get("rebuttal_effect_on_claim", "")
        if effect not in CONTROL_EFFECTS and response not in CONTROL_RESPONSES:
            continue
        claim_id = record_key(record)
        roles = []
        if effect in CONTROL_EFFECTS:
            roles.append("control_resolved_or_weakened")
        if response in CONTROL_RESPONSES:
            roles.append("control_specifically_addressed")
        if claim_id in items_by_id:
            items_by_id[claim_id]["roles"] = sorted(set(items_by_id[claim_id]["roles"]) | set(roles))
            continue
        item = item_from_claim_record(record, normalized_papers, roles=roles)
        items_by_id[item["claim_id"]] = item
    return sorted(items_by_id.values(), key=lambda item: item["claim_id"])


def item_from_candidate(
    task: dict[str, Any],
    normalized_papers: dict[str, dict[str, Any]],
    *,
    roles: list[str],
) -> dict[str, Any]:
    paper = normalized_papers.get(task.get("paper_id", ""), {})
    context = paper_context(paper, fallback_title=task.get("title", ""))
    return {
        "claim_id": task.get("task_id", ""),
        "paper_id": task.get("paper_id", ""),
        "review_id": task.get("review_id", ""),
        "claim_index": task.get("claim_index", 0),
        "reviewer_claim": task.get("reviewer_claim", ""),
        "title": context["title"],
        "paper_context": context["text"],
        "had_paper_context": context["has_abstract"],
        "context_source": context["source"],
        "importance_proxy": task.get("importance_proxy", ""),
        "current_rebuttal_response_label": task.get("current_rebuttal_response_label", ""),
        "current_rebuttal_effect_label": task.get("current_rebuttal_effect_label", ""),
        "roles": roles,
    }


def item_from_claim_record(
    record: dict[str, Any],
    normalized_papers: dict[str, dict[str, Any]],
    *,
    roles: list[str],
) -> dict[str, Any]:
    claim = record["claim"]
    llm = current_llm_rebuttal(claim)
    paper = normalized_papers.get(record.get("paper_id", ""), {})
    context = paper_context(paper, fallback_title=record.get("title", ""))
    return {
        "claim_id": record_key(record),
        "paper_id": record.get("paper_id", ""),
        "review_id": record.get("review_id", ""),
        "claim_index": record.get("claim_index", 0),
        "reviewer_claim": claim.get("claim_text", ""),
        "title": context["title"],
        "paper_context": context["text"],
        "had_paper_context": context["has_abstract"],
        "context_source": context["source"],
        "importance_proxy": claim.get("importance", ""),
        "current_rebuttal_response_label": llm.get("rebuttal_response_label", ""),
        "current_rebuttal_effect_label": llm.get("rebuttal_effect_on_claim", ""),
        "roles": roles,
    }


def classify_items(
    items: list[dict[str, Any]],
    *,
    llm_client: Any,
    model: str,
    prompt_variant: str = "main",
    prompt_version: str = "v0.1",
) -> list[dict[str, Any]]:
    labels = []
    for item in items:
        labels.append(
            classify_item(
                item,
                llm_client=llm_client,
                model=model,
                prompt_variant=prompt_variant,
                prompt_version=prompt_version,
            )
        )
    return labels


def classify_item(
    item: dict[str, Any],
    *,
    llm_client: Any,
    model: str,
    prompt_variant: str = "main",
    prompt_version: str = "v0.1",
) -> dict[str, Any]:
    payload = llm_client.complete_json(
        model=model,
        messages=addressability_messages(item, prompt_variant=prompt_variant, prompt_version=prompt_version),
        schema_name="concern_addressability_label",
        schema=addressability_schema(prompt_version=prompt_version),
    )
    label = {
        "claim_id": item["claim_id"],
        "paper_id": item["paper_id"],
        "review_id": item["review_id"],
        "claim_index": item["claim_index"],
        "label_schema_version": ADDRESSABILITY_LABEL_VERSION,
        "model": model,
        "prompt_variant": prompt_variant,
        "prompt_version": prompt_version,
        "addressability": payload.get("addressability", ""),
        "fixable": payload.get("addressability") == "answerable_fixable",
        "rationale": str(payload.get("rationale", "")),
        "confidence": payload.get("confidence", ""),
        "had_paper_context": bool(item.get("had_paper_context")),
        "context_source": item.get("context_source", ""),
        "roles": list(item.get("roles", [])),
        "importance_proxy": item.get("importance_proxy", ""),
        "current_rebuttal_response_label": item.get("current_rebuttal_response_label", ""),
        "current_rebuttal_effect_label": item.get("current_rebuttal_effect_label", ""),
    }
    errors = validate_label(label)
    if errors:
        raise ValueError(f"Invalid addressability label for {item['claim_id']}: {errors}")
    return label


def addressability_messages(
    item: dict[str, Any],
    *,
    prompt_variant: str = "main",
    prompt_version: str = "v0.1",
) -> list[dict[str, str]]:
    if prompt_version == "v0.2":
        return addressability_messages_v02(item, prompt_variant=prompt_variant)
    if prompt_variant == "self_consistency_reworded":
        system = (
            "You are an experienced ML/AI area chair. Classify one reviewer concern by whether it could be "
            "substantively addressed within an author rebuttal. Ignore any imagined actual rebuttal. Do not decide "
            "whether the reviewer is right; decide only the intrinsic addressability of the concern. Return JSON only."
        )
        user_intro = "Classify this concern using exactly one category."
    else:
        system = (
            "You are an expert ML/AI area chair. You will receive ONE reviewer concern about a paper, plus context "
            "on the paper's core contribution. Judge ONE thing only: what kind of concern it is with respect to "
            "whether it could, in principle, be substantively addressed in an author rebuttal. You are NOT judging "
            "whether any actual rebuttal resolved it. You are NOT judging whether the concern is correct. Judge only "
            "the concern's intrinsic addressability. Choose exactly one category and output JSON only."
        )
        user_intro = "Output JSON only."
    category_text = (
        "- answerable_fixable: could in principle be substantively addressed in a rebuttal, such as with an added "
        "experiment/result, clarifying explanation, missing detail, correcting a misreading, or pointing to overlooked "
        "existing content.\n"
        "- structurally_unresolvable: a holistic verdict/framing judgment no rebuttal text can resolve, such as "
        "novelty/incrementality, significance/impact, problem importance, or objections to the paper's basic approach "
        "or structure. At most the author can argue framing/scope.\n"
        "- requires_concession: a valid, concrete flaw/limitation that cannot be fixed in a rebuttal and is best "
        "handled by honest concession, acknowledging a limitation, or narrowing the claim.\n"
        "- unclear: not a substantive concern, or insufficient information."
    )
    return [
        {"role": "system", "content": f"{system}\n\nCategories:\n{category_text}"},
        {
            "role": "user",
            "content": (
                f"PAPER (core contribution / abstract):\n{item.get('paper_context', '')}\n\n"
                f"REVIEWER CONCERN:\n{item.get('reviewer_claim', '')}\n\n"
                f"{user_intro}"
            ),
        },
    ]


def addressability_messages_v02(item: dict[str, Any], *, prompt_variant: str = "main") -> list[dict[str, str]]:
    if prompt_variant == "self_consistency_reworded":
        system = (
            "You are an expert ML/AI area chair. Given one reviewer concern and the paper's core contribution, "
            "decide whether the concern is intrinsically addressable in an author rebuttal. Ignore any actual "
            "rebuttal and do not judge whether the concern is correct. Use unclear only when the concern text is "
            "too vague or garbled to classify. Output JSON only, with a one-sentence rationale first and the final "
            "field addressability matching that rationale."
        )
    else:
        system = (
            "You are an expert ML/AI area chair. You will receive ONE reviewer concern plus the paper's core "
            "contribution. Judge ONE thing only: whether the concern could, in principle, be substantively addressed "
            "in an author rebuttal. You are NOT judging whether any actual rebuttal resolved it, nor whether the "
            "concern is correct.\n"
            "Choose exactly one:\n\n"
            "answerable_fixable: could in principle be addressed in a rebuttal - added experiment/result, clarifying "
            "explanation, missing detail, correcting a misreading, or pointing to overlooked content. This INCLUDES "
            "all presentation issues: typos, grammar, figure/table/notation clarity, section or appendix placement, "
            "writing clarity - these are always fixable in revision.\n"
            "structurally_unresolvable: a substantive verdict about the contribution itself that no rebuttal text can "
            "resolve - novelty/incrementality, significance/impact/interest, \"the problem isn't important,\" or "
            "rejection of the basic approach/framing. Use ONLY for judgments about the worth/novelty/framing of the "
            "contribution; NEVER for presentation or missing-detail issues.\n"
            "requires_concession: a valid, concrete flaw best handled by honestly conceding / acknowledging a "
            "limitation / narrowing the claim.\n"
            "unclear: use ONLY when the concern text itself is too vague or garbled to tell what is asked, or there "
            "is genuinely insufficient information. Do NOT use as a hedge: if your reasoning concludes it could be "
            "addressed in a rebuttal, you MUST label answerable_fixable.\n\n"
            "Output JSON only, rationale (ONE sentence) FIRST, then addressability as the FINAL field. "
            "addressability MUST match your rationale's conclusion."
        )
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"PAPER (core contribution / abstract):\n{item.get('paper_context', '')}\n\n"
                f"REVIEWER CONCERN:\n{item.get('reviewer_claim', '')}\n\n"
                "Output JSON only."
            ),
        },
    ]


def addressability_schema(*, prompt_version: str = "v0.1") -> dict[str, Any]:
    if prompt_version == "v0.2":
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "rationale": {"type": "string"},
                "confidence": {"type": "string", "enum": list(CONFIDENCE_LABELS)},
                "addressability": {"type": "string", "enum": list(ADDRESSABILITY_LABELS)},
            },
            "required": ["rationale", "confidence", "addressability"],
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "addressability": {"type": "string", "enum": list(ADDRESSABILITY_LABELS)},
            "rationale": {"type": "string"},
            "confidence": {"type": "string", "enum": list(CONFIDENCE_LABELS)},
        },
        "required": ["addressability", "rationale", "confidence"],
    }


def build_addressability_report(
    items: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    *,
    self_consistency_labels: list[dict[str, Any]] | None = None,
    test_1b: dict[str, Any] | None = None,
    baseline_labels: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    labels_by_id = {label["claim_id"]: label for label in labels}
    main = [labels_by_id[item["claim_id"]] for item in items if "main" in item.get("roles", [])]
    controls_resolved = [
        labels_by_id[item["claim_id"]]
        for item in items
        if "control_resolved_or_weakened" in item.get("roles", [])
    ]
    controls_specific = [
        labels_by_id[item["claim_id"]]
        for item in items
        if "control_specifically_addressed" in item.get("roles", [])
    ]
    high_unresolved = [
        label
        for label in main
        if normalize_importance(label.get("importance_proxy", "")) == "high"
        and label.get("current_rebuttal_effect_label") in TARGET_EFFECTS
    ]
    return {
        "schema_version": ADDRESSABILITY_REPORT_VERSION,
        "summary": {
            "classified_unique_claim_count": len(labels),
            "main_claim_count": len(main),
            "control_resolved_or_weakened_count": len(controls_resolved),
            "control_specifically_addressed_count": len(controls_specific),
            "no_leakage_check": {
                "prompt_includes_rebuttal_text": False,
                "prompt_includes_existing_response_or_effect_labels": False,
                "prompt_includes_importance_proxy": False,
                "prompt_context": "title + abstract when available; title-only fallback flagged per item",
            },
            "paper_context_counts": dict(Counter("abstract" if label["had_paper_context"] else "title_only" for label in labels)),
        },
        "main_distribution": distribution(main),
        "main_fixable_split": fixable_split(main),
        "main_tri_state_split": tri_state_split(main),
        "main_determinate_split": determinate_split(main),
        "main_not_fixable_subtypes": not_fixable_subtypes(main),
        "addressability_by_importance_proxy": nested_counts(main, "addressability", "importance_proxy"),
        "addressability_by_effect": nested_counts(main, "addressability", "current_rebuttal_effect_label"),
        "addressability_by_response": nested_counts(main, "addressability", "current_rebuttal_response_label"),
        "headline_high_importance_unresolved": {
            "claim_count": len(high_unresolved),
            "distribution": distribution(high_unresolved),
            "fixable_split": fixable_split(high_unresolved),
            "tri_state_split": tri_state_split(high_unresolved),
            "determinate_split": determinate_split(high_unresolved),
            "not_fixable_subtypes": not_fixable_subtypes(high_unresolved),
        },
        "controls": {
            "resolved_or_weakened": {
                "claim_count": len(controls_resolved),
                "distribution": distribution(controls_resolved),
                "fixable_split": fixable_split(controls_resolved),
            },
            "specifically_addressed": {
                "claim_count": len(controls_specific),
                "distribution": distribution(controls_specific),
                "fixable_split": fixable_split(controls_specific),
            },
        },
        "self_consistency": summarize_self_consistency(labels, self_consistency_labels or []),
        "model_robustness_vs_baseline": compare_with_baseline(main, baseline_labels or []),
        "rationale_label_consistency_check": rationale_label_consistency_check(main),
        "test_1b_importance_resolution_independence": test_1b or {},
        "examples": {
            "not_fixable_high_importance_unresolved": example_labels(
                [label for label in high_unresolved if not label.get("fixable")]
            ),
            "fixable_high_importance_unresolved": example_labels(
                [label for label in high_unresolved if label.get("fixable")]
            ),
            "controls_not_fixable": example_labels([label for label in controls_specific if not label.get("fixable")]),
        },
        "labels": labels,
        "self_consistency_labels": self_consistency_labels or [],
    }


def summarize_self_consistency(
    main_labels: list[dict[str, Any]],
    self_labels: list[dict[str, Any]],
) -> dict[str, Any]:
    if not self_labels:
        return {"status": "not_run", "label_count": 0}
    main_by_id = {label["claim_id"]: label for label in main_labels}
    compared = [label for label in self_labels if label["claim_id"] in main_by_id]
    exact_matches = [
        label
        for label in compared
        if label.get("addressability") == main_by_id[label["claim_id"]].get("addressability")
    ]
    fixable_matches = [
        label
        for label in compared
        if label.get("fixable") == main_by_id[label["claim_id"]].get("fixable")
    ]
    by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for label in self_labels:
        by_claim[label["claim_id"]].append(label)
    unanimous_exact = sum(
        1 for labels in by_claim.values() if len({label.get("addressability") for label in labels}) == 1
    )
    unanimous_fixable = sum(1 for labels in by_claim.values() if len({label.get("fixable") for label in labels}) == 1)
    return {
        "status": "run",
        "claim_count": len(by_claim),
        "label_count": len(self_labels),
        "agreement_with_main_exact_count": len(exact_matches),
        "agreement_with_main_exact_rate": rate(len(exact_matches), len(compared)),
        "agreement_with_main_fixable_count": len(fixable_matches),
        "agreement_with_main_fixable_rate": rate(len(fixable_matches), len(compared)),
        "unanimous_exact_claim_count": unanimous_exact,
        "unanimous_exact_claim_rate": rate(unanimous_exact, len(by_claim)),
        "unanimous_fixable_claim_count": unanimous_fixable,
        "unanimous_fixable_claim_rate": rate(unanimous_fixable, len(by_claim)),
        "note": "Self-consistency used a reworded prompt variant because the default GPT-5 model path does not expose temperature controls in this client.",
    }


def compare_with_baseline(current_main: list[dict[str, Any]], baseline_labels: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_by_id = {label.get("claim_id", ""): label for label in baseline_labels if label.get("claim_id")}
    paired = [(label, baseline_by_id[label["claim_id"]]) for label in current_main if label["claim_id"] in baseline_by_id]
    if not paired:
        return {"status": "not_available", "paired_count": 0}
    baseline_states = [tri_state(old) for _, old in paired]
    current_states = [tri_state(new) for new, _ in paired]
    tri_matches = sum(1 for current, baseline in zip(current_states, baseline_states) if current == baseline)
    determinate_pairs = [
        (current, baseline)
        for current, baseline in zip(current_states, baseline_states)
        if current != "unclear" and baseline != "unclear"
    ]
    binary_matches = sum(1 for current, baseline in determinate_pairs if current == baseline)
    return {
        "status": "run",
        "paired_count": len(paired),
        "tri_state_agreement_count": tri_matches,
        "tri_state_agreement_rate": rate(tri_matches, len(paired)),
        "binary_determinate_pair_count": len(determinate_pairs),
        "binary_agreement_count": binary_matches,
        "binary_agreement_rate": rate(binary_matches, len(determinate_pairs)),
        "baseline_tri_state_counts": dict(Counter(baseline_states)),
        "current_tri_state_counts": dict(Counter(current_states)),
        "baseline_fixable_rate_all": rate(sum(1 for state in baseline_states if state == "fixable"), len(baseline_states)),
        "current_fixable_rate_all": rate(sum(1 for state in current_states if state == "fixable"), len(current_states)),
        "fixable_rate_delta_all": round(
            rate(sum(1 for state in current_states if state == "fixable"), len(current_states))
            - rate(sum(1 for state in baseline_states if state == "fixable"), len(baseline_states)),
            4,
        ),
        "baseline_fixable_rate_excluding_unclear": fixable_rate_excluding_unclear(baseline_states),
        "current_fixable_rate_excluding_unclear": fixable_rate_excluding_unclear(current_states),
        "fixable_rate_delta_excluding_unclear": round(
            fixable_rate_excluding_unclear(current_states) - fixable_rate_excluding_unclear(baseline_states),
            4,
        ),
    }


def rationale_label_consistency_check(labels: list[dict[str, Any]]) -> dict[str, Any]:
    mismatches = []
    for label in labels:
        mismatch_type = rationale_label_mismatch_type(label)
        if mismatch_type:
            mismatches.append({**label, "mismatch_type": mismatch_type})
    return {
        "checked_count": len(labels),
        "mismatch_count": len(mismatches),
        "mismatch_rate": rate(len(mismatches), len(labels)),
        "mismatch_type_counts": dict(Counter(item["mismatch_type"] for item in mismatches)),
        "examples": example_labels(mismatches, limit=12),
    }


def rationale_label_mismatch_type(label: dict[str, Any]) -> str:
    rationale = clean_text(label.get("rationale", "")).lower()
    addressability = label.get("addressability", "")
    suggests_fixable = any(
        phrase in rationale
        for phrase in (
            "answerable_fixable",
            "could be addressed",
            "can be addressed",
            "could be fixed",
            "can be fixed",
            "could be clarified",
            "can be clarified",
            "is fixable",
            "is addressable",
            "presentation issue",
            "writing clarity",
            "missing detail",
        )
    )
    suggests_not_fixable = any(
        phrase in rationale
        for phrase in (
            "structurally_unresolvable",
            "requires_concession",
            "cannot be addressed",
            "cannot be fixed",
            "cannot be resolved",
            "not fixable",
            "not addressable",
            "no rebuttal text can",
            "best handled by concession",
            "needs concession",
        )
    )
    if suggests_fixable and addressability != "answerable_fixable":
        return "rationale_suggests_fixable_label_not_fixable_or_unclear"
    if suggests_not_fixable and addressability == "answerable_fixable":
        return "rationale_suggests_not_fixable_label_fixable"
    return ""


def build_test_1b_independence_audit() -> dict[str, Any]:
    return {
        "judgment": "independent_model_calls",
        "importance_source": "claim_extraction.py::build_claim_messages + claim_extraction_schema",
        "resolution_source": "reviewer_calibration.py::rebuttal_resolution_messages",
        "same_call": False,
        "same_prompt": False,
        "importance_prompt_sees_rebuttal": False,
        "resolution_prompt_sees_importance": True,
        "discount_test1_directional": "partially",
        "interpretation": (
            "Importance is produced during claim extraction from the original review only. Rebuttal resolution is "
            "produced later from reviewer-claim/author-response pairs. The Test-1 cross-tab is not confounded by a "
            "single shared model call, but importance remains an unvalidated LLM proxy and should not be treated as "
            "human-validated materiality."
        ),
    }


def render_report_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    if "headline_high_importance_unresolved" not in report:
        test1b = report.get("test_1b_importance_resolution_independence", {})
        return "\n".join(
            [
                "# Addressability Classification Test 4 Dry Run",
                "",
                f"- Prepared unique claims: {summary.get('prepared_unique_claim_count', 0)}",
                f"- Main unresolved/generic candidate claims: {summary.get('main_claim_count', 0)}",
                f"- Resolved/effect control claims: {summary.get('control_resolved_or_weakened_count', 0)}",
                f"- Specifically-addressed control claims: {summary.get('control_specifically_addressed_count', 0)}",
                f"- Paper context counts: `{json.dumps(summary.get('paper_context_counts', {}), sort_keys=True)}`",
                f"- No-leakage check: `{json.dumps(summary.get('no_leakage_check', {}), sort_keys=True)}`",
                "",
                "## Test 1b - Importance / Resolution Independence",
                "",
                f"- Judgment: `{test1b.get('judgment', '')}`",
                f"- Same call: `{test1b.get('same_call')}`",
                f"- Same prompt: `{test1b.get('same_prompt')}`",
                f"- Importance prompt sees rebuttal: `{test1b.get('importance_prompt_sees_rebuttal')}`",
                f"- Interpretation: {test1b.get('interpretation', '')}",
                "",
            ]
        )
    headline = report["headline_high_importance_unresolved"]
    controls = report["controls"]
    self_consistency = report["self_consistency"]
    robustness = report.get("model_robustness_vs_baseline", {})
    consistency_check = report.get("rationale_label_consistency_check", {})
    test1b = report["test_1b_importance_resolution_independence"]
    lines = [
        "# Addressability Classification Test 4",
        "",
        "## Run Summary",
        "",
        f"- Classified unique claims: {summary['classified_unique_claim_count']}",
        f"- Main unresolved/generic candidate claims: {summary['main_claim_count']}",
        f"- Resolved/effect control claims: {summary['control_resolved_or_weakened_count']}",
        f"- Specifically-addressed control claims: {summary['control_specifically_addressed_count']}",
        f"- Paper context counts: `{json.dumps(summary['paper_context_counts'], sort_keys=True)}`",
        f"- No-leakage check: `{json.dumps(summary['no_leakage_check'], sort_keys=True)}`",
        "",
        "## Main Distribution",
        "",
        f"- Addressability: `{json.dumps(report['main_distribution'], sort_keys=True)}`",
        f"- Fixable split: `{json.dumps(report['main_fixable_split'], sort_keys=True)}`",
        f"- Tri-state split: `{json.dumps(report.get('main_tri_state_split', {}), sort_keys=True)}`",
        f"- Determinate split excluding unclear: `{json.dumps(report.get('main_determinate_split', {}), sort_keys=True)}`",
        f"- Not-fixable subtypes: `{json.dumps(report.get('main_not_fixable_subtypes', {}), sort_keys=True)}`",
        "",
        "## Headline Cell: High-Importance Proxy + Unresolved/Partial",
        "",
        f"- Claims: {headline['claim_count']}",
        f"- Addressability: `{json.dumps(headline['distribution'], sort_keys=True)}`",
        f"- Fixable split: `{json.dumps(headline['fixable_split'], sort_keys=True)}`",
        f"- Tri-state split: `{json.dumps(headline.get('tri_state_split', {}), sort_keys=True)}`",
        f"- Determinate split excluding unclear: `{json.dumps(headline.get('determinate_split', {}), sort_keys=True)}`",
        f"- Not-fixable subtypes: `{json.dumps(headline.get('not_fixable_subtypes', {}), sort_keys=True)}`",
        "",
        "## Cross-Tabs",
        "",
        f"- Addressability x importance proxy: `{json.dumps(report['addressability_by_importance_proxy'], sort_keys=True)}`",
        f"- Addressability x current effect: `{json.dumps(report['addressability_by_effect'], sort_keys=True)}`",
        f"- Addressability x current response: `{json.dumps(report['addressability_by_response'], sort_keys=True)}`",
        "",
        "## Controls",
        "",
        f"- Resolved/effect control: `{json.dumps(controls['resolved_or_weakened'], sort_keys=True)}`",
        f"- Specifically-addressed control: `{json.dumps(controls['specifically_addressed'], sort_keys=True)}`",
        "",
        "## Self-Consistency",
        "",
        f"`{json.dumps(self_consistency, sort_keys=True)}`",
        "",
        "## Model Robustness vs Baseline",
        "",
        f"`{json.dumps(robustness, sort_keys=True)}`",
        "",
        "## Rationale / Label Consistency Check",
        "",
        f"`{json.dumps(consistency_check, sort_keys=True)}`",
        "",
        "## Test 1b - Importance / Resolution Independence",
        "",
        f"- Judgment: `{test1b.get('judgment', '')}`",
        f"- Same call: `{test1b.get('same_call')}`",
        f"- Same prompt: `{test1b.get('same_prompt')}`",
        f"- Importance prompt sees rebuttal: `{test1b.get('importance_prompt_sees_rebuttal')}`",
        f"- Discount Test-1 directional: `{test1b.get('discount_test1_directional')}`",
        f"- Interpretation: {test1b.get('interpretation', '')}",
        "",
        "## Example Labels",
        "",
    ]
    for name, examples in report.get("examples", {}).items():
        lines.append(f"### {name.replace('_', ' ').title()}")
        if not examples:
            lines.append("No examples.")
        for example in examples:
            lines.append(
                f"- `{example['claim_id']}` {example['addressability']} fixable={example['fixable']} "
                f"importance={example['importance_proxy']} effect={example['current_rebuttal_effect_label']}: "
                f"{example['rationale']}"
            )
        lines.append("")
    return "\n".join(lines)


def iter_claim_records(report: dict[str, Any]):
    for paper in report.get("papers", []):
        for review in paper.get("reviews", []):
            for claim_index, claim in enumerate(review.get("claims", [])):
                yield {
                    "paper_id": paper.get("paper_id", ""),
                    "review_id": review.get("review_id", ""),
                    "claim_index": claim_index,
                    "title": paper.get("title", ""),
                    "claim": claim,
                }


def current_llm_rebuttal(claim: dict[str, Any]) -> dict[str, Any]:
    return claim.get("rebuttal_resolution", {}).get("llm_calibration", {}) or {}


def paper_context(paper: dict[str, Any], *, fallback_title: str = "") -> dict[str, Any]:
    title = clean_text(paper.get("title") or fallback_title)
    abstract = clean_text(paper.get("abstract"))
    if abstract:
        return {
            "title": title,
            "text": f"Title: {title}\nAbstract: {truncate(abstract, 1800)}",
            "has_abstract": True,
            "source": "title_abstract",
        }
    return {
        "title": title,
        "text": f"Title: {title}",
        "has_abstract": False,
        "source": "title_only",
    }


def load_normalized_papers(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    return {paper.get("paper_id", ""): paper for paper in payload.get("papers", []) if paper.get("paper_id")}


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def write_markdown(path: str | Path, report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report_markdown(report), encoding="utf-8")


def distribution(labels: list[dict[str, Any]]) -> dict[str, int]:
    return {label: Counter(item.get("addressability", "") for item in labels).get(label, 0) for label in ADDRESSABILITY_LABELS}


def tri_state_split(labels: list[dict[str, Any]]) -> dict[str, Any]:
    states = [tri_state(label) for label in labels]
    counts = Counter(states)
    return {
        "fixable": counts.get("fixable", 0),
        "not_fixable": counts.get("not_fixable", 0),
        "unclear": counts.get("unclear", 0),
        "fixable_rate": rate(counts.get("fixable", 0), len(states)),
        "not_fixable_rate": rate(counts.get("not_fixable", 0), len(states)),
        "unclear_rate": rate(counts.get("unclear", 0), len(states)),
    }


def fixable_split(labels: list[dict[str, Any]]) -> dict[str, Any]:
    fixable_count = sum(1 for label in labels if label.get("fixable"))
    not_fixable_count = len(labels) - fixable_count
    return {
        "fixable": fixable_count,
        "not_fixable": not_fixable_count,
        "fixable_rate": rate(fixable_count, len(labels)),
        "not_fixable_rate": rate(not_fixable_count, len(labels)),
    }


def determinate_split(labels: list[dict[str, Any]]) -> dict[str, Any]:
    determinate = [label for label in labels if label.get("addressability") != "unclear"]
    fixable_count = sum(1 for label in determinate if label.get("addressability") == "answerable_fixable")
    not_fixable_count = len(determinate) - fixable_count
    return {
        "determinate_count": len(determinate),
        "fixable": fixable_count,
        "not_fixable": not_fixable_count,
        "fixable_rate": rate(fixable_count, len(determinate)),
        "not_fixable_rate": rate(not_fixable_count, len(determinate)),
    }


def not_fixable_subtypes(labels: list[dict[str, Any]]) -> dict[str, Any]:
    framing = sum(1 for label in labels if label.get("addressability") == "structurally_unresolvable")
    other = sum(1 for label in labels if label.get("addressability") == "requires_concession")
    return {
        "novelty_significance_framing_verdict": framing,
        "other_requires_concession": other,
        "true_not_fixable_total": framing + other,
    }


def tri_state(label: dict[str, Any]) -> str:
    if label.get("addressability") == "answerable_fixable":
        return "fixable"
    if label.get("addressability") == "unclear":
        return "unclear"
    return "not_fixable"


def fixable_rate_excluding_unclear(states: list[str]) -> float:
    determinate = [state for state in states if state != "unclear"]
    return rate(sum(1 for state in determinate if state == "fixable"), len(determinate))


def nested_counts(rows: list[dict[str, Any]], row_key: str, col_key: str) -> dict[str, dict[str, int]]:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        table[str(row.get(row_key, ""))][str(row.get(col_key, ""))] += 1
    return {key: dict(value) for key, value in sorted(table.items())}


def example_labels(labels: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    return [
        {
            "claim_id": label.get("claim_id", ""),
            "addressability": label.get("addressability", ""),
            "fixable": label.get("fixable", False),
            "importance_proxy": label.get("importance_proxy", ""),
            "current_rebuttal_effect_label": label.get("current_rebuttal_effect_label", ""),
            "rationale": truncate(label.get("rationale", ""), 240),
        }
        for label in labels[:limit]
    ]


def validate_label(label: dict[str, Any]) -> list[str]:
    errors = []
    if label.get("addressability") not in ADDRESSABILITY_LABELS:
        errors.append("invalid:addressability")
    if label.get("confidence") not in CONFIDENCE_LABELS:
        errors.append("invalid:confidence")
    if not isinstance(label.get("fixable"), bool):
        errors.append("invalid:fixable")
    if not isinstance(label.get("rationale"), str) or not label.get("rationale", "").strip():
        errors.append("invalid:rationale")
    return errors


def normalize_importance(value: Any) -> str:
    value = str(value or "").strip().lower()
    if value in {"major", "high"}:
        return "high"
    if value in {"medium", "moderate"}:
        return "medium"
    if value in {"minor", "low", "tone-only", "question"}:
        return "low"
    return value or "unknown"


def record_key(record: dict[str, Any]) -> str:
    return f"{record.get('paper_id', '')}:{record.get('review_id', '')}:{record.get('claim_index', 0)}"


def truncate(value: Any, limit: int) -> str:
    text = clean_text(value)
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run concern addressability classification for Test 4.")
    parser.add_argument("--candidates", default="data/validation/addressability_test4_candidates_v0.1.jsonl")
    parser.add_argument("--reviewer-calibration", default="data/validation/reviewer_calibration_iclr_2024_full_v0.3_lifecycle.json")
    parser.add_argument("--normalized-papers", default="data/normalized/iclr_2024_sample_80.json")
    parser.add_argument("--labels-out", default="data/validation/addressability_test4_llm_labels_v0.1.jsonl")
    parser.add_argument("--self-consistency-out", default="data/validation/addressability_test4_self_consistency_v0.1.jsonl")
    parser.add_argument("--report-out", default="data/validation/addressability_test4_report_v0.1.json")
    parser.add_argument("--markdown", default="reports/validation/addressability_test4_report_v0.1.md")
    parser.add_argument("--model", default=DEFAULT_CHEAP_MODEL)
    parser.add_argument("--prompt-version", default="v0.1", choices=["v0.1", "v0.2"])
    parser.add_argument("--baseline-labels", default=DEFAULT_BASELINE_LABELS)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-self-consistency", action="store_true")
    parser.add_argument("--self-consistency-size", type=int, default=30)
    parser.add_argument("--self-consistency-runs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=47)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    candidates = read_jsonl(args.candidates)
    reviewer_calibration = read_json(args.reviewer_calibration)
    normalized_papers = load_normalized_papers(args.normalized_papers)
    items = build_addressability_items(candidates, reviewer_calibration, normalized_papers)
    if args.limit is not None:
        items = items[: args.limit]

    if args.dry_run:
        report = {
            "schema_version": ADDRESSABILITY_REPORT_VERSION,
            "summary": {
                "prepared_unique_claim_count": len(items),
                "main_claim_count": sum(1 for item in items if "main" in item["roles"]),
                "control_resolved_or_weakened_count": sum(
                    1 for item in items if "control_resolved_or_weakened" in item["roles"]
                ),
                "control_specifically_addressed_count": sum(
                    1 for item in items if "control_specifically_addressed" in item["roles"]
                ),
                "paper_context_counts": dict(Counter(item["context_source"] for item in items)),
                "no_leakage_check": {
                    "prompt_includes_rebuttal_text": False,
                    "prompt_includes_existing_response_or_effect_labels": False,
                    "prompt_includes_importance_proxy": False,
                },
            },
            "test_1b_importance_resolution_independence": build_test_1b_independence_audit(),
        }
        write_json(args.report_out, report)
        write_markdown(args.markdown, report)
        print(f"Prepared {len(items)} addressability items (dry-run).")
        return

    llm_client = OpenAIChatClient.from_env()
    labels = classify_items(items, llm_client=llm_client, model=args.model, prompt_version=args.prompt_version)
    write_jsonl(args.labels_out, labels)

    self_labels: list[dict[str, Any]] = []
    if not args.skip_self_consistency and items:
        rng = random.Random(args.seed)
        sample_size = min(args.self_consistency_size, len(items))
        sampled = rng.sample(items, sample_size)
        for run_index in range(args.self_consistency_runs):
            for label in classify_items(
                sampled,
                llm_client=llm_client,
                model=args.model,
                prompt_variant="self_consistency_reworded",
                prompt_version=args.prompt_version,
            ):
                label["self_consistency_run"] = run_index + 1
                self_labels.append(label)
        write_jsonl(args.self_consistency_out, self_labels)

    baseline_labels = read_jsonl(args.baseline_labels) if args.baseline_labels and Path(args.baseline_labels).exists() else []
    report = build_addressability_report(
        items,
        labels,
        self_consistency_labels=self_labels,
        test_1b=build_test_1b_independence_audit(),
        baseline_labels=baseline_labels,
    )
    write_json(args.report_out, report)
    write_markdown(args.markdown, report)
    print(f"Saved addressability labels to {args.labels_out}; report to {args.report_out} and {args.markdown}.")


if __name__ == "__main__":
    try:
        main()
    except LLMClientError as exc:
        raise SystemExit(str(exc)) from exc
