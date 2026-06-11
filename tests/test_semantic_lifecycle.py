from secondopinion.semantic_lifecycle import (
    apply_semantic_meta_to_calibration,
    build_semantic_lifecycle_report,
    render_semantic_lifecycle_markdown,
)


def test_semantic_lifecycle_replaces_meta_review_proxy_on_labeled_subset():
    report = build_semantic_lifecycle_report(sample_calibration_report(), sample_semantic_labels())

    assert report["summary"]["claim_count"] == 2
    assert report["summary"]["semantic_meta_matched_count"] == 2
    assert report["summary"]["semantic_meta_decisive_count"] == 1

    diag = report["semantic_meta_diagnostics"]
    assert diag["proxy_false_positive_count"] == 1
    assert diag["semantic_positive_rate"] == 0.0
    assert diag["proxy_positive_rate"] == 1.0

    comparison = report["comparisons"]["semantic_labeled_vs_current_subset"]
    assert comparison["claim_count"] == 1
    assert comparison["mean_meta_review_uptake_delta"] == -1.0
    assert comparison["mean_score_delta"] == -0.2


def test_apply_semantic_meta_to_calibration_adds_semantic_lifecycle_payload():
    updated = apply_semantic_meta_to_calibration(sample_calibration_report(), sample_semantic_labels())
    claim = updated["papers"][0]["reviews"][0]["claims"][0]

    assert claim["meta_review_uptake"]["proxy_label"] == "survived"
    assert claim["meta_review_uptake"]["label"] == "not_found"
    assert claim["lifecycle_robustness_semantic_meta"]["signal_scores"]["meta_review_uptake"] == 0.0


def test_semantic_lifecycle_markdown_renders_summary():
    report = build_semantic_lifecycle_report(sample_calibration_report(), sample_semantic_labels())
    markdown = render_semantic_lifecycle_markdown(report)

    assert "# Semantic Meta-Review Lifecycle Recalibration" in markdown
    assert "semantic_labeled_only" in markdown
    assert "Proxy false-positive candidates" in markdown


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
                                "consensus": {"label": "none"},
                                "rebuttal_resolution": {"label": "not_addressed"},
                                "discussion_followup": {"label": "not_found"},
                                "meta_review_uptake": {"label": "survived", "score": 1.0},
                            },
                            {
                                "claim_text": "The writing is unclear.",
                                "grounded": True,
                                "specificity_score": 0.5,
                                "consensus": {"label": "partial"},
                                "rebuttal_resolution": {"label": "addressed_unclear_resolution"},
                                "discussion_followup": {"label": "not_found"},
                                "meta_review_uptake": {"label": "partial", "score": 0.6},
                            },
                        ],
                    }
                ],
            }
        ],
    }


def sample_semantic_labels():
    return [
        {
            "paper_id": "paper1",
            "review_id": "review1",
            "claim_index": 0,
            "llm_label_id": "label1",
            "llm_meta_review_match": "not_found",
            "llm_ac_treatment": "not_mentioned",
            "llm_concern_quality": "high",
            "llm_confidence": "high",
            "llm_label_evidence_strength": "high",
            "llm_training_use": "include",
            "llm_rationale": "The meta-review does not mention this specific baseline concern.",
            "high_confidence_training_candidate": True,
        },
        {
            "paper_id": "paper1",
            "review_id": "review1",
            "claim_index": 1,
            "llm_label_id": "label2",
            "llm_meta_review_match": "unsure",
            "llm_ac_treatment": "unclear",
            "llm_concern_quality": "unsure",
            "llm_confidence": "low",
            "llm_label_evidence_strength": "low",
            "llm_training_use": "exclude",
            "llm_rationale": "Ambiguous.",
            "high_confidence_training_candidate": False,
        },
    ]
