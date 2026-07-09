from secondopinion.openreview_probe_queue import build_probe_queue


def test_probe_queue_builds_candidate_level_commands():
    report = build_probe_queue(
        venues=[
            {
                "venue_id": "ICLR",
                "priority": 1,
                "scope_decision": "score_public_reviews",
                "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
                "evidence_urls": ["https://openreview.net/group?id=ICLR.cc/2025/Conference"],
            },
            {
                "venue_id": "UAI",
                "priority": 2,
                "scope_decision": "probe_then_score_if_public",
                "invitation_candidates": ["auai.org/UAI/2025/Conference/-/Submission", "UAI.cc/2025/Conference/-/Submission"],
                "evidence_urls": ["https://openreview.net/group?id=auai.org/UAI/2025/Conference"],
            },
            {"venue_id": "JMLR", "priority": 3, "scope_decision": "exclude_no_public_reviews", "include_in_inventory": False},
        ],
        sample_limit=25,
    )

    assert report["summary"]["probe_count"] == 3
    assert report["summary"]["multi_candidate_probe_count"] == 2
    assert report["items"][0]["venue_id"] == "ICLR"
    assert report["items"][0]["result_json"] == "data/validation/openreview_probe_iclr_c1_25.json"
    assert report["items"][0]["result_markdown"] == "reports/validation/openreview_probe_iclr_c1_25.md"
    assert "openreview_probe_invitation" in report["items"][0]["command"]
    assert "--sample-limit 25" in report["items"][0]["command"]
    assert "openreview_probe_uai_c1_25.json" in report["items"][1]["command"]
    assert "openreview_probe_uai_c2_25.json" in report["items"][2]["command"]
