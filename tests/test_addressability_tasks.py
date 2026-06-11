from secondopinion.addressability_tasks import build_addressability_tasks


def test_build_addressability_tasks_exports_unresolved_or_generic_claims():
    tasks = build_addressability_tasks(sample_report())

    assert len(tasks) == 2
    assert tasks[0]["task_id"] == "paper1:review1:0"
    assert tasks[0]["current_rebuttal_effect_label"] == "does_not_address"
    assert tasks[1]["task_id"] == "paper1:review1:1"
    assert tasks[1]["current_rebuttal_response_label"] == "specifically_addressed"
    assert "answerable_fixable" in tasks[0]["label_schema"]["concern_addressability"]


def sample_report():
    return {
        "papers": [
            {
                "paper_id": "paper1",
                "title": "Example Paper",
                "reviews": [
                    {
                        "review_id": "review1",
                        "claims": [
                            {
                                "claim_text": "Missing ablation.",
                                "claim_type": "ablation",
                                "importance": "major",
                                "source_sentence": "Missing ablation.",
                                "rebuttal_resolution": {
                                    "matched_segment": "We discuss ablations.",
                                    "llm_calibration": {
                                        "rebuttal_response_label": "not_addressed",
                                        "rebuttal_effect_on_claim": "does_not_address",
                                        "rationale": "No actual answer.",
                                    },
                                },
                            },
                            {
                                "claim_text": "Need clearer baseline.",
                                "claim_type": "baseline",
                                "importance": "major",
                                "source_sentence": "Need clearer baseline.",
                                "rebuttal_resolution": {
                                    "matched_segment": "We compare more.",
                                    "llm_calibration": {
                                        "rebuttal_response_label": "specifically_addressed",
                                        "rebuttal_effect_on_claim": "partially_addresses",
                                        "rationale": "Partial.",
                                    },
                                },
                            },
                            {
                                "claim_text": "Typo.",
                                "claim_type": "clarity",
                                "importance": "minor",
                                "source_sentence": "Typo.",
                                "rebuttal_resolution": {
                                    "matched_segment": "Fixed.",
                                    "llm_calibration": {
                                        "rebuttal_response_label": "likely_resolved",
                                        "rebuttal_effect_on_claim": "resolved_or_weakened",
                                    },
                                },
                            },
                        ],
                    }
                ],
            }
        ]
    }
