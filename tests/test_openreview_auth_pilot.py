from pathlib import Path

from secondopinion.openreview_auth_pilot import run_openreview_auth_pilot
from secondopinion.openreview_client import OpenReviewAPIError


class FakeAuthClient:
    def __init__(self, *, ok=True):
        self.cookie = "openreview_session=ok"
        self.token = ""
        self.user_agent = "test"
        self.base_url = "https://api2.openreview.net"
        self.ok = ok

    def get_notes(self, invitation, *, limit=1, offset=0, details="replies"):
        if not self.ok:
            raise OpenReviewAPIError(403, '{"name":"ChallengeRequiredError","message":"Challenge verification required","challengeUrl":"x"}', "url")
        return {"notes": [{"id": "paper1"}]}


def test_auth_pilot_blocks_missing_cookie(tmp_path):
    report = run_openreview_auth_pilot(
        venue_specs=[],
        out_cookie=tmp_path / "openreview.cookie",
        env_path=tmp_path / ".env",
    )

    assert report["status"] == "blocked_cookie_setup"
    assert report["openai_submit_used"] is False


def test_auth_pilot_blocks_failed_auth_check(tmp_path):
    source = tmp_path / "cookie.txt"
    source.write_text("openreview_session=abc", encoding="utf-8")

    report = run_openreview_auth_pilot(
        venue_specs=[],
        cookie_file=str(source),
        out_cookie=tmp_path / "openreview.cookie",
        env_path=tmp_path / ".env",
        auth_client_factory=lambda: FakeAuthClient(ok=False),
    )

    assert report["status"] == "blocked_auth_check"
    assert report["auth_check"]["status"] == "challenge_required"
    assert report["safe_pipeline"] == {}


def test_auth_pilot_runs_safe_pipeline_dry_run_after_auth_ok(tmp_path):
    source = tmp_path / "cookie.txt"
    source.write_text("openreview_session=abc", encoding="utf-8")
    calls = []

    def fake_runner(**kwargs):
        calls.append(kwargs)
        return {
            "action": "dry_run_safe_stages",
            "gate_status": "ready_for_safe_runner_execute",
            "gate_recommendation": "Run safe runner.",
            "selected_venues": ["ICLR"],
            "pull_limit": 50,
            "safe_runner_status_counts": {"dry_run": 6},
            "pilot_readiness_status": "ready_for_pilot",
        }

    report = run_openreview_auth_pilot(
        venue_specs=[{"venue_id": "ICLR"}],
        cookie_file=str(source),
        out_cookie=tmp_path / "openreview.cookie",
        env_path=tmp_path / ".env",
        auth_client_factory=lambda: FakeAuthClient(ok=True),
        safe_pipeline_runner=fake_runner,
    )

    assert report["status"] == "pilot_ready_dry_run"
    assert calls[0]["execute_safe"] is False
    assert calls[0]["venues"] == ["ICLR"]
    assert report["safe_pipeline"]["safe_runner_status_counts"] == {"dry_run": 6}


def test_auth_pilot_reports_executed_safe_pilot(tmp_path):
    source = tmp_path / "cookie.txt"
    source.write_text("openreview_session=abc", encoding="utf-8")

    report = run_openreview_auth_pilot(
        venue_specs=[{"venue_id": "ICLR"}],
        cookie_file=str(source),
        out_cookie=tmp_path / "openreview.cookie",
        env_path=tmp_path / ".env",
        execute_safe=True,
        auth_client_factory=lambda: FakeAuthClient(ok=True),
        safe_pipeline_runner=lambda **kwargs: {
            "action": "executed_safe_stages",
            "gate_status": "ready_for_safe_runner_execute",
            "gate_recommendation": "Run safe runner.",
            "selected_venues": ["ICLR"],
            "pull_limit": 50,
            "safe_runner_status_counts": {"completed": 6},
        },
    )

    assert report["status"] == "pilot_executed"
    assert "openreview_pilot_readiness" in report["next_commands"][0]
