from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .addressability_classification import (
    TARGET_EFFECTS,
    build_addressability_items,
    normalize_importance,
    read_json,
    read_jsonl,
)
from .data_inventory import classify_reply
from .llm_client import LLMClientError, OpenAIChatClient
from .normalize import get_replies, note_id
from .snapshot import load_snapshot_notes


COUNTERFACTUAL_PREFLIGHT_VERSION = "counterfactual-rebuttal-preflight-v0.1"
DEFAULT_ADDRESSABILITY_LABELS = "data/validation/addressability_test4_gpt5_labels_v0.2.jsonl"
DEFAULT_CANDIDATES = "data/validation/addressability_test4_candidates_v0.1.jsonl"
DEFAULT_REVIEWER_CALIBRATION = "data/validation/reviewer_calibration_iclr_2024_full_v0.3_lifecycle.json"
DEFAULT_NORMALIZED_PAPERS = "data/normalized/iclr_2024_sample_80.json"
DEFAULT_INVENTORY = "data/validation/openreview_inventory_iclr_2024_80.json"
DEFAULT_SNAPSHOT_DIR = "data/raw/openreview/iclr/2024/20260522T083133Z"
DEFAULT_REPORT_JSON = "data/validation/counterfactual_rebuttal_preflight_v0.1.json"
DEFAULT_REPORT_MD = "reports/validation/counterfactual_rebuttal_preflight_v0.1.md"
DEFAULT_PILOT_SAMPLE = "data/validation/counterfactual_rebuttal_pilot_sample_v0.1.jsonl"
DEFAULT_PILOT_GENERATIONS = "data/validation/counterfactual_rebuttal_pilot_generations_v0.1.jsonl"
DEFAULT_PILOT_JUDGMENTS = "data/validation/counterfactual_rebuttal_pilot_judgments_v0.1.jsonl"
DEFAULT_PILOT_REPORT = "data/validation/counterfactual_rebuttal_pilot_report_v0.1.json"
DEFAULT_PILOT_REPORT_MD = "reports/validation/counterfactual_rebuttal_pilot_report_v0.1.md"
DEFAULT_GENERATOR_MODEL = "gpt-5-mini"
DEFAULT_JUDGE_MODEL = "gpt-5"

ARM_NAMES = ("avoid", "engage", "polished_avoid")
PRIMARY_JUDGE_PAIRS = (("engage", "avoid"), ("engage", "polished_avoid"))
FULL_JUDGE_PAIRS = (("engage", "avoid"), ("engage", "polished_avoid"), ("polished_avoid", "avoid"))

PREREGISTERED_HYPOTHESES = {
    "H1": "Engage beats Avoid: a direct, substantive rebuttal should be preferred over evasive non-response.",
    "H2": "Engage beats Polished-avoid: substance should beat polite length when length and tone are controlled.",
    "H3": (
        "The Engage advantage should be larger for answerable/fixable concerns and smaller for structural "
        "novelty/significance/framing concerns."
    ),
}

RATINGISH_RE = re.compile(
    r"\b("
    r"score|rating|recommendation|raise|raised|increase|increased|lower|lowered|decrease|"
    r"maintain|maintained|keep|kept|remain|remains|unchanged|update|updated"
    r")\b",
    re.IGNORECASE,
)
STRICT_SCORE_CHANGE_RE = re.compile(
    r"("
    r"post[- ]?rebuttal|after rebuttal|after the rebuttal|"
    r"raise(?:d)? my score|increase(?:d)? my score|lower(?:ed)? my score|"
    r"maintain(?:ed)? my score|keep(?:ing)? my score|score remains|rating remains|updated my rating"
    r")",
    re.IGNORECASE,
)


def build_preflight_report(
    *,
    labels_path: str | Path = DEFAULT_ADDRESSABILITY_LABELS,
    candidates_path: str | Path = DEFAULT_CANDIDATES,
    reviewer_calibration_path: str | Path = DEFAULT_REVIEWER_CALIBRATION,
    normalized_papers_path: str | Path = DEFAULT_NORMALIZED_PAPERS,
    inventory_path: str | Path = DEFAULT_INVENTORY,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    pilot_size: int = 30,
    seed: int = 53,
) -> dict[str, Any]:
    labels = read_jsonl(labels_path)
    candidates = read_jsonl(candidates_path)
    reviewer_calibration = read_json(reviewer_calibration_path)
    normalized_papers = load_normalized_papers(normalized_papers_path)
    inventory = read_json(inventory_path)

    items = build_addressability_items(candidates, reviewer_calibration, normalized_papers)
    items_by_id = {item["claim_id"]: item for item in items}
    main_labels = [label for label in labels if "main" in label.get("roles", [])]
    main_labels = [label for label in main_labels if label.get("claim_id") in items_by_id]
    pilot_sample = stratified_pilot_sample(main_labels, items_by_id, pilot_size=pilot_size, seed=seed)

    score_probe = probe_score_movement(snapshot_dir)
    call_budget = estimate_call_budget(len(main_labels), pilot_size=len(pilot_sample))

    return {
        "schema_version": COUNTERFACTUAL_PREFLIGHT_VERSION,
        "preregistered_hypotheses": PREREGISTERED_HYPOTHESES,
        "guardrails": {
            "paired_counterfactual": "Hold paper and reviewer concern fixed; only vary rebuttal style.",
            "scope": "This measures an LLM-AC judge response, not real reviewer behavior.",
            "generator_judge_separation": "Use different model families or at least different prompts for generation and judging.",
            "length_control": "Engage and Polished-avoid should be comparable in length.",
            "no_fabricated_results": "Generated rebuttals must not invent experiments, numbers, or claims absent from paper context.",
            "blind_pairwise_judging": "Judge pairwise with order swaps and repeated runs; count only stable wins.",
            "stratification": "Report by addressability x importance_proxy.",
        },
        "data": {
            "addressability_labels_path": str(labels_path),
            "candidate_tasks_path": str(candidates_path),
            "main_claim_count": len(main_labels),
            "joined_main_claim_count": len(main_labels),
            "addressability_distribution": distribution(main_labels, "addressability"),
            "importance_distribution": distribution(main_labels, "importance_proxy"),
            "addressability_by_importance": nested_counts(main_labels, "addressability", "importance_proxy"),
            "headline_high_importance_unresolved": headline_high_importance_unresolved(main_labels),
        },
        "pre_post_score_availability": {
            "inventory_metric_feasibility": inventory.get("summary", {}).get("metric_feasibility", {}),
            "raw_snapshot_probe": score_probe,
            "interpretation": (
                "The snapshot supports initial ratings and post-rebuttal discussion/update proxies, but it does "
                "not reliably expose clean paired pre/post numeric reviewer ratings. Use score movement only as an "
                "optional observational appendix."
            ),
        },
        "experiment_design": {
            "arms": list(ARM_NAMES),
            "primary_judge_pairs": [list(pair) for pair in PRIMARY_JUDGE_PAIRS],
            "full_judge_pairs": [list(pair) for pair in FULL_JUDGE_PAIRS],
            "judge_repeats": 3,
            "order_swaps": 2,
            "call_budget": call_budget,
            "recommendation": (
                "Run the stratified pilot first. Full 232-claim experiment is call-heavy; pilot can test whether "
                "H2 has a real signal before scaling."
            ),
        },
        "pilot_sample": {
            "seed": seed,
            "requested_size": pilot_size,
            "actual_size": len(pilot_sample),
            "distribution": {
                "addressability": distribution(pilot_sample, "addressability"),
                "importance_proxy": distribution(pilot_sample, "importance_proxy"),
                "addressability_by_importance": nested_counts(pilot_sample, "addressability", "importance_proxy"),
            },
            "records": pilot_sample,
        },
    }


