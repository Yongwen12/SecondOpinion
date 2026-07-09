from secondopinion.openreview_execution_runbook import (
    build_openreview_execution_runbook,
    render_openreview_execution_runbook_markdown,
)


def venue(venue_id, decision, priority=1, include=True):
    return {
        "venue_id": venue_id,
        "year": 2025,
        "priority": priority,
        "scope_decision": decision,
        "include_in_inventory": include,
    }


def test_execution_runbook_orders_cookie_pilot_full_probe_submit_phases():
    runbook = build_openreview_execution_runbook(
        venue_specs=[
            venue("ICLR", "score_public_reviews", priority=1),
            venue("TMLR", "score_public_reviews", priority=1),
            venue("COLM", "probe_then_score_if_public", priority=2),
            venue("JMLR", "exclude_no_public_reviews", priority=3, include=False),
        ],
        venues_path="venues.json",
        sample_limit=25,
        max_submit_cost_usd=3.0,
        batch_cost_limit_usd=4.0,
    )
    markdown = render_openreview_execution_runbook_markdown(runbook)

    assert runbook["summary"]["core_priority1"] == ["ICLR", "TMLR"]
    assert runbook["summary"]["probe_priority2"] == ["COLM"]
    assert runbook["summary"]["excluded"] == ["JMLR"]
    assert [phase["phase"] for phase in runbook["phases"]] == [
        "install_cookie_and_probe_inventory",
        "priority1_pilots",
        "priority1_full_pull_and_batch_build",
        "priority2_public_review_probe",
        "batch_submit_after_cost_review",
    ]
    assert "--venue ICLR --pull-limit 25" in markdown
    full_commands = runbook["phases"][2]["commands"]
    assert any("--venue ICLR" in command and "--execute-safe" in command and "--pull-limit" not in command for command in full_commands)
    assert "openreview_challenge_resume" in markdown
    assert "--execute-probe --skip-existing" in markdown
    assert "--include-costly --stage submit_batch" in markdown
    assert "human approval for OpenAI spend" in markdown
