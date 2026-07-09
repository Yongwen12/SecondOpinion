from pathlib import Path

from secondopinion.openreview_challenge_resume import run_openreview_challenge_resume
from secondopinion.openreview_client import OpenReviewAPIError
from tests.test_openreview_venue_inventory import paper


class FakeClient:
    cookie = "openreview_session=ok"
    token = ""
    user_agent = "test"
    base_url = "https://api2.openreview.net"

    def __init__(self, *, ok=True, notes=None):
        self.ok = ok
        self.notes = notes if notes is not None else [paper()]

    def get_notes(self, invitation, *, limit=1, offset=0, details="replies"):
        if not self.ok:
            raise OpenReviewAPIError(403, '{"name":"ChallengeRequiredError","message":"Challenge verification required"}', "url")
        return {"notes": self.notes[:limit]}


def venue_specs():
    return [
        {
            "venue_id": "ICLR",
            "year": 2025,
            "priority": 1,
            "scope_decision": "score_public_reviews",
            "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
        }
    ]


def run_kwargs(tmp_path: Path):
    probe_out = tmp_path / "probe-json"
    probe_md = tmp_path / "probe-md"
    return {
        "paths": paths(tmp_path),
        "probe_output_dir": probe_out,
        "probe_report_dir": probe_md,
        "probe_result_patterns": [str(probe_out / "*.json")],
    }


def paths(tmp_path: Path):
    return {
        "auth_check": str(tmp_path / "auth.json"),
        "probe_queue": str(tmp_path / "probe_queue.json"),
        "probe_queue_markdown": str(tmp_path / "probe_queue.md"),
        "probe_runner": str(tmp_path / "runner.json"),
        "probe_runner_markdown": str(tmp_path / "runner.md"),
        "probe_results": str(tmp_path / "probe_results.json"),
        "probe_results_markdown": str(tmp_path / "probe_results.md"),
        "resolved_inventory": str(tmp_path / "resolved_inventory.json"),
        "resolved_inventory_markdown": str(tmp_path / "resolved_inventory.md"),
        "summary": str(tmp_path / "summary.json"),
        "summary_markdown": str(tmp_path / "summary.md"),
    }


def test_challenge_resume_blocks_bad_cookie_setup(tmp_path):
    report = run_openreview_challenge_resume(
        venue_specs=venue_specs(),
        cookie_file=str(tmp_path / "missing-cookie.txt"),
        out_cookie=tmp_path / "openreview.cookie",
        env_path=tmp_path / ".env",
        **run_kwargs(tmp_path),
        client_factory=lambda: FakeClient(ok=True),
    )

    assert report["status"] == "blocked_cookie_setup"
    assert report["auth_diagnosis"]["reason"] == "cookie_setup_failed"
    assert report["openai_submit_used"] is False


def test_challenge_resume_blocks_missing_secret_before_network(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = run_openreview_challenge_resume(
        venue_specs=venue_specs(),
        **run_kwargs(tmp_path),
        client_factory=lambda: FakeClient(ok=False),
    )

    assert report["status"] == "blocked_missing_secret"
    assert report["auth_check"] == {}
    assert report["auth_diagnosis"]["reason"] == "missing_cookie_or_token"
    assert Path(report["paths"]["summary"]).exists()


def test_challenge_resume_can_force_anonymous_auth_check(tmp_path):
    report = run_openreview_challenge_resume(
        venue_specs=venue_specs(),
        require_secret=False,
        **run_kwargs(tmp_path),
        client_factory=lambda: FakeClient(ok=False),
    )

    assert report["status"] == "blocked_auth_check"
    assert report["auth_check"]["status"] == "challenge_required"


def test_challenge_resume_dry_runs_probe_after_auth_ok(tmp_path):
    report = run_openreview_challenge_resume(
        venue_specs=venue_specs(),
        execute_probe=False,
        require_secret=False,
        **run_kwargs(tmp_path),
        client_factory=lambda: FakeClient(ok=True),
    )

    assert report["status"] == "auth_ok_probe_dry_run"
    assert report["auth_diagnosis"]["reason"] == "auth_ok"
    assert report["probe_runner"]["status_counts"] == {"dry_run": 1}
    assert report["openai_submit_used"] is False


def test_challenge_resume_executes_probe_and_builds_ready_inventory(tmp_path):
    report = run_openreview_challenge_resume(
        venue_specs=venue_specs(),
        execute_probe=True,
        require_secret=False,
        **run_kwargs(tmp_path),
        client_factory=lambda: FakeClient(ok=True, notes=[paper()]),
    )

    assert report["status"] == "ready_for_safe_execute"
    assert report["probe_runner"]["status_counts"] == {"success": 1}
    assert report["probe_results_summary"]["selected_for_scoring"] == ["ICLR"]
    assert report["resolved_inventory_summary"]["ready_to_pull_and_score"] == ["ICLR"]