def load_normalized_papers(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    return {paper.get("paper_id", ""): paper for paper in payload.get("papers", []) if paper.get("paper_id")}


def stratified_pilot_sample(
    labels: list[dict[str, Any]],
    items_by_id: dict[str, dict[str, Any]],
    *,
    pilot_size: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    eligible = [label for label in labels if label.get("claim_id") in items_by_id]
    structural = [label for label in eligible if label.get("addressability") == "structurally_unresolvable"]
    concession = [label for label in eligible if label.get("addressability") == "requires_concession"]
    unclear = [label for label in eligible if label.get("addressability") == "unclear"]
    fixable = [label for label in eligible if label.get("addressability") == "answerable_fixable"]

    selected: list[dict[str, Any]] = []
    selected.extend(sorted(structural + concession, key=lambda row: row["claim_id"]))
    selected.extend(sorted(unclear, key=lambda row: row["claim_id"])[: min(2, len(unclear))])

    remaining_slots = max(0, pilot_size - len(selected))
    fixable_by_importance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for label in fixable:
        fixable_by_importance[normalize_importance(label.get("importance_proxy", ""))].append(label)
    for rows in fixable_by_importance.values():
        rng.shuffle(rows)

    fill_order = ["high", "medium", "low", "question", "unknown"]
    while remaining_slots > 0:
        progressed = False
        for importance in fill_order:
            rows = fixable_by_importance.get(importance, [])
            if not rows:
                continue
            selected.append(rows.pop())
            remaining_slots -= 1
            progressed = True
            if remaining_slots == 0:
                break
        if not progressed:
            break

    return [pilot_record(label, items_by_id[label["claim_id"]]) for label in selected[:pilot_size]]


def pilot_record(label: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": label.get("claim_id", ""),
        "paper_id": label.get("paper_id", ""),
        "review_id": label.get("review_id", ""),
        "claim_index": label.get("claim_index"),
        "title": item.get("title", ""),
        "paper_context": item.get("paper_context", ""),
        "reviewer_claim": item.get("reviewer_claim", ""),
        "importance_proxy": label.get("importance_proxy", ""),
        "addressability": label.get("addressability", ""),
        "fixable": label.get("fixable"),
        "addressability_rationale": label.get("rationale", ""),
        "current_rebuttal_response_label": label.get("current_rebuttal_response_label", ""),
        "current_rebuttal_effect_label": label.get("current_rebuttal_effect_label", ""),
    }


def headline_high_importance_unresolved(labels: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        label
        for label in labels
        if normalize_importance(label.get("importance_proxy", "")) == "high"
        and label.get("current_rebuttal_effect_label") in TARGET_EFFECTS
    ]
    return {
        "claim_count": len(rows),
        "addressability_distribution": distribution(rows, "addressability"),
        "fixable_count": sum(1 for row in rows if row.get("fixable")),
        "fixable_rate": rate(sum(1 for row in rows if row.get("fixable")), len(rows)),
    }


def probe_score_movement(snapshot_dir: str | Path) -> dict[str, Any]:
    notes = load_snapshot_notes(snapshot_dir)
    post_review_updates = []
    post_reviewer_comments = []
    ratingish_comments = []
    strict_change_comments = []
    strict_review_update_text = []

    for note in notes:
        replies = [classify_reply(reply) for reply in get_replies(note)]
        author_responses = [reply for reply in replies if reply["type"] == "author_response"]
        earliest_author_response = min(
            (reply["cdate_ms"] for reply in author_responses if reply["cdate_ms"] is not None),
            default=None,
        )
        if earliest_author_response is None:
            continue
        for reply in replies:
            if (
                reply["type"] == "official_review"
                and reply["modified_ms"] is not None
                and reply["created_ms"] is not None
                and reply["modified_ms"] > earliest_author_response
                and reply["modified_ms"] > reply["created_ms"]
            ):
                post_review_updates.append(score_probe_record(note, reply))
                if STRICT_SCORE_CHANGE_RE.search(reply.get("text", "")):
                    strict_review_update_text.append(score_probe_record(note, reply))
            if (
                reply["type"] == "official_comment"
                and reply["signer_role"] in {"reviewer", "area_chair", "program_chair"}
                and reply["created_ms"] is not None
                and reply["created_ms"] > earliest_author_response
            ):
                record = score_probe_record(note, reply)
                post_reviewer_comments.append(record)
                text = reply.get("text", "")
                if RATINGISH_RE.search(text):
                    ratingish_comments.append(record)
                if STRICT_SCORE_CHANGE_RE.search(text):
                    strict_change_comments.append(record)

    return {
        "post_rebuttal_official_review_updates": len(post_review_updates),
        "post_rebuttal_official_review_updates_with_current_rating": sum(
            1 for row in post_review_updates if row.get("rating_raw")
        ),
        "strict_score_change_text_in_updated_reviews": len(strict_review_update_text),
        "post_rebuttal_reviewer_or_ac_comments": len(post_reviewer_comments),
        "ratingish_post_rebuttal_comments": len(ratingish_comments),
        "strict_score_change_post_rebuttal_comments": len(strict_change_comments),
        "examples": {
            "ratingish_post_rebuttal_comments": ratingish_comments[:8],
            "strict_score_change_post_rebuttal_comments": strict_change_comments[:8],
            "strict_score_change_updated_reviews": strict_review_update_text[:5],
        },
        "caveat": (
            "Official review updates expose current review state in this snapshot, not guaranteed revision history. "
            "Discussion comments can mention score movement, but require text normalization before observational use."
        ),
    }


def score_probe_record(note: dict[str, Any], reply: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": note_id(note),
        "note_id": reply.get("id", ""),
        "type": reply.get("type", ""),
        "signer_role": reply.get("signer_role", ""),
        "created_at": reply.get("created_at", ""),
        "modified_at": reply.get("modified_at", ""),
        "title": truncate(reply.get("title", ""), 100),
        "text": truncate(reply.get("text", ""), 260),
        "rating_raw": reply.get("rating_raw", ""),
        "rating_normalized": reply.get("rating_normalized"),
    }


def estimate_call_budget(
    claim_count: int,
    *,
    pilot_size: int,
    judge_repeats: int = 3,
    order_swaps: int = 2,
) -> dict[str, Any]:
    def budget(n: int, pairs: tuple[tuple[str, str], ...]) -> dict[str, int]:
        return {
            "claim_count": n,
            "generation_calls": n * len(ARM_NAMES),
            "judge_calls": n * len(pairs) * order_swaps * judge_repeats,
            "total_calls": n * len(ARM_NAMES) + n * len(pairs) * order_swaps * judge_repeats,
        }

    return {
        "pilot_primary_pairs": budget(pilot_size, PRIMARY_JUDGE_PAIRS),
        "pilot_full_pairs": budget(pilot_size, FULL_JUDGE_PAIRS),
        "full_primary_pairs": budget(claim_count, PRIMARY_JUDGE_PAIRS),
        "full_all_pairs": budget(claim_count, FULL_JUDGE_PAIRS),
    }


def run_counterfactual_pilot(
    sample: list[dict[str, Any]],
    *,
    llm_client: Any,
    generator_model: str,
    judge_model: str,
    pair_set: str = "primary",
    judge_repeats: int = 3,
    limit: int | None = None,
) -> dict[str, Any]:
    rows = sample[: limit or len(sample)]
    pairs = PRIMARY_JUDGE_PAIRS if pair_set == "primary" else FULL_JUDGE_PAIRS
    generations: list[dict[str, Any]] = []
    judgments: list[dict[str, Any]] = []

    for item in rows:
        arm_outputs = {}
        avoid_generation = generate_rebuttal_arm(item, arm="avoid", llm_client=llm_client, model=generator_model)
        generations.append(avoid_generation)
        arm_outputs["avoid"] = avoid_generation["response"]

        engage_generation = generate_rebuttal_arm(item, arm="engage", llm_client=llm_client, model=generator_model)
        generations.append(engage_generation)
        arm_outputs["engage"] = engage_generation["response"]

        engage_words = int(engage_generation.get("word_count") or 120)
        polished_target = f"{max(95, engage_words - 10)}-{engage_words + 10} words"
        polished_generation = generate_rebuttal_arm(
            item,
            arm="polished_avoid",
            llm_client=llm_client,
            model=generator_model,
            target_words=polished_target,
        )
        if not length_matched(polished_generation.get("word_count", 0), engage_words):
            retry_target = f"exactly {engage_words} words, acceptable range {max(90, engage_words - 8)}-{engage_words + 8} words"
            retry_generation = generate_rebuttal_arm(
                item,
                arm="polished_avoid",
                llm_client=llm_client,
                model=generator_model,
                target_words=retry_target,
            )
            retry_generation["retry_count"] = 1
            retry_generation["previous_word_count"] = polished_generation.get("word_count")
            polished_generation = retry_generation
        generations.append(polished_generation)
        arm_outputs["polished_avoid"] = polished_generation["response"]
        for left_arm, right_arm in pairs:
            for repeat in range(1, judge_repeats + 1):
                judgments.append(
                    judge_rebuttal_pair(
                        item,
                        arm_a=left_arm,
                        response_a=arm_outputs[left_arm],
                        arm_b=right_arm,
                        response_b=arm_outputs[right_arm],
                        repeat=repeat,
                        order="forward",
                        llm_client=llm_client,
                        model=judge_model,
                    )
                )
                judgments.append(
                    judge_rebuttal_pair(
                        item,
                        arm_a=right_arm,
                        response_a=arm_outputs[right_arm],
                        arm_b=left_arm,
                        response_b=arm_outputs[left_arm],
                        repeat=repeat,
                        order="swapped",
                        llm_client=llm_client,
                        model=judge_model,
                    )
                )

    return build_pilot_report(
        sample=rows,
        generations=generations,
        judgments=judgments,
        generator_model=generator_model,
        judge_model=judge_model,
        pair_set=pair_set,
        judge_repeats=judge_repeats,
    )


def run_counterfactual_pilot_checkpointed(
    sample: list[dict[str, Any]],
    *,
    llm_client: Any,
    generator_model: str,
    judge_model: str,
    generations_path: str | Path,
    judgments_path: str | Path,
    pair_set: str = "primary",
    judge_repeats: int = 3,
    limit: int | None = None,
) -> dict[str, Any]:
    rows = sample[: limit or len(sample)]
    pairs = PRIMARY_JUDGE_PAIRS if pair_set == "primary" else FULL_JUDGE_PAIRS
    generations = read_jsonl_if_exists(generations_path)
    judgments = read_jsonl_if_exists(judgments_path)
    generations_by_key = {generation_key(row): row for row in generations}
    judgments_by_key = {judgment_key(row): row for row in judgments}

    for item_index, item in enumerate(rows, start=1):
        arm_outputs: dict[str, str] = {}
        for arm in ("avoid", "engage"):
            key = (item.get("claim_id", ""), arm)
            generation = generations_by_key.get(key)
            if generation is None:
                generation = generate_rebuttal_arm(item, arm=arm, llm_client=llm_client, model=generator_model)
                append_jsonl(generations_path, generation)
                generations.append(generation)
                generations_by_key[key] = generation
            arm_outputs[arm] = generation["response"]

        polished_key = (item.get("claim_id", ""), "polished_avoid")
        polished_generation = generations_by_key.get(polished_key)
        if polished_generation is None:
            engage_words = int(generations_by_key[(item.get("claim_id", ""), "engage")].get("word_count") or 120)
            polished_target = f"{max(95, engage_words - 10)}-{engage_words + 10} words"
            polished_generation = generate_rebuttal_arm(
                item,
                arm="polished_avoid",
                llm_client=llm_client,
                model=generator_model,
                target_words=polished_target,
            )
            if not length_matched(polished_generation.get("word_count", 0), engage_words):
                retry_target = (
                    f"exactly {engage_words} words, acceptable range "
                    f"{max(90, engage_words - 8)}-{engage_words + 8} words"
                )
                retry_generation = generate_rebuttal_arm(
                    item,
                    arm="polished_avoid",
                    llm_client=llm_client,
                    model=generator_model,
                    target_words=retry_target,
                )
                retry_generation["retry_count"] = 1
                retry_generation["previous_word_count"] = polished_generation.get("word_count")
                polished_generation = retry_generation
            append_jsonl(generations_path, polished_generation)
            generations.append(polished_generation)
            generations_by_key[polished_key] = polished_generation
        arm_outputs["polished_avoid"] = polished_generation["response"]

        for left_arm, right_arm in pairs:
            for repeat in range(1, judge_repeats + 1):
                for order, arm_a, arm_b in (
                    ("forward", left_arm, right_arm),
                    ("swapped", right_arm, left_arm),
                ):
                    key = (
                        item.get("claim_id", ""),
                        canonical_pair(left_arm, right_arm),
                        arm_a,
                        arm_b,
                        repeat,
                        order,
                    )
                    if key in judgments_by_key:
                        continue
                    judgment = judge_rebuttal_pair(
                        item,
                        arm_a=arm_a,
                        response_a=arm_outputs[arm_a],
                        arm_b=arm_b,
                        response_b=arm_outputs[arm_b],
                        repeat=repeat,
                        order=order,
                        llm_client=llm_client,
                        model=judge_model,
                    )
                    append_jsonl(judgments_path, judgment)
                    judgments.append(judgment)
                    judgments_by_key[key] = judgment
        print(
            f"Completed claim {item_index}/{len(rows)}: {item.get('claim_id', '')} "
            f"(generations={len(generations)}, judgments={len(judgments)})",
            flush=True,
        )

    return build_pilot_report(
        sample=rows,
        generations=generations,
        judgments=judgments,
        generator_model=generator_model,
        judge_model=judge_model,
        pair_set=pair_set,
        judge_repeats=judge_repeats,
    )


def generate_rebuttal_arm(
    item: dict[str, Any],
    *,
    arm: str,
    llm_client: Any,
    model: str,
    target_words: str | None = None,
) -> dict[str, Any]:
    payload = llm_client.complete_json(
        model=model,
        messages=generation_messages(item, arm=arm, target_words=target_words),
        schema_name="counterfactual_rebuttal_generation",
        schema=generation_schema(),
    )
    response = clean_generated_response(payload.get("response", ""))
    return {
        "claim_id": item.get("claim_id", ""),
        "paper_id": item.get("paper_id", ""),
        "review_id": item.get("review_id", ""),
        "claim_index": item.get("claim_index"),
        "arm": arm,
        "model": model,
        "response": response,
        "word_count": len(response.split()),
        "target_words": target_words or "",
        "strategy_notes": str(payload.get("strategy_notes", "")),
    }


def generation_messages(item: dict[str, Any], *, arm: str, target_words: str | None = None) -> list[dict[str, str]]:
    arm_instruction = {
        "avoid": (
            "Write an evasive or shallow author response. It may acknowledge the concern politely, but it should "
            "not directly resolve the reviewer concern or provide concrete reasoning. Do not give mechanisms, "
            "evidence, comparisons, or an argument for why the reviewer is wrong."
        ),
        "engage": (
            "Write a direct, substantive author response. Engage the specific concern with reasoning grounded in "
            "the provided paper context. You may promise a feasible clarification or small additional check, but "
            "must not claim new experiments, numbers, or results that are not in the context."
        ),
        "polished_avoid": (
            "Write a polished, courteous, length-controlled response that sounds careful but avoids substantively "
            "answering the concern. Match the likely length of a substantive rebuttal, but do not add concrete "
            "reasoning or evidence."
        ),
    }[arm]
    if target_words is None:
        target_words = "45-65 words" if arm == "avoid" else "110-130 words"
    system = (
        "You are writing controlled counterfactual author rebuttals for an experiment. "
        "Never invent completed experiments, numerical results, citations, or claims absent from the paper context. "
        "Output JSON only."
    )
    user = (
        f"PAPER CONTEXT:\n{item.get('paper_context', '')}\n\n"
        f"REVIEWER CONCERN:\n{item.get('reviewer_claim', '')}\n\n"
        f"ARM: {arm}\n"
        f"TARGET LENGTH: {target_words}\n"
        f"INSTRUCTION: {arm_instruction}\n\n"
        "The target length is mandatory for experiment validity. If you need more words without adding substance, "
        "use acknowledgments, scope language, and promises to clarify; do not add technical evidence.\n\n"
        "Return JSON with response and strategy_notes."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "response": {"type": "string"},
            "strategy_notes": {"type": "string"},
        },
        "required": ["response", "strategy_notes"],
    }


def judge_rebuttal_pair(
    item: dict[str, Any],
    *,
    arm_a: str,
    response_a: str,
    arm_b: str,
    response_b: str,
    repeat: int,
    order: str,
    llm_client: Any,
    model: str,
) -> dict[str, Any]:
    payload = llm_client.complete_json(
        model=model,
        messages=judge_messages(item, response_a=response_a, response_b=response_b),
        schema_name="counterfactual_rebuttal_pairwise_judgment",
        schema=judge_schema(),
    )
    winner = payload.get("winner", "tie")
    mapped_winner = map_winner_to_arm(winner, arm_a=arm_a, arm_b=arm_b)
    return {
        "claim_id": item.get("claim_id", ""),
        "paper_id": item.get("paper_id", ""),
        "review_id": item.get("review_id", ""),
        "claim_index": item.get("claim_index"),
        "addressability": item.get("addressability", ""),
        "importance_proxy": item.get("importance_proxy", ""),
        "pair": f"{arm_a}_vs_{arm_b}",
        "arm_a": arm_a,
        "arm_b": arm_b,
        "winner": winner,
        "winner_arm": mapped_winner,
        "repeat": repeat,
        "order": order,
        "model": model,
        "confidence": payload.get("confidence", ""),
        "rationale": str(payload.get("rationale", "")),
        "resolution_a": payload.get("resolution_a", ""),
        "resolution_b": payload.get("resolution_b", ""),
        "good_faith_a": payload.get("good_faith_a", ""),
        "good_faith_b": payload.get("good_faith_b", ""),
        "predicted_ac_helpfulness_a": payload.get("predicted_ac_helpfulness_a"),
        "predicted_ac_helpfulness_b": payload.get("predicted_ac_helpfulness_b"),
    }


def judge_messages(item: dict[str, Any], *, response_a: str, response_b: str) -> list[dict[str, str]]:
    system = (
        "You are an expert ML/AI area chair judging two anonymous author rebuttal responses to the same reviewer "
        "concern. Prefer the response that more substantively addresses the concern while staying credible. "
        "Do not reward length, polish, or politeness unless it improves substantive resolution. Penalize fabricated "
        "experiments, numbers, or unsupported claims. Output JSON only."
    )
    user = (
        f"PAPER CONTEXT:\n{item.get('paper_context', '')}\n\n"
        f"REVIEWER CONCERN:\n{item.get('reviewer_claim', '')}\n\n"
        f"RESPONSE A:\n{response_a}\n\n"
        f"RESPONSE B:\n{response_b}\n\n"
        "Choose winner A, B, or tie. Also rate each response's resolution and good faith."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def judge_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "winner": {"type": "string", "enum": ["A", "B", "tie"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "rationale": {"type": "string"},
            "resolution_a": {"type": "string", "enum": ["none", "partial", "strong"]},
            "resolution_b": {"type": "string", "enum": ["none", "partial", "strong"]},
            "good_faith_a": {"type": "string", "enum": ["low", "medium", "high"]},
            "good_faith_b": {"type": "string", "enum": ["low", "medium", "high"]},
            "predicted_ac_helpfulness_a": {"type": "integer", "minimum": 1, "maximum": 5},
            "predicted_ac_helpfulness_b": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": [
            "winner",
            "confidence",
            "rationale",
            "resolution_a",
            "resolution_b",
            "good_faith_a",
            "good_faith_b",
            "predicted_ac_helpfulness_a",
            "predicted_ac_helpfulness_b",
        ],
    }


def build_pilot_report(
    *,
    sample: list[dict[str, Any]],
    generations: list[dict[str, Any]],
    judgments: list[dict[str, Any]],
    generator_model: str,
    judge_model: str,
    pair_set: str,
    judge_repeats: int,
) -> dict[str, Any]:
    stable = stable_pairwise_results(judgments)
    return {
        "schema_version": "counterfactual-rebuttal-pilot-report-v0.1",
        "preregistered_hypotheses": PREREGISTERED_HYPOTHESES,
        "models": {"generator": generator_model, "judge": judge_model},
        "design": {
            "pair_set": pair_set,
            "judge_repeats": judge_repeats,
            "order_swaps": 2,
            "arms": list(ARM_NAMES),
        },
        "summary": {
            "claim_count": len(sample),
            "generation_count": len(generations),
            "judgment_count": len(judgments),
            "sample_addressability": distribution(sample, "addressability"),
            "sample_importance": distribution(sample, "importance_proxy"),
        },
        "arm_length": summarize_arm_lengths(generations),
        "length_control": summarize_length_control(generations),
        "judge_diagnostics": summarize_judgments(judgments),
        "stable_pairwise": stable,
        "hypothesis_readout": hypothesis_readout(stable),
        "generations": generations,
        "judgments": judgments,
    }


def stable_pairwise_results(judgments: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for judgment in judgments:
        canonical = canonical_pair(judgment.get("arm_a", ""), judgment.get("arm_b", ""))
        grouped[(judgment.get("claim_id", ""), canonical)].append(judgment)

    results = []
    for (claim_id, pair), rows in sorted(grouped.items()):
        counts = Counter(row.get("winner_arm", "tie") for row in rows)
        threshold = len(rows) // 2 + 1
        stable_winner = "unstable"
        for winner, count in counts.items():
            if count >= threshold:
                stable_winner = winner
                break
        first = rows[0]
        results.append(
            {
                "claim_id": claim_id,
                "pair": pair,
                "addressability": first.get("addressability", ""),
                "importance_proxy": first.get("importance_proxy", ""),
                "judgment_count": len(rows),
                "winner_counts": dict(sorted(counts.items())),
                "stable_winner": stable_winner,
            }
        )

    pair_summary: dict[str, Counter[str]] = defaultdict(Counter)
    pair_by_addressability: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for row in results:
        pair_summary[row["pair"]][row["stable_winner"]] += 1
        pair_by_addressability[row["pair"]][row["addressability"]][row["stable_winner"]] += 1

    return {
        "per_claim": results,
        "pair_summary": {key: dict(sorted(value.items())) for key, value in sorted(pair_summary.items())},
        "pair_by_addressability": {
            pair: {addr: dict(sorted(counts.items())) for addr, counts in sorted(by_addr.items())}
            for pair, by_addr in sorted(pair_by_addressability.items())
        },
    }


def hypothesis_readout(stable: dict[str, Any]) -> dict[str, Any]:
    summary = stable.get("pair_summary", {})
    return {
        "H1_engage_over_avoid": pair_readout(summary.get(canonical_pair("engage", "avoid"), {}), winner="engage"),
        "H2_engage_over_polished_avoid": pair_readout(
            summary.get(canonical_pair("engage", "polished_avoid"), {}),
            winner="engage",
        ),
        "H3_by_addressability": stable.get("pair_by_addressability", {}),
    }


def pair_readout(counts: dict[str, int], *, winner: str) -> dict[str, Any]:
    total = sum(counts.values())
    return {
        "counts": counts,
        "winner_count": counts.get(winner, 0),
        "winner_rate": rate(counts.get(winner, 0), total),
        "stable_total": total,
    }


def summarize_arm_lengths(generations: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for generation in generations:
        grouped[generation.get("arm", "")].append(int(generation.get("word_count") or 0))
    summary = {}
    for arm, counts in sorted(grouped.items()):
        summary[arm] = {
            "count": len(counts),
            "mean_words": round(sum(counts) / len(counts), 2) if counts else 0,
            "min_words": min(counts) if counts else 0,
            "max_words": max(counts) if counts else 0,
        }
    return summary


def summarize_length_control(generations: list[dict[str, Any]]) -> dict[str, Any]:
    by_claim: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for generation in generations:
        by_claim[generation.get("claim_id", "")][generation.get("arm", "")] = generation
    diffs = []
    for arms in by_claim.values():
        engage = arms.get("engage")
        polished = arms.get("polished_avoid")
        if not engage or not polished:
            continue
        engage_words = int(engage.get("word_count") or 0)
        polished_words = int(polished.get("word_count") or 0)
        if engage_words <= 0:
            continue
        diffs.append(abs(engage_words - polished_words) / engage_words)
    return {
        "engage_polished_pairs": len(diffs),
        "mean_relative_word_diff": round(sum(diffs) / len(diffs), 4) if diffs else 0.0,
        "max_relative_word_diff": round(max(diffs), 4) if diffs else 0.0,
        "over_15pct_diff_count": sum(1 for diff in diffs if diff > 0.15),
        "polished_retry_count": sum(1 for row in generations if row.get("arm") == "polished_avoid" and row.get("retry_count")),
    }


def summarize_judgments(judgments: list[dict[str, Any]]) -> dict[str, Any]:
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for judgment in judgments:
        by_pair[canonical_pair(judgment.get("arm_a", ""), judgment.get("arm_b", ""))].append(judgment)
    return {
        "confidence": distribution(judgments, "confidence"),
        "winner_arm": distribution(judgments, "winner_arm"),
        "by_pair": {
            pair: {
                "judgment_count": len(rows),
                "confidence": distribution(rows, "confidence"),
                "winner_arm": distribution(rows, "winner_arm"),
            }
            for pair, rows in sorted(by_pair.items())
        },
        "engage_vs_polished_by_addressability_deltas": engage_vs_polished_deltas(judgments),
    }


def engage_vs_polished_deltas(judgments: list[dict[str, Any]]) -> dict[str, Any]:
    resolution_values = {"none": 0, "partial": 1, "strong": 2}
    rows_by_addressability: dict[str, list[dict[str, float]]] = defaultdict(list)
    for judgment in judgments:
        if {judgment.get("arm_a", ""), judgment.get("arm_b", "")} != {"engage", "polished_avoid"}:
            continue
        if judgment.get("arm_a") == "engage":
            engage_resolution = resolution_values.get(str(judgment.get("resolution_a", "")), 0)
            polished_resolution = resolution_values.get(str(judgment.get("resolution_b", "")), 0)
            engage_helpfulness = float(judgment.get("predicted_ac_helpfulness_a") or 0)
            polished_helpfulness = float(judgment.get("predicted_ac_helpfulness_b") or 0)
        else:
            engage_resolution = resolution_values.get(str(judgment.get("resolution_b", "")), 0)
            polished_resolution = resolution_values.get(str(judgment.get("resolution_a", "")), 0)
            engage_helpfulness = float(judgment.get("predicted_ac_helpfulness_b") or 0)
            polished_helpfulness = float(judgment.get("predicted_ac_helpfulness_a") or 0)
        rows_by_addressability[str(judgment.get("addressability", ""))].append(
            {
                "resolution_delta": engage_resolution - polished_resolution,
                "helpfulness_delta": engage_helpfulness - polished_helpfulness,
                "engage_resolution": engage_resolution,
                "polished_resolution": polished_resolution,
                "engage_helpfulness": engage_helpfulness,
                "polished_helpfulness": polished_helpfulness,
            }
        )
    return {key: summarize_delta_rows(rows) for key, rows in sorted(rows_by_addressability.items())}


def summarize_delta_rows(rows: list[dict[str, float]]) -> dict[str, Any]:
    return {
        "judgment_count": len(rows),
        "claim_count_estimate": round(len(rows) / 6, 2),
        "mean_resolution_delta": mean_field(rows, "resolution_delta"),
        "mean_helpfulness_delta": mean_field(rows, "helpfulness_delta"),
        "mean_engage_resolution": mean_field(rows, "engage_resolution"),
        "mean_polished_resolution": mean_field(rows, "polished_resolution"),
        "mean_engage_helpfulness": mean_field(rows, "engage_helpfulness"),
        "mean_polished_helpfulness": mean_field(rows, "polished_helpfulness"),
    }


def mean_field(rows: list[dict[str, float]], field: str) -> float:
    return round(sum(row[field] for row in rows) / len(rows), 4) if rows else 0.0


def canonical_pair(left: str, right: str) -> str:
    if {left, right} == {"engage", "avoid"}:
        return "engage_vs_avoid"
    if {left, right} == {"engage", "polished_avoid"}:
        return "engage_vs_polished_avoid"
    if {left, right} == {"polished_avoid", "avoid"}:
        return "polished_avoid_vs_avoid"
    return f"{left}_vs_{right}"


def map_winner_to_arm(winner: Any, *, arm_a: str, arm_b: str) -> str:
    if winner == "A":
        return arm_a
    if winner == "B":
        return arm_b
    return "tie"


def clean_generated_response(value: Any) -> str:
    return " ".join(str(value or "").split())


def generation_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("claim_id", "")), str(row.get("arm", "")))


def judgment_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("claim_id", "")),
        canonical_pair(str(row.get("arm_a", "")), str(row.get("arm_b", ""))),
        str(row.get("arm_a", "")),
        str(row.get("arm_b", "")),
        row.get("repeat"),
        str(row.get("order", "")),
    )


