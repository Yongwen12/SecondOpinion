from secondopinion.openreview_ingestion_plan import build_ingestion_plan
from secondopinion.openreview_resolved_inventory import build_resolved_inventory


def specs():
    return [
        {
            "venue_id": "ICLR",
            "name": "International Conference on Learning Representations",
            "year": 2025,
            "priority": 1,
            "scope_decision": "score_public_reviews",
            "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
        },
        {
            "venue_id": "AISTATS",
            "year": 2025,
            "priority": 2,
            "scope_decision": "probe_then_score_if_public",
            "invitation_candidates": ["AISTATS.cc/2025/Conference/-/Submission"],
        },
        {
            "venue_id": "JMLR",
            "year": 2025,
            "priority": 3,
            "include_in_inventory": False,
            "manual_status": "excluded_no_public_reviews",
            "scope_decision": "exclude_no_public_reviews",
        },
    ]


def test_resolved_inventory_turns_selected_probe_into_ready_plan():
    probe_results = {
        "created_at": "2026-07-06T00:00:00+00:00",
        "venues": [
            {
                "venue_id": "ICLR",
                "status": "selected_public_reviews",
                "selected_invitation": "ICLR.cc/2025/Conference/-/Submission",
                "candidates": [
                    {
                        "invitation": "ICLR.cc/2025/Conference/-/Submission",
                        "paper_count": 50,
                        "review_count": 150,
                        "review_coverage_rate": 1.0,
                        "mean_reviews_per_paper": 3.0,
                    }
                ],
            }
        ],
    }

    inventory = build_resolved_inventory(venue_specs=specs(), probe_results=probe_results)
    by_id = {venue["venue_id"]: venue for venue in inventory["venues"]}
    plan = build_ingestion_plan(inventory, pull_limit=50)

    assert by_id["ICLR"]["status"] == "open_reviews_available"
    assert by_id["ICLR"]["recommendation"] == "pull_and_score"
    assert by_id["ICLR"]["sample_stats"]["review_count"] == 150
    assert by_id["AISTATS"]["status"] == "missing_probe_results"
    assert by_id["JMLR"]["status"] == "excluded_no_public_reviews"
    assert inventory["summary"]["ready_to_pull_and_score"] == ["ICLR"]
    assert plan["summary"]["ready"] == ["ICLR"]
    assert plan["venues"][0]["commands_enabled"] is True


def test_resolved_inventory_maps_probe_auth_block_to_challenge_required():
    inventory = build_resolved_inventory(
        venue_specs=specs()[:1],
        probe_results={"venues": [{"venue_id": "ICLR", "status": "blocked_auth"}]},
    )

    assert inventory["venues"][0]["status"] == "challenge_required"
    assert inventory["summary"]["blocked_openreview_auth"] == ["ICLR"]


def test_resolved_inventory_keeps_low_coverage_probe_out_of_pull_queue():
    venues = [
        {
            "venue_id": "AISTATS",
            "name": "AISTATS",
            "year": 2025,
            "priority": 2,
            "scope_decision": "probe_then_score_if_public",
            "invitation_candidates": ["AISTATS.cc/2025/Conference/-/Submission"],
        }
    ]
    probe_results = {
        "venues": [
            {
                "venue_id": "AISTATS",
                "status": "needs_larger_probe",
                "selected_invitation": "AISTATS.cc/2025/Conference/-/Submission",
                "candidates": [
                    {
                        "invitation": "AISTATS.cc/2025/Conference/-/Submission",
                        "paper_count": 10,
                        "review_count": 2,
                        "review_coverage_rate": 0.2,
                        "mean_reviews_per_paper": 0.2,
                    }
                ],
            }
        ]
    }

    report = build_resolved_inventory(venue_specs=venues, probe_results=probe_results)

    assert report["summary"]["ready_to_pull_and_score"] == []
    assert report["summary"]["needs_larger_probe"] == ["AISTATS"]
    assert report["venues"][0]["recommendation"] == "rerun_larger_probe_before_full_pull"
