from secondopinion.counterfactual_rebuttal import (
    PREREGISTERED_HYPOTHESES,
    build_pilot_report,
    estimate_call_budget,
    length_matched,
    map_winner_to_arm,
    stratified_pilot_sample,
)


def test_preregistered_hypotheses_include_substance_over_polish():
    assert "H1" in PREREGISTERED_HYPOTHESES
    assert "H2" in PREREGISTERED_HYPOTHESES
    assert "Polished-avoid" in PREREGISTERED_HYPOTHESES["H2"]
    assert "H3" in PREREGISTERED_HYPOTHESES


def test_stratified_pilot_sample_keeps_rare_structural_cases():
    labels = [
        label("p:r:0", "structurally_unresolvable", "major"),
        label("p:r:1", "unclear", "minor"),
        label("p:r:2", "answerable_fixable", "major"),
        label("p:r:3", "answerable_fixable", "medium"),
        label("p:r:4", "answerable_fixable", "minor"),
        label("p:r:5", "answerable_fixable", "question"),
    ]
    items = {
        row["claim_id"]: {
            "claim_id": row["claim_id"],
            "title": "Paper",
            "paper_context": "Title: Paper\nAbstract: Test.",
            "reviewer_claim": "Concern.",
        }
        for row in labels
    }

    sample = stratified_pilot_sample(labels, items, pilot_size=4, seed=7)

    assert sample[0]["addressability"] == "structurally_unresolvable"
    assert len(sample) == 4
    assert any(row["importance_proxy"] == "major" for row in sample)


def test_estimate_call_budget_counts_order_swaps_and_repeats():
    budget = estimate_call_budget(232, pilot_size=30)

    assert budget["pilot_primary_pairs"]["generation_calls"] == 90
    assert budget["pilot_primary_pairs"]["judge_calls"] == 360
    assert budget["full_all_pairs"]["generation_calls"] == 696
    assert budget["full_all_pairs"]["judge_calls"] == 4176


def test_pairwise_report_aggregates_swapped_order_to_canonical_pair():
    sample = [
        {
            "claim_id": "p:r:0",
            "addressability": "answerable_fixable",
            "importance_proxy": "major",
        }
    ]
    generations = [
        {"claim_id": "p:r:0", "arm": "engage", "word_count": 120},
        {"claim_id": "p:r:0", "arm": "avoid", "word_count": 50},
    ]
    judgments = [
        judgment("p:r:0", "engage", "avoid", "A", "engage"),
        judgment("p:r:0", "avoid", "engage", "B", "engage"),
        judgment("p:r:0", "engage", "avoid", "A", "engage"),
        judgment("p:r:0", "avoid", "engage", "B", "engage"),
    ]

    report = build_pilot_report(
        sample=sample,
        generations=generations,
        judgments=judgments,
        generator_model="gpt-5-mini",
        judge_model="gpt-5",
        pair_set="primary",
        judge_repeats=2,
    )

    assert report["stable_pairwise"]["pair_summary"]["engage_vs_avoid"]["engage"] == 1
    assert report["hypothesis_readout"]["H1_engage_over_avoid"]["winner_rate"] == 1.0


def test_map_winner_to_arm_handles_tie():
    assert map_winner_to_arm("A", arm_a="avoid", arm_b="engage") == "avoid"
    assert map_winner_to_arm("B", arm_a="avoid", arm_b="engage") == "engage"
    assert map_winner_to_arm("tie", arm_a="avoid", arm_b="engage") == "tie"


def test_length_matched_uses_relative_tolerance():
    assert length_matched(115, 100, tolerance=0.15)
    assert not length_matched(116, 100, tolerance=0.15)
    assert not length_matched("bad", 100)


def label(claim_id: str, addressability: str, importance: str):
    return {
        "claim_id": claim_id,
        "paper_id": claim_id.split(":")[0],
        "review_id": claim_id.split(":")[1],
        "claim_index": int(claim_id.split(":")[2]),
        "roles": ["main"],
        "addressability": addressability,
        "fixable": addressability == "answerable_fixable",
        "importance_proxy": importance,
        "rationale": "Test rationale.",
        "current_rebuttal_response_label": "not_addressed",
        "current_rebuttal_effect_label": "does_not_address",
    }


def judgment(claim_id: str, arm_a: str, arm_b: str, winner: str, winner_arm: str):
    return {
        "claim_id": claim_id,
        "addressability": "answerable_fixable",
        "importance_proxy": "major",
        "arm_a": arm_a,
        "arm_b": arm_b,
        "winner": winner,
        "winner_arm": winner_arm,
    }
