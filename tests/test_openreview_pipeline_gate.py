import json

from secondopinion.openreview_client import OpenReviewAPIError
from secondopinion.openreview_pipeline_gate import run_openreview_pipeline_gate


def content(**values):
    return {key: {"value": value} for key, value in values.items()}


def review(note_id):
    return {
        "id": note_id,
        "forum": "paper1",
        "invitations": ["ICLR.cc/2025/Conference/Submission1/-/Official_Review"],
        "content": content(summary="Useful.", rating="8: accept"),
        "cdate": 1000,
    }


def paper():
    return {
        "id": "paper1",
        "forum": "paper1",
        "content": content(title="A paper"),
        "details": {"replies": [review("review1")]},
    }


class FakeClient:
    user_agent = "test"
    base_url = "https://api2.openreview.net"

    def __init__(self, *, error=None, payload=None, cookie="", token=""):
        self.error = error
        self.payload = payload or {"notes": [paper()]}
        self.cookie = cookie
        self.token = token

    def get_notes(self, invitation, *, limit=50, details="replies", offset=0):
        if self.error:
            raise self.error
        return self.payload


def venue_specs():
    return [
        {
            "venue_id": "ICLR",
            "year": 2025,
            "category": "top_conference",
            "scope": "all_submissions",
            "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
        }
    ]


def challenge_error():
    return OpenReviewAPIError(
        403,
        json.dumps(
            {
                "name": "ChallengeRequiredError",
                "message": "Challenge verification required",
                "challengeUrl": "https://openreview.net/challenge",
            }
        ),
        "https://api2.openreview.net/notes",
    )


def secret_check(ok=False):
    return {
        "ok": ok,
        "recommendation": "run_openreview_pipeline_gate" if ok else "set_openreview_cookie_file_or_token",
        "cookie": {"set": ok, "cookie_names": ["openreview_session"] if ok else []},
        "token": {"set": False},
    }


def test_pipeline_gate_stops_before_inventory_when_auth_blocked():
    result = run_openreview_pipeline_gate(
        venue_specs=venue_specs(),
        auth_client=FakeClient(error=challenge_error()),
        secret_check=secret_check(False),
    )

    assert result["status"] == "blocked_openreview_auth"
    assert result["secret_check"]["ok"] is False
    assert result["ran_inventory"] is False
    assert result["ran_runner_dry_run"] is False
    assert result["auth"]["status"] == "challenge_required"


def test_pipeline_gate_reports_configured_secret_even_if_auth_blocked():
    result = run_openreview_pipeline_gate(
        venue_specs=venue_specs(),
        auth_client=FakeClient(error=challenge_error(), cookie="session=abc"),
        secret_check=secret_check(True),
    )

    assert result["status"] == "blocked_openreview_auth"
    assert result["secret_check"]["ok"] is True
    assert result["auth"]["environment"]["cookie_set"] is True


def test_pipeline_gate_builds_plan_and_runner_when_auth_ok():
    result = run_openreview_pipeline_gate(
        venue_specs=venue_specs(),
        auth_client=FakeClient(cookie="session=abc"),
        secret_check=secret_check(True),
        max_submit_cost_usd=7.5,
    )

    assert result["status"] == "ready_for_safe_runner_execute"
    assert result["secret_check"]["ok"] is True
    assert result["inventory_summary"]["ready_to_pull_and_score"] == ["ICLR"]
    assert result["plan_summary"]["ready"] == ["ICLR"]
    assert result["runner_status_counts"]["dry_run"] >= 1
    assert result["max_submit_cost_usd"] == 7.5
    assert result["scope_matrix_summary"]["ready_to_pull"] == ["ICLR"]


def test_pipeline_gate_markdown_shows_blocked_secret_next_step():
    from secondopinion.openreview_pipeline_gate import render_pipeline_gate_markdown

    result = run_openreview_pipeline_gate(
        venue_specs=venue_specs(),
        auth_client=FakeClient(error=challenge_error()),
        secret_check=secret_check(False),
    )
    markdown = render_pipeline_gate_markdown(result)

    assert "# OpenReview Pipeline Gate" in markdown
    assert "blocked_openreview_auth" in markdown
    assert "openreview_auth_setup" in markdown
    assert "openreview_pipeline_gate" in markdown
    assert "openreview_scope_matrix" in markdown
    assert "openreview_safe_pipeline" in markdown


def test_pipeline_gate_markdown_shows_execute_command_when_ready():
    from secondopinion.openreview_pipeline_gate import render_pipeline_gate_markdown

    result = run_openreview_pipeline_gate(
        venue_specs=venue_specs(),
        auth_client=FakeClient(cookie="session=abc"),
        secret_check=secret_check(True),
        max_submit_cost_usd=7.5,
    )
    markdown = render_pipeline_gate_markdown(result)

    assert "ready_for_safe_runner_execute" in markdown
    assert "openreview_safe_pipeline" in markdown
    assert "--execute-safe" in markdown
    assert "--max-submit-cost-usd 7.5" in markdown
    assert "openreview_safe_pipeline" in markdown
    assert "--execute-safe" in markdown
    assert "openreview_scope_matrix" in markdown

def test_pipeline_gate_includes_scope_audit_payload():
    result = run_openreview_pipeline_gate(
        venue_specs=venue_specs(),
        auth_client=FakeClient(error=challenge_error()),
        secret_check=secret_check(False),
    )

    assert "scope_audit" in result
    assert "scope_matrix" in result
    assert result["scope_audit_status"] == "failed"
    assert any("missing required core venue" in error for error in result["scope_audit_errors"])