def length_matched(candidate_words: Any, reference_words: Any, *, tolerance: float = 0.15) -> bool:
    try:
        candidate = int(candidate_words)
        reference = int(reference_words)
    except (TypeError, ValueError):
        return False
    if reference <= 0:
        return False
    return abs(candidate - reference) / reference <= tolerance


def distribution(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key, "")) for row in rows).items()))


def nested_counts(rows: list[dict[str, Any]], row_key: str, col_key: str) -> dict[str, dict[str, int]]:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        table[str(row.get(row_key, ""))][str(row.get(col_key, ""))] += 1
    return {key: dict(sorted(value.items())) for key, value in sorted(table.items())}


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl_if_exists(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_markdown(path: str | Path, report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if report.get("schema_version") == "counterfactual-rebuttal-pilot-report-v0.1":
        text = render_pilot_markdown(report)
    else:
        text = render_markdown(report)
    path.write_text(text, encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    data = report["data"]
    score = report["pre_post_score_availability"]["raw_snapshot_probe"]
    call_budget = report["experiment_design"]["call_budget"]
    pilot = report["pilot_sample"]
    lines = [
        "# Counterfactual Rebuttal Experiment Preflight",
        "",
        "## Preregistered Hypotheses",
        "",
    ]
    for key, value in report["preregistered_hypotheses"].items():
        lines.append(f"- **{key}**: {value}")
    lines.extend(
        [
            "",
            "## Data Readiness",
            "",
            f"- Main Test-4 concerns joined: {data['joined_main_claim_count']} / {data['main_claim_count']}",
            f"- Addressability distribution: `{json.dumps(data['addressability_distribution'], sort_keys=True)}`",
            f"- Importance distribution: `{json.dumps(data['importance_distribution'], sort_keys=True)}`",
            f"- Headline high-importance unresolved cell: `{json.dumps(data['headline_high_importance_unresolved'], sort_keys=True)}`",
            "",
            "## Pre/Post Reviewer Score Availability",
            "",
            f"- Post-rebuttal official review updates: {score['post_rebuttal_official_review_updates']}",
            f"- Updated official reviews with current rating field: {score['post_rebuttal_official_review_updates_with_current_rating']}",
            f"- Post-rebuttal reviewer/AC comments: {score['post_rebuttal_reviewer_or_ac_comments']}",
            f"- Rating-ish post-rebuttal comments: {score['ratingish_post_rebuttal_comments']}",
            f"- Strict score-change comments: {score['strict_score_change_post_rebuttal_comments']}",
            f"- Strict score-change text inside updated reviews: {score['strict_score_change_text_in_updated_reviews']}",
            "",
            "**Interpretation:** Clean paired pre/post numeric reviewer ratings are not reliably available in this snapshot. "
            "Use score movement only as an optional observational appendix; it should not gate the counterfactual experiment.",
            "",
            "## Call Budget",
            "",
            f"- Pilot primary pairs: `{json.dumps(call_budget['pilot_primary_pairs'], sort_keys=True)}`",
            f"- Pilot full pairs: `{json.dumps(call_budget['pilot_full_pairs'], sort_keys=True)}`",
            f"- Full primary pairs: `{json.dumps(call_budget['full_primary_pairs'], sort_keys=True)}`",
            f"- Full all pairs: `{json.dumps(call_budget['full_all_pairs'], sort_keys=True)}`",
            "",
            "## Pilot Sample",
            "",
            f"- Requested / actual: {pilot['requested_size']} / {pilot['actual_size']}",
            f"- Addressability: `{json.dumps(pilot['distribution']['addressability'], sort_keys=True)}`",
            f"- Importance: `{json.dumps(pilot['distribution']['importance_proxy'], sort_keys=True)}`",
            "",
            "## Guardrails",
            "",
        ]
    )
    for key, value in report["guardrails"].items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    return "\n".join(lines)


def render_pilot_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Counterfactual Rebuttal Pilot Report",
        "",
        "## Summary",
        "",
        f"- Claims: {summary['claim_count']}",
        f"- Generations: {summary['generation_count']}",
        f"- Pairwise judgments: {summary['judgment_count']}",
        f"- Generator model: `{report['models']['generator']}`",
        f"- Judge model: `{report['models']['judge']}`",
        f"- Sample addressability: `{json.dumps(summary['sample_addressability'], sort_keys=True)}`",
        f"- Sample importance: `{json.dumps(summary['sample_importance'], sort_keys=True)}`",
        "",
        "## Arm Length",
        "",
        f"`{json.dumps(report['arm_length'], sort_keys=True)}`",
        "",
        "## Length Control",
        "",
        f"`{json.dumps(report['length_control'], sort_keys=True)}`",
        "",
        "## Judge Diagnostics",
        "",
        f"`{json.dumps(report['judge_diagnostics'], sort_keys=True)}`",
        "",
        "## Stable Pairwise Results",
        "",
        f"- Pair summary: `{json.dumps(report['stable_pairwise']['pair_summary'], sort_keys=True)}`",
        f"- By addressability: `{json.dumps(report['stable_pairwise']['pair_by_addressability'], sort_keys=True)}`",
        "",
        "## Hypothesis Readout",
        "",
        f"`{json.dumps(report['hypothesis_readout'], sort_keys=True)}`",
        "",
        "## Caveat",
        "",
        "This is an LLM-AC counterfactual experiment, not direct evidence of human reviewer score movement.",
        "",
    ]
    return "\n".join(lines)


def truncate(text: Any, limit: int) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Prepare the counterfactual rebuttal experiment preflight report.")
    parser.add_argument("--run-pilot", action="store_true", help="Run the LLM counterfactual pilot from a pilot sample.")
    parser.add_argument("--labels", default=DEFAULT_ADDRESSABILITY_LABELS)
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--reviewer-calibration", default=DEFAULT_REVIEWER_CALIBRATION)
    parser.add_argument("--normalized-papers", default=DEFAULT_NORMALIZED_PAPERS)
    parser.add_argument("--inventory", default=DEFAULT_INVENTORY)
    parser.add_argument("--snapshot-dir", default=DEFAULT_SNAPSHOT_DIR)
    parser.add_argument("--report-out", default=DEFAULT_REPORT_JSON)
    parser.add_argument("--markdown", default=DEFAULT_REPORT_MD)
    parser.add_argument("--pilot-sample-out", default=DEFAULT_PILOT_SAMPLE)
    parser.add_argument("--pilot-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=53)
    parser.add_argument("--pilot-sample-in", default=DEFAULT_PILOT_SAMPLE)
    parser.add_argument("--generations-out", default=DEFAULT_PILOT_GENERATIONS)
    parser.add_argument("--judgments-out", default=DEFAULT_PILOT_JUDGMENTS)
    parser.add_argument("--pilot-report-out", default=DEFAULT_PILOT_REPORT)
    parser.add_argument("--pilot-markdown", default=DEFAULT_PILOT_REPORT_MD)
    parser.add_argument("--generator-model", default=DEFAULT_GENERATOR_MODEL)
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--pair-set", default="primary", choices=["primary", "full"])
    parser.add_argument("--judge-repeats", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    if args.run_pilot:
        sample = read_jsonl(args.pilot_sample_in)
        llm_client = OpenAIChatClient.from_env()
        report = run_counterfactual_pilot_checkpointed(
            sample,
            llm_client=llm_client,
            generator_model=args.generator_model,
            judge_model=args.judge_model,
            generations_path=args.generations_out,
            judgments_path=args.judgments_out,
            pair_set=args.pair_set,
            judge_repeats=args.judge_repeats,
            limit=args.limit,
        )
        write_json(args.pilot_report_out, report)
        write_markdown(args.pilot_markdown, report)
        print(
            f"Saved pilot generations to {args.generations_out}, judgments to {args.judgments_out}, "
            f"and report to {args.pilot_report_out} / {args.pilot_markdown}."
        )
        return

    report = build_preflight_report(
        labels_path=args.labels,
        candidates_path=args.candidates,
        reviewer_calibration_path=args.reviewer_calibration,
        normalized_papers_path=args.normalized_papers,
        inventory_path=args.inventory,
        snapshot_dir=args.snapshot_dir,
        pilot_size=args.pilot_size,
        seed=args.seed,
    )
    write_json(args.report_out, report)
    write_markdown(args.markdown, report)
    write_jsonl(args.pilot_sample_out, report["pilot_sample"]["records"])
    print(
        f"Saved preflight report to {args.report_out}, markdown to {args.markdown}, "
        f"and pilot sample to {args.pilot_sample_out}."
    )


if __name__ == "__main__":
    try:
        main()
    except LLMClientError as exc:
        raise SystemExit(str(exc)) from exc
