import json
import uuid
from pathlib import Path

from secondopinion.openreview_client import OpenReviewAPIError
import secondopinion.openreview_safe_pipeline as safe_pipeline
from secondopinion.openreview_safe_pipeline import run_openreview_safe_pipeline


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

    def __init__(self, *, error=None, cookie="session=abc"):
        self.error = error
        self.cookie = cookie
        self.token = ""

    def get_notes(self, invitation, *, limit=50, details="replies", offset=0):
        if self.error:
            raise self.error
        return {"notes": [paper()]}


def challenge_error():
    return OpenReviewAPIError(
        403,
        json.dumps({"name": "ChallengeRequiredError", "message": "Challenge verification required"}),
        "https://api2.openreview.net/notes",
    )


def venue_specs():
    return [
        {
            "venue_id": "ICLR",
            "year": 2025,
            "category": "top_conference",
            "priority": 1,
            "scope_decision": "score_public_reviews",
            "scope": "all_submissions",
            "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
        },
        {
            "venue_id": "ICML",
            "year": 2025,
            "category": "top_conference",
            "priority": 1,
            "scope_decision": "score_public_reviews",
            "scope": "accepted_plus_public_opt_in",
            "invitation_candidates": ["ICML.cc/2025/Conference/-/Submission"],
        },
        {
            "venue_id": "NEURIPS",
            "year": 2025,
            "category": "top_conference",
            "priority": 1,
            "scope_decision": "score_public_reviews",
            "scope": "accepted_plus_public_opt_in",
            "invitation_candidates": ["NeurIPS.cc/2025/Conference/-/Submission"],
        },
        {
            "venue_id": "TMLR",
            "year": 2025,
            "category": "top_journal",
            "priority": 1,
            "scope_decision": "score_public_reviews",
            "scope": "rolling_2025_decision_or_activity",
            "rolling_venue": True,
            "year_filter": "decision_or_activity_year",
            "invitation_candidates": ["TMLR/-/Submission"],
        },
        {
            "venue_id": "JMLR",
            "year": 2025,
            "category": "top_journal",
            "priority": 3,
            "scope_decision": "exclude_no_public_reviews",
            "include_in_inventory": False,
            "manual_status": "excluded_no_public_reviews",
            "invitation_candidates": [],
        },
        {
            "venue_id": "JAIR",
            "year": 2025,
            "category": "top_journal",
            "priority": 3,
            "scope_decision": "exclude_no_public_reviews",
            "include_in_inventory": False,
            "manual_status": "excluded_no_public_reviews",
            "invitation_candidates": [],
        },
        {
            "venue_id": "MLJ",
            "year": 2025,
            "category": "top_journal",
            "priority": 3,
            "scope_decision": "exclude_no_public_reviews",
            "include_in_inventory": False,
            "manual_status": "excluded_no_public_reviews",
            "invitation_candidates": [],
        },
    ]


def temp_paths(root):
    names = [
        "auth_out", "inventory_out", "inventory_markdown", "plan_out", "plan_markdown",
        "runner_out", "runner_markdown", "scope_audit_out", "scope_audit_markdown",
        "scope_matrix_out", "scope_matrix_markdown", "gate_out", "gate_markdown",
        "safe_runner_out", "safe_runner_markdown", "cost_out", "cost_markdown",
        "summary_out", "summary_markdown", "auth_setup_out", "pilot_readiness_out", "pilot_readiness_markdown",
        "scale_estimate_out", "scale_estimate_markdown",
    ]
    return {name: str(root / f"{name}.json") if not name.endswith("markdown") else str(root / f"{name}.md") for name in names}


def test_safe_pipeline_stops_before_safe_stages_when_auth_blocked():
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        auth_client=FakeClient(error=challenge_error(), cookie=""),
        paths=temp_paths(root),
    )

    assert summary["gate_status"] == "blocked_openreview_auth"
    assert summary["action"] == "blocked_before_safe_execute"
    assert summary["safe_runner_status_counts"] == {}
    assert summary["scale_estimate_status"] == "blocked_missing_inventory_sample"
    assert Path(summary["paths"]["scale_estimate_out"]).exists()
    assert Path(summary["paths"]["summary_out"]).exists()
    assert Path(summary["paths"]["gate_out"]).exists()


