from secondopinion.lifecycle_ablation import build_lifecycle_ablation_report, render_lifecycle_ablation_markdown


def test_lifecycle_ablation_quantifies_proxy_vs_llm_subset():
    report = build_lifecycle_ablation_report(sample_calibration_report())

    assert report["summary"]["claim_count"] == 2
    assert report["summary"]["any_llm_claim_count"] == 1
    assert report["modes"]["proxy_only"]["claim_count"] == 2
    assert report["modes"]["hybrid"]["claim_count"] == 2
    assert report["modes"]["llm_calibrated_only"]["claim_count"] == 1
    assert report["modes"]["strict_both_llm"]["claim_count"] == 1

    subset = report["comparisons"]["llm_subset_hybrid_vs_proxy"]
    assert subset["claim_count"] == 1
    assert subset["mean_signal_deltas"]["consensus"] == -0.55
    assert subset["mean_signal_deltas"]["rebuttal_robustness"] == 0.3

    diagnostics = report["lexical_proxy_diagnostics"]
    assert diagnostics["rebuttal"]["lexical_false_positive_candidate_count"] == 1
    assert diagnostics["consensus"]["lexical_false_positive_candidate_count"] == 1


def test_lifecycle_ablation_markdown_renders_key_sections():
    report = build_lifecycle_ablation_report(sample_calibration_report())
    markdown = render_lifecycle_ablation_markdown(report)

    assert "# Lifecycle Proxy Ablation" in markdown
    assert "proxy_only" in markdown
    assert "Lexical Proxy Diagnostics" in markdown


def sample_calibration_report():
    return {
        "calibration_version": "test",
        "papers": [
            {
                "paper_id": "paper1",
                "reviews": [
                    {
                        "review_id": "review1",
                        "claims": [
                            {
                                "claim_text": "The paper lacks a baseline.",
                                "grounded": True,
                                "specificity_score": 1.0,
                                "consensus": {
                                    "label": "partial",
                                    "llm_calibration": {
                                        "consensus_label": "not_same_concern",
                                    },
                                },
                                "rebuttal_resolution": {
                                    "label": "addressed_unclear_resolution",
                                    "llm_calibration": {
                                        "rebuttal_response_label": "not_addressed",
                                        "rebuttal_effect_on_claim": "does_not_address",
                                    },
                                },
                                "discussion_followup": {"label": "not_found"},
                                "meta_review_uptake": {"label": "not_found"},
                            },
                            {
                                "claim_text": "The writing is unclear.",
                                "grounded": True,
                                "specificity_score": 0.5,
                                "consensus": {"label": "none"},
                                "rebuttal_resolution": {"label": "not_addressed"},
                                "discussion_followup": {"label": "followed_up"},
                                "meta_review_uptake": {"label": "partial"},
                            },
                        ],
                    }
                ],
            }
        ],
    }
