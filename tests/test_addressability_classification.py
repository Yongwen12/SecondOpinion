from secondopinion.addressability_classification import (
    build_addressability_items,
    build_addressability_report,
    build_test_1b_independence_audit,
)


def test_build_addressability_items_adds_controls_without_leaking_prompt_fields():
    items = build_addressability_items(
        candidates=[
            {
                "task_id": "p1:r1:0",
                "paper_id": "p1",
                "review_id": "r1",
                "claim_index": 0,
                "reviewer_claim": "Missing ablation.",
                "importance_proxy": "major",
                "current_rebuttal_response_label": "specifically_addressed",
                "current_rebuttal_effect_label": "partially_addresses",
            }
        ],
        reviewer_calibration=sample_reviewer_calibration(),
        normalized_papers={
            "p1": {
                "title": "A paper",
                "abstract": "The paper proposes a method and evaluates it.",
            }
        },
    )

    assert len(items) == 3
    by_id = {item["claim_id"]: item for item in items}
    assert by_id["p1:r1:0"]["roles"] == ["control_specifically_addressed", "main"]
    assert by_id["p1:r1:0"]["had_paper_context"] is True
    assert "matched_rebuttal_segment" not in by_id["p1:r1:0"]
    assert "current_rationale" not in by_id["p1:r1:0"]
    assert by_id["p1:r1:1"]["roles"] == ["control_resolved_or_weakened"]


def test_build_addressability_report_counts_headline_and_controls():
    items = [
        {
            "claim_id": "p1:r1:0",
            "roles": ["main", "control_specifically_addressed"],
        },
        {
            "claim_id": "p1:r1:1",
            "roles": ["main"],
        },
        {
            "claim_id": "p1:r1:2",
            "roles": ["control_resolved_or_weakened"],
        },
    ]
    labels = [
        label("p1:r1:0", "answerable_fixable", True, importance="major", response="specifically_addressed", effect="partially_addresses"),
        label("p1:r1:1", "requires_concession", False, importance="major", response="not_addressed", effect="does_not_address"),
        label("p1:r1:2", "answerable_fixable", True, importance="minor", response="likely_resolved", effect="resolved_or_weakened"),
    ]

    report = build_addressability_report(items, labels, test_1b=build_test_1b_independence_audit())

    assert report["main_distribution"]["answerable_fixable"] == 1
    assert report["main_distribution"]["requires_concession"] == 1
    headline = report["headline_high_importance_unresolved"]
    assert headline["claim_count"] == 2
    assert headline["fixable_split"]["fixable"] == 1
    assert headline["fixable_split"]["not_fixable"] == 1
    assert report["controls"]["resolved_or_weakened"]["claim_count"] == 1
    assert report["controls"]["specifically_addressed"]["claim_count"] == 1
    assert report["test_1b_importance_resolution_independence"]["same_call"] is False


def test_test_1b_independence_audit_marks_separate_calls_but_proxy_caveat():
    audit = build_test_1b_independence_audit()

    assert audit["judgment"] == "independent_model_calls"
    assert audit["same_call"] is False
    assert audit["importance_prompt_sees_rebuttal"] is False
    assert audit["discount_test1_directional"] == "partially"


def sample_reviewer_calibration():
    return {
        "papers": [
            {
                "paper_id": "p1",
                "title": "A paper",
                "reviews": [
                    {
                        "review_id": "r1",
                        "claims": [
                            {
                                "claim_text": "Missing ablation.",
                                "importance": "major",
                                "rebuttal_resolution": {
                                    "llm_calibration": {
                                        "rebuttal_response_label": "specifically_addressed",
                                        "rebuttal_effect_on_claim": "partially_addresses",
                                    }
                                },
                            },
                            {
                                "claim_text": "Issue resolved.",
                                "importance": "minor",
                                "rebuttal_resolution": {
                                    "llm_calibration": {
                                        "rebuttal_response_label": "likely_resolved",
                                        "rebuttal_effect_on_claim": "resolved_or_weakened",
                                    }
                                },
                            },
                            {
                                "claim_text": "Engaged concern.",
                                "importance": "medium",
                                "rebuttal_resolution": {
                                    "llm_calibration": {
                                        "rebuttal_response_label": "specifically_addressed",
                                        "rebuttal_effect_on_claim": "unclear",
                                    }
                                },
                            },
                        ],
                    }
                ],
            }
        ]
    }


def label(claim_id, addressability, fixable, *, importance, response, effect):
    return {
        "claim_id": claim_id,
        "addressability": addressability,
        "fixable": fixable,
        "rationale": "Test rationale.",
        "confidence": "high",
        "had_paper_context": True,
        "importance_proxy": importance,
        "current_rebuttal_response_label": response,
        "current_rebuttal_effect_label": effect,
    }
