from secondopinion.openreview_ingestion_plan import build_ingestion_plan, render_ingestion_plan_markdown


def test_rolling_venue_plan_filters_before_quality_and_scoring():
    inventory = {
        "created_at": "2026-07-06T00:00:00+00:00",
        "venues": [
            {
                "venue_id": "TMLR",
                "name": "Transactions on Machine Learning Research",
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

    plan = build_ingestion_plan(inventory)
    venue = plan["venues"][0]
    command_names = [command["name"] for command in venue["commands"]]
    markdown = render_ingestion_plan_markdown(plan)

    assert venue["readiness"] == "ready"
    assert venue["commands_enabled"] is True
    assert venue["paths"]["raw_normalized"] == "data/normalized/tmlr_2025_full_unfiltered.json"
    assert venue["paths"]["normalized"] == "data/normalized/tmlr_2025_full.json"
    assert command_names[:3] == ["pull", "filter_normalized", "quality"]
    assert "--mode decision_or_activity_year" in venue["commands"][1]["command"]
    assert "is applied before quality checks" in markdown
