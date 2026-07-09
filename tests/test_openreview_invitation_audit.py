from secondopinion.openreview_invitation_audit import audit_invitation_candidates, expected_group_url, render_invitation_audit_markdown, valid_invitation


def test_expected_group_url_from_invitation():
    assert expected_group_url("ICLR.cc/2025/Conference/-/Submission") == "https://openreview.net/group?id=ICLR.cc/2025/Conference"
    assert expected_group_url("TMLR/-/Submission") == "https://openreview.net/group?id=TMLR"
    assert valid_invitation("TMLR/-/Submission") is True
    assert valid_invitation("bad invitation") is False


def test_invitation_audit_marks_ready_and_attention_cases():
    report = audit_invitation_candidates(
        [
            {
                "venue_id": "ICLR",
                "priority": 1,
                "scope_decision": "score_public_reviews",
                "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
                "evidence_urls": ["https://openreview.net/group?id=ICLR.cc/2025/Conference"],
            },
            {
                "venue_id": "AISTATS",
                "priority": 2,
                "scope_decision": "probe_then_score_if_public",
                "invitation_candidates": [
                    "AISTATS.cc/2025/Conference/-/Submission",
                    "aistats.org/AISTATS/2025/Conference/-/Submission",
                ],
                "evidence_urls": ["https://openreview.net/group?id=AISTATS.cc/2025/Conference"],
            },
            {
                "venue_id": "BROKEN",
                "priority": 2,
                "scope_decision": "probe_then_score_if_public",
                "invitation_candidates": ["bad invitation"],
                "evidence_urls": [],
            },
            {
                "venue_id": "JMLR",
                "priority": 3,
                "include_in_inventory": False,
                "scope_decision": "exclude_no_public_reviews",
                "invitation_candidates": [],
            },
        ]
    )
    by_id = {row["venue_id"]: row for row in report["venues"]}
    markdown = render_invitation_audit_markdown(report)

    assert by_id["ICLR"]["status"] == "ready_for_api_probe"
    assert by_id["AISTATS"]["status"] == "ready_for_multi_candidate_probe"
    assert "multiple_invitation_candidates" in by_id["AISTATS"]["issues"]
    assert "invalid_invitation_format" in by_id["BROKEN"]["issues"]
    assert by_id["JMLR"]["status"] == "excluded"
    assert report["summary"]["multi_candidate_ready"] == ["AISTATS"]
    assert report["summary"]["needs_attention"] == ["BROKEN"]
    assert report["summary"]["multi_candidate_venues"] == ["AISTATS"]
    assert "OpenReview Invitation Audit" in markdown
