from secondopinion.openreview_ingestion_plan import build_ingestion_plan, render_ingestion_plan_markdown


def inventory_with(status: str):
    ready_statuses = {"open_reviews_available", "partial_public_reviews"}
    return {
        "created_at": "2026-07-06T00:00:00+00:00",
        "venues": [
            {
                "venue_id": "ICLR",
                "name": "International Conference on Learning Representations",
                "year": 2025,
                "status": status,
                "recommendation": "pull_and_score" if status in ready_statuses else "retry_with_openreview_cookie",
                "selected_invitation": "ICLR.cc/2025/Conference/-/Submission" if status in ready_statuses else "",
                "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
                "sample_stats": {"paper_count": 25, "review_count": 75},
            }
        ],
    }


def test_ingestion_plan_builds_ready_pull_score_queue():
    plan = build_ingestion_plan(inventory_with("open_reviews_available"), model="gpt-5.4-nano")
    venue = plan["venues"][0]

    assert plan["summary"]["ready"] == ["ICLR"]
    assert venue["commands_enabled"] is True
    assert venue["dataset_slug"] == "iclr_2025_full"
    assert venue["paths"]["normalized"] == "data/normalized/iclr_2025_full.json"
    assert "python -m secondopinion.tools.openreview_pull" in venue["commands"][0]["command"]
    assert "--invitation ICLR.cc/2025/Conference/-/Submission" in venue["commands"][0]["command"]
    assert "--polite-delay 0.2" in venue["commands"][0]["command"]
    assert "--snapshot iclr_2025_full" in venue["commands"][0]["command"]
    assert venue["paths"]["snapshot_id"] == "iclr_2025_full"
    assert "--model gpt-5.4-nano" in venue["commands"][3]["command"]


def test_ingestion_plan_marks_challenge_as_auth_blocked():
    plan = build_ingestion_plan(inventory_with("challenge_required"))
    venue = plan["venues"][0]
    markdown = render_ingestion_plan_markdown(plan)

    assert plan["summary"]["blocked_openreview_auth"] == ["ICLR"]
    assert venue["commands_enabled"] is False
    assert venue["readiness"] == "blocked_openreview_auth"
    assert venue["commands"][0]["requires_openreview_auth"] is True
    assert "Commands are recorded for handoff" in markdown


def test_ingestion_plan_treats_partial_public_reviews_as_ready():
    plan = build_ingestion_plan(inventory_with("partial_public_reviews"))
    venue = plan["venues"][0]

    assert plan["summary"]["ready"] == ["ICLR"]
    assert venue["readiness"] == "ready"
    assert venue["commands_enabled"] is True

def test_ingestion_plan_excludes_non_public_review_journals():
    plan = build_ingestion_plan(
        {
            "created_at": "2026-07-06T00:00:00+00:00",
            "venues": [
                {
                    "venue_id": "JMLR",
                    "name": "Journal of Machine Learning Research",
                    "year": 2025,
                    "status": "excluded_no_public_reviews",
                    "recommendation": "skip_no_public_reviews",
                    "category": "top_journal",
                }
            ],
        }
    )
    venue = plan["venues"][0]

    assert venue["readiness"] == "excluded_not_scored"
    assert venue["commands_enabled"] is False
    assert venue["commands"] == []
    assert plan["summary"]["excluded_not_scored"] == ["JMLR"]


def test_ingestion_plan_can_limit_pull_for_small_pilot():
    plan = build_ingestion_plan(inventory_with("open_reviews_available"), pull_limit=50)
    venue = plan["venues"][0]

    assert plan["pull_limit"] == 50
    assert venue["pull_limit"] == 50
    assert venue["dataset_slug"] == "iclr_2025_sample50"
    assert venue["paths"]["normalized"] == "data/normalized/iclr_2025_sample50.json"
    assert venue["paths"]["quality_json"] == "data/validation/iclr_2025_sample50_quality.json"
    assert venue["paths"]["batch_manifest"] == "data/batch/iclr_2025_sample50_batch_manifest.json"
    assert "--output data/normalized/iclr_2025_sample50.json" in venue["commands"][0]["command"]
    assert "--snapshot iclr_2025_sample50" in venue["commands"][0]["command"]
    assert "--limit 50" in venue["commands"][0]["command"]
    assert venue["commands"][0]["limit"] == 50


def test_ingestion_plan_limits_rolling_venue_without_overwriting_full_paths():
    inventory = {
        "created_at": "2026-07-06T00:00:00+00:00",
        "venues": [
            {
                "venue_id": "TMLR",
                "year": 2025,
                "status": "open_reviews_available",
                "recommendation": "pull_and_score",
                "rolling_venue": True,
                "year_filter": "decision_or_activity_year",
                "selected_invitation": "TMLR/-/Submission",
                "invitation_candidates": ["TMLR/-/Submission"],
            }
        ],
    }
    plan = build_ingestion_plan(inventory, pull_limit=25)
    venue = plan["venues"][0]

    assert venue["dataset_slug"] == "tmlr_2025_sample25"
    assert venue["paths"]["raw_normalized"] == "data/normalized/tmlr_2025_sample25_unfiltered.json"
    assert venue["paths"]["normalized"] == "data/normalized/tmlr_2025_sample25.json"
    assert "--output data/normalized/tmlr_2025_sample25_unfiltered.json" in venue["commands"][0]["command"]
    assert "--snapshot tmlr_2025_sample25" in venue["commands"][0]["command"]
    assert "--input data/normalized/tmlr_2025_sample25_unfiltered.json" in venue["commands"][1]["command"]
