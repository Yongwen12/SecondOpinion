from secondopinion.presentation_checks import build_p0_report, render_p0_markdown


def test_presentation_checks_builds_rebuttal_cross_tables():
    report = build_p0_report(sample_reviewer_calibration())
    test1 = report["tests"]["test_1_materiality_resolution"]

    assert test1["claim_count"] == 3
    assert test1["importance_counts"]["high"] == 2
    assert test1["effect_counts"]["does_not_address"] == 1
    assert test1["importance_by_effect"]["high"]["does_not_address"] == 1
    assert test1["response_by_effect"]["specifically_addressed"]["partially_addresses"] == 1
    assert test1["high_importance_unresolved_or_partial_count"] == 2
    assert test1["specifically_addressed_unresolved_or_partial_count"] == 1


def test_presentation_checks_counts_scope_and_grounding():
    grounding = {
        "stats": {
            "raw_candidate_count": 10,
            "raw_grounding_pass_count": 8,
            "raw_grounding_fail_count": 2,
            "raw_grounding_pass_rate": 0.8,
            "final_claim_count": 7,
            "final_grounding_pass_count": 7,
            "final_grounding_fail_count": 0,
            "final_grounding_pass_rate": 1.0,
        },
        "examples": {"raw_grounding_failures": [{"paper_id": "p1", "review_id": "r1", "claim_text": "bad"}]},
    }

    report = build_p0_report(sample_reviewer_calibration(), grounding_validation=grounding)
    test2 = report["tests"]["test_2_sample_size_alignment"]
    test3 = report["tests"]["test_3_grounding_check"]

    assert test2["summary_counts"]["paper_count"] == 1
    assert test2["actual_nested_counts"]["review_with_claim_count"] == 1
    assert test3["reviewer_calibration_grounding"]["grounded_true_count"] == 2
    assert test3["reviewer_calibration_grounding"]["grounded_false_count"] == 1
    assert test3["grounding_validation_stats"]["raw_grounding_fail_count"] == 2


def test_presentation_checks_markdown_renders_sections():
    report = build_p0_report(sample_reviewer_calibration())
    markdown = render_p0_markdown(report)

    assert "Test 1 - Materiality Proxy x Resolution" in markdown
    assert "Test 2 - Sample Size Alignment" in markdown
    assert "Test 3 - Grounding Check" in markdown


def sample_reviewer_calibration():
    return {
        "calibration_version": "test",
        "source": {"llm_rebuttal_label_count": 3, "llm_consensus_label_count": 0},
        "summary": {"paper_count": 1, "review_count": 1, "claim_count": 3},
        "papers": [
            {
                "paper_id": "paper1",
                "reviews": [
                    {
                        "review_id": "review1",
                        "claims": [
                            {
                                "claim_text": "Missing ablations.",
                                "importance": "major",
                                "grounded": True,
                                "source_sentence": "Missing ablations.",
                                "rebuttal_resolution": {
                                    "llm_calibration": {
                                        "rebuttal_response_label": "not_addressed",
                                        "rebuttal_effect_on_claim": "does_not_address",
                                    }
                                },
                            },
                            {
                                "claim_text": "Need clearer baseline.",
                                "importance": "major",
                                "grounded": True,
                                "source_sentence": "Need clearer baseline.",
                                "rebuttal_resolution": {
                                    "llm_calibration": {
                                        "rebuttal_response_label": "specifically_addressed",
                                        "rebuttal_effect_on_claim": "partially_addresses",
                                    }
                                },
                            },
                            {
                                "claim_text": "Minor typo.",
                                "importance": "minor",
                                "grounded": False,
                                "source_sentence": "",
                                "rebuttal_resolution": {
                                    "llm_calibration": {
                                        "rebuttal_response_label": "likely_resolved",
                                        "rebuttal_effect_on_claim": "resolved_or_weakened",
                                    }
                                },
                            },
                        ],
                    }
                ],
            }
        ],
    }
