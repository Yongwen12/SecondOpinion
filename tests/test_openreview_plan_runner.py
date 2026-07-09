from secondopinion.openreview_plan_runner import run_plan_steps, select_plan_steps


def sample_plan(readiness="ready", commands_enabled=True):
    return {
        "venues": [
            {
                "venue_id": "ICLR",
                "readiness": readiness,
                "blocked_reason": "OpenReview challenge/auth required" if not commands_enabled else "",
                "commands_enabled": commands_enabled,
                "commands": [
                    {"name": "pull", "command": "python -m secondopinion.tools.openreview_pull --venue ICLR"},
                    {"name": "quality", "command": "python -m secondopinion.tools.data_quality_report --input x"},
                    {"name": "submit_batch", "command": "python -m secondopinion.tools.submit_scoring_batch --input x"},
                ],
            },
            {
                "venue_id": "TMLR",
                "readiness": "ready",
                "commands_enabled": True,
                "commands": [
                    {"name": "pull", "command": "python -m secondopinion.tools.openreview_pull --venue TMLR"},
                    {"name": "filter_normalized", "command": "python -m secondopinion.tools.filter_normalized --input x"},
                ],
            },
        ]
    }


def test_select_plan_steps_skips_blocked_venues_by_default():
    steps = select_plan_steps(sample_plan(readiness="blocked_openreview_auth", commands_enabled=False))

    assert steps[0]["venue_id"] == "ICLR"
    assert steps[0]["status"] == "skipped"
    assert steps[0]["reason"] == "OpenReview challenge/auth required"
    assert any(step["venue_id"] == "TMLR" and step["status"] == "pending" for step in steps)


def test_select_plan_steps_filters_venue_stage_and_costly_steps():
    steps = select_plan_steps(sample_plan(), venues=["iclr"], stages=["pull", "submit_batch"])

    assert [step["name"] for step in steps] == ["pull", "submit_batch"]
    assert steps[0]["status"] == "pending"
    assert steps[1]["status"] == "skipped"
    assert steps[1]["reason"] == "costly_step_requires_include_costly"


def test_run_plan_steps_defaults_to_dry_run():
    steps = select_plan_steps(sample_plan(), venues=["TMLR"])
    result = run_plan_steps(steps)

    assert result["execute"] is False
    assert result["status_counts"]["dry_run"] == 2
    assert result["steps"][0]["command"].startswith("python -m secondopinion.tools.openreview_pull")