def test_safe_pipeline_dry_runs_safe_stages_and_cost_review_when_ready():
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    manifest = root / "existing_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"request_count": 2, "estimated_batch_cost_usd": 0.1}), encoding="utf-8")

    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        auth_client=FakeClient(cookie="session=abc"),
        paths=temp_paths(root),
        execute_safe=False,
        batch_manifest_patterns=[str(manifest)],
    )

    assert summary["gate_status"] == "ready_for_safe_runner_execute"
    assert summary["action"] == "dry_run_safe_stages"
    assert summary["safe_runner_status_counts"]["dry_run"] >= 1
    assert summary["batch_cost_summary"]["estimated_batch_cost_usd"] == 0.1
    assert summary["scale_estimate_status"] == "ready_for_budget_review"
    assert Path(summary["paths"]["safe_runner_out"]).exists()
    assert Path(summary["paths"]["cost_out"]).exists()


def test_safe_pipeline_can_filter_safe_runner_to_selected_venue():
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    manifest = root / "existing_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"request_count": 2, "estimated_batch_cost_usd": 0.1}), encoding="utf-8")

    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        auth_client=FakeClient(cookie="session=abc"),
        paths=temp_paths(root),
        venues=["ICLR"],
        batch_manifest_patterns=[str(manifest)],
    )
    runner = json.loads(Path(summary["paths"]["safe_runner_out"]).read_text(encoding="utf-8"))
    runner_venues = {step["venue_id"] for step in runner["steps"]}

    assert summary["selected_venues"] == ["ICLR"]
    assert runner_venues == {"ICLR"}


def test_safe_pipeline_can_probe_inventory_when_auth_check_is_blocked():
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    auth_client = FakeClient(error=challenge_error(), cookie="")
    inventory_client = FakeClient(error=challenge_error(), cookie="")

    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        auth_client=auth_client,
        inventory_client=inventory_client,
        paths=temp_paths(root),
        probe_when_auth_blocked=True,
    )

    inventory = json.loads(Path(summary["paths"]["inventory_out"]).read_text(encoding="utf-8"))

    assert summary["gate_status"] == "blocked_openreview_auth"
    assert summary["ran_inventory"] is True
    assert summary["ran_runner_dry_run"] is True
    assert summary["scope_matrix_summary"]["blocked_openreview_auth"] == ["ICLR", "ICML", "NEURIPS", "TMLR"]
    assert inventory["summary"]["needs_openreview_auth"] == ["ICLR", "ICML", "NEURIPS", "TMLR"]
    assert Path(summary["paths"]["inventory_markdown"]).exists()


def test_safe_pipeline_can_install_cookie_file_before_gate_without_leaking_values():
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    source = root / "cookies.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "# Netscape HTTP Cookie File\n"
        ".openreview.net\tTRUE\t/\tTRUE\t1893456000\topenreview_session\tsecret_session\n",
        encoding="utf-8",
    )
    out_cookie = root / "openreview.cookie"
    env_path = root / ".env"

    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        auth_client=FakeClient(error=challenge_error(), cookie=""),
        paths=temp_paths(root),
        cookie_file=str(source),
        out_cookie=out_cookie,
        env_path=env_path,
    )

    assert summary["auth_setup"]["ok"] is True
    assert summary["auth_setup"]["cookie"]["cookie_names"] == ["openreview_session"]
    assert out_cookie.read_text(encoding="utf-8") == "openreview_session=secret_session\n"
    assert env_path.read_text(encoding="utf-8") == f"OPENREVIEW_COOKIE_FILE={out_cookie}\n"
    assert Path(summary["paths"]["auth_setup_out"]).exists()
    assert "secret_session" not in str(summary)


