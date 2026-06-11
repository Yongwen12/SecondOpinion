from secondopinion.consensus_recalibration import (
    build_consensus_recalibration_report,
    render_consensus_recalibration_markdown,
)


def test_consensus_recalibration_demotes_related_but_different():
    report = build_consensus_recalibration_report(sample_calibration_report())

    assert report["summary"]["claim_count"] == 3
    assert report["summary"]["llm_consensus_claim_count"] == 2
    assert report["modes"]["current_labeled_only"]["claim_count"] == 2
    assert report["modes"]["strict_same_only_labeled"]["claim_count"] == 2

    diagnostics = report["diagnostics"]
    assert diagnostics["current_related_or_same_support_rate"] == 1.0
    assert diagnostics["strict_same_support_rate"] == 0.5
    assert diagnostics["related_demotion_count"] == 1

    comparison = report["comparisons"]["strict_labeled_vs_current_labeled"]
    assert comparison["claim_count"] == 2
    assert comparison["mean_signal_deltas"]["consensus"] == -0.275


def test_consensus_recalibration_markdown_renders_summary():
    report = build_consensus_recalibration_report(sample_calibration_report())
    markdown = render_consensus_recalibration_markdown(report)

    assert "# Consensus Recalibration" in markdown
    assert "strict_same_only_hybrid" in markdown
    assert "Related-but-different demotions" in markdown


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
                                    "matched_review_id": "review2",
                                    "matched_claim_text": "The experimental setup needs stronger baselines.",
                                    "llm_calibration": {
                                        "consensus_label": "same_concern",
                                    },
                                },
                                "rebuttal_resolution": {"label": "not_addressed"},
                                "discussion_followup": {"label": "not_found"},
                                "meta_review_uptake": {"label": "not_found"},
                            },
                            {
                                "claim_text": "The notation is unclear.",
                                "grounded": True,
                                "specificity_score": 1.0,
                                "consensus": {
                                    "label": "partial",
                                    "matched_review_id": "review2",
                                    "matched_claim_text": "The evaluation protocol is unclear.",
                                    "llm_calibration": {
                                        "consensus_label": "related_but_different",
                                    },
                                },
                                "rebuttal_resolution": {"label": "not_addressed"},
                                "discussion_followup": {"label": "not_found"},
                                "meta_review_uptake": {"label": "not_found"},
                            },
                            {
                                "claim_text": "The paper needs more examples.",
                                "grounded": True,
                                "specificity_score": 0.5,
                                "consensus": {"label": "partial"},
                                "rebuttal_resolution": {"label": "not_addressed"},
                                "discussion_followup": {"label": "not_found"},
                                "meta_review_uptake": {"label": "not_found"},
                            },
                        ],
                    }
                ],
            }
        ],
    }
