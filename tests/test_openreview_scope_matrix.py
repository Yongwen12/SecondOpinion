from secondopinion.openreview_scope_matrix import build_scope_matrix, render_scope_matrix_markdown


def test_scope_matrix_classifies_target_probe_and_excluded_venues():
    report = build_scope_matrix(
        venues=[
            {
                "venue_id": "ICLR",
                "year": 2025,
                "category": "top_conference",
                "priority": 1,
                "scope_decision": "score_public_reviews",
                "review_policy": "fully_open_public_reviews",
                "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
            },
            {
                "venue_id": "COLM",
                "year": 2025,
                "category": "top_conference",
                "priority": 2,
                "scope_decision": "probe_then_score_if_public",
                "review_policy": "verify_public_review_coverage",
                "invitation_candidates": ["colmweb.org/2025/Conference/-/Submission"],
            },
            {
                "venue_id": "JMLR",
                "year": 2025,
                "category": "top_journal",
                "priority": 3,
                "scope_decision": "exclude_no_public_reviews",
                "include_in_inventory": False,
            },
        ],
        inventory={
            "venues": [
                {"venue_id": "ICLR", "status": "open_reviews_available", "selected_invitation": "ICLR.cc/2025/Conference/-/Submission", "public_review_evidence": {"state": "api_confirmed_public_reviews"}},
                {"venue_id": "COLM", "status": "challenge_required", "recommendation": "retry_with_openreview_cookie", "public_review_evidence": {"state": "candidate_requires_api_probe"}},
                {"venue_id": "JMLR", "status": "excluded_no_public_reviews"},
            ]
        },
    )
    markdown = render_scope_matrix_markdown(report)

    assert report["summary"]["target_or_probe"] == ["ICLR", "COLM"]
    assert report["summary"]["excluded"] == ["JMLR"]
    assert report["summary"]["ready_to_pull"] == ["ICLR"]
    assert report["summary"]["blocked_openreview_auth"] == ["COLM"]
    assert report["venues"][0]["public_review_evidence_state"] == "api_confirmed_public_reviews"
    assert "OpenReview 2025 Scope Matrix" in markdown
    assert "probe_then_score_if_public" in markdown
    assert "candidate_requires_api_probe" in markdown


def test_scope_matrix_marks_unprobed_targets_before_inventory_exists():
    report = build_scope_matrix(
        venues=[
            {
                "venue_id": "TMLR",
                "year": 2025,
                "category": "top_journal",
                "priority": 1,
                "scope_decision": "score_public_reviews",
                "rolling_venue": True,
                "invitation_candidates": ["TMLR/-/Submission"],
            }
        ],
        inventory=None,
    )

    assert report["summary"]["needs_inventory_probe"] == ["TMLR"]
    assert report["venues"][0]["execution_state"] == "needs_inventory_probe"