def test_safe_pipeline_constructs_client_after_cookie_install(monkeypatch):
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    source = root / "cookies.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("openreview_session=secret_session\n", encoding="utf-8")
    out_cookie = root / "openreview.cookie"
    env_path = root / ".env"
    seen = {}

    class RecordingClient(FakeClient):
        def __init__(self, *, base_url="https://api2.openreview.net", timeout=60):
            seen["cookie_exists"] = out_cookie.exists()
            seen["cookie_text"] = out_cookie.read_text(encoding="utf-8") if out_cookie.exists() else ""
            seen["env_text"] = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
            super().__init__(cookie="session=abc")

    monkeypatch.setattr(safe_pipeline, "OpenReviewClient", RecordingClient)

    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        cookie_file=str(source),
        out_cookie=out_cookie,
        env_path=env_path,
        paths=temp_paths(root),
    )

    assert seen["cookie_exists"] is True
    assert seen["cookie_text"] == "openreview_session=secret_session\n"
    assert seen["env_text"] == f"OPENREVIEW_COOKIE_FILE={out_cookie}\n"
    assert summary["gate_status"] == "ready_for_safe_runner_execute"
    assert "secret_session" not in str(summary)


def test_safe_pipeline_passes_pull_limit_into_safe_runner_steps():
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    manifest = root / "existing_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"request_count": 2, "estimated_batch_cost_usd": 0.1}), encoding="utf-8")

    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        auth_client=FakeClient(cookie="session=abc"),
        paths=temp_paths(root),
        venues=["ICLR"],
        pull_limit=50,
        batch_manifest_patterns=[str(manifest)],
    )
    runner = json.loads(Path(summary["paths"]["safe_runner_out"]).read_text(encoding="utf-8"))
    pull_step = next(step for step in runner["steps"] if step["name"] == "pull")

    assert summary["pull_limit"] == 50
    assert "--output data/normalized/iclr_2025_sample50.json" in pull_step["command"]
    assert "--limit 50" in pull_step["command"]


def test_safe_pipeline_writes_pilot_readiness_after_selected_venue_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    paths = temp_paths(root)
    normalized = Path("data/normalized/iclr_2025_sample50.json")
    quality = Path("data/validation/iclr_2025_sample50_quality.json")
    manifest = Path("data/batch/iclr_2025_sample50_batch_manifest.json")
    normalized.parent.mkdir(parents=True, exist_ok=True)
    quality.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text(json.dumps({"papers": []}), encoding="utf-8")
    quality.write_text(json.dumps({"paper_count": 50, "review_count": 200, "empty_core_review_rate": 0.0}), encoding="utf-8")
    manifest.write_text(json.dumps({"request_count": 200, "estimated_batch_cost_usd": 0.05}), encoding="utf-8")

    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        auth_client=FakeClient(cookie="session=abc"),
        paths=paths,
        venues=["ICLR"],
        pull_limit=50,
        batch_manifest_patterns=[str(manifest)],
    )
    readiness = json.loads(Path(paths["pilot_readiness_out"]).read_text(encoding="utf-8"))

    assert summary["pilot_readiness_status"] == "ready_for_full_pull"
    assert readiness["dataset_slug"] == "iclr_2025_sample50"
    assert Path(paths["pilot_readiness_markdown"]).exists()


def test_safe_pipeline_stops_locally_when_explicit_cookie_file_is_empty(monkeypatch):
    root = Path("data/test_tmp") / f"safe_pipeline_{uuid.uuid4().hex}"
    source = root / "empty_cookie.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("   ", encoding="utf-8")

    class ShouldNotConstructClient(FakeClient):
        def __init__(self, *args, **kwargs):
            raise AssertionError("OpenReviewClient should not be constructed after failed auth setup")

    monkeypatch.setattr(safe_pipeline, "OpenReviewClient", ShouldNotConstructClient)

    summary = run_openreview_safe_pipeline(
        venue_specs=venue_specs(),
        cookie_file=str(source),
        paths=temp_paths(root),
        venues=["ICLR"],
        pull_limit=50,
    )

    assert summary["action"] == "blocked_auth_setup_failed"
    assert summary["gate_status"] == "not_run"
    assert summary["auth_setup"]["ok"] is False
    assert summary["auth_setup"]["recommendation"] == "provide_cookie_or_cookie_file"
    assert Path(summary["paths"]["summary_out"]).exists()
