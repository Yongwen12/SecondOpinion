import json
from pathlib import Path

from secondopinion.openreview_readiness_dashboard import (
    build_openreview_readiness_dashboard,
    render_openreview_readiness_dashboard_markdown,
)


def write_json(path: Path | str, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def paths(root: Path):
    return {
        "secret": str(root / "secret.json"),
        "auth_check": str(root / "auth_check.json"),
        "safe_pipeline": str(root / "safe.json"),
        "challenge_resume": str(root / "challenge_resume.json"),
        "cookie_handoff": str(root / "cookie_handoff.json"),
        "cookie_preflight": str(root / "cookie_preflight.json"),
        "scope_audit": str(root / "scope_audit.json"),
        "snapshot_recovery": str(root / "recovery.json"),
        "batch_cost": str(root / "cost.json"),
        "scale_estimate": str(root / "scale.json"),
        "runbook": str(root / "runbook.json"),
        "pilot_readiness_iclr": str(root / "pilot_iclr.json"),
        "pilot_readiness_icml": str(root / "pilot_icml.json"),
        "pilot_readiness_neurips": str(root / "pilot_neurips.json"),
    }


def test_dashboard_blocks_on_missing_openreview_auth(tmp_path):
    p = paths(tmp_path)
    write_json(p["secret"], {"ok": False, "recommendation": "set_openreview_cookie_file_or_token", "cookie": {}})
    write_json(p["safe_pipeline"], {"gate_status": "blocked_openreview_auth", "scope_matrix_summary": {}})
    write_json(p["cookie_handoff"], {"status": "ready_for_cookie_export", "diagnosis_reason": "missing_cookie_or_token", "cookie_warnings": []})
    write_json(p["cookie_preflight"], {"status": "missing_cookie_or_token", "recommendation": "set_openreview_cookie_file_or_token", "blocking_warnings": []})
    write_json(p["scope_audit"], {"status": "passed", "completeness": {"target_count": 8, "excluded_count": 3, "priority1_core_ids": ["ICLR", "ICML", "NEURIPS", "TMLR"], "priority2_probe_ids": ["AISTATS"], "explicitly_excluded_top_journal_ids": ["JAIR", "JMLR", "MLJ"]}})

    report = build_openreview_readiness_dashboard(paths=p)
    markdown = render_openreview_readiness_dashboard_markdown(report)

    assert report["status"] == "blocked_openreview_auth"
    assert "openreview_challenge_resume" in report["next_commands"][0]
    assert "Auth ok: `False`" in markdown
    assert report["cookie_handoff"]["status"] == "ready_for_cookie_export"
    assert "Cookie handoff: `ready_for_cookie_export`" in markdown
    assert "Cookie preflight: `missing_cookie_or_token`" in markdown
    assert "Scope audit: `passed` targets=8 excluded=3" in markdown


def test_dashboard_recommends_pilot_when_inventory_has_ready_venue(tmp_path):
    p = paths(tmp_path)
    write_json(
        p["secret"],
        {
            "ok": True,
            "recommendation": "run_openreview_pipeline_gate",
            "cookie": {"cookie_names": ["openreview_session"], "diagnostics": {"warnings": []}},
        },
    )
    write_json(p["auth_check"], {"ok": True, "status": "ok", "recommendation": "run_inventory"})
    write_json(
        p["safe_pipeline"],
        {
            "gate_status": "ready_for_safe_runner_execute",
            "ran_inventory": True,
            "scope_matrix_summary": {"ready_to_pull": ["ICLR"], "blocked_openreview_auth": []},
        },
    )
    write_json(p["snapshot_recovery"], {"summary": {"recoverable_count": 0}})
    write_json(p["scale_estimate"], {"status": "ready_for_budget_review", "summary": {"estimated_batch_cost_usd": 2.0, "blocked_venues": []}})
    write_json(p["runbook"], {"summary": {"core_priority1": ["ICLR"], "probe_priority2": ["COLM"]}})

    report = build_openreview_readiness_dashboard(paths=p)

    assert report["status"] == "run_priority1_pilot"
    assert "--pull-limit 50" in report["next_commands"][0]
    assert report["pipeline"]["ready_to_pull"] == ["ICLR"]



def test_dashboard_recommends_full_pull_when_pilots_are_ready(tmp_path):
    p = paths(tmp_path)
    write_json(
        p["secret"],
        {
            "ok": True,
            "recommendation": "run_openreview_pipeline_gate",
            "cookie": {"cookie_names": ["openreview.accessToken"], "diagnostics": {"warnings": []}},
        },
    )
    write_json(p["auth_check"], {"ok": True, "status": "ok", "recommendation": "run_inventory"})
    write_json(
        p["safe_pipeline"],
        {
            "gate_status": "ready_for_safe_runner_execute",
            "ran_inventory": True,
            "scope_matrix_summary": {"ready_to_pull": ["ICLR", "ICML", "NEURIPS"], "blocked_openreview_auth": []},
        },
    )
    write_json(p["snapshot_recovery"], {"summary": {"recoverable_count": 0}})
    for key, venue in [
        ("pilot_readiness_iclr", "ICLR"),
        ("pilot_readiness_icml", "ICML"),
        ("pilot_readiness_neurips", "NEURIPS"),
    ]:
        write_json(
            p[key],
            {
                "status": "ready_for_full_pull",
                "venue_id": venue,
                "quality_summary": {"paper_count": 50, "review_count": 200},
                "batch_summary": {"request_count": 200, "estimated_batch_cost_usd": 0.05},
                "errors": [],
                "warnings": [],
            },
        )

    report = build_openreview_readiness_dashboard(paths=p)
    markdown = render_openreview_readiness_dashboard_markdown(report)

    assert report["status"] == "run_full_pull"
    assert "--pull-limit" not in report["next_commands"][0]
    assert "--venue ICLR --venue ICML --venue NEURIPS" in report["next_commands"][0]
    assert report["pilot_readiness"]["ICML"]["status"] == "ready_for_full_pull"
    assert "Pilot readiness: `ICLR=ready_for_full_pull" in markdown



def test_dashboard_blocks_when_local_cookie_exists_but_api_challenge_remains(tmp_path):
    p = paths(tmp_path)
    write_json(
        p["secret"],
        {
            "ok": True,
            "recommendation": "run_openreview_pipeline_gate",
            "cookie": {"cookie_names": ["openreview_session"], "diagnostics": {"warnings": []}},
        },
    )
    write_json(
        p["auth_check"],
        {
            "ok": False,
            "status": "challenge_required",
            "recommendation": "set_openreview_cookie_after_browser_challenge",
        },
    )
    write_json(p["safe_pipeline"], {"gate_status": "blocked_openreview_auth", "scope_matrix_summary": {}})

    report = build_openreview_readiness_dashboard(paths=p)
    markdown = render_openreview_readiness_dashboard_markdown(report)

    assert report["status"] == "blocked_openreview_api_auth"
    assert "openreview_auth_check" in report["next_commands"][1]
    assert "openreview_challenge_resume" in report["next_commands"][0]
    assert report["auth"]["api_status"] == "challenge_required"
    assert "OpenReview API auth status: `challenge_required`" in markdown



def test_dashboard_marks_reports_stale_against_auth_check(tmp_path):
    p = paths(tmp_path)
    write_json(
        p["secret"],
        {"created_at": "2026-07-06T10:00:00+00:00", "ok": False, "recommendation": "set_openreview_cookie_file_or_token", "cookie": {}},
    )
    write_json(
        p["auth_check"],
        {"checked_at": "2026-07-06T11:00:00+00:00", "ok": False, "status": "challenge_required"},
    )
    write_json(
        p["safe_pipeline"],
        {"created_at": "2026-07-06T10:30:00+00:00", "gate_status": "blocked_openreview_auth", "scope_matrix_summary": {}},
    )
    write_json(
        p["scale_estimate"],
        {"created_at": "2026-07-06T10:30:00+00:00", "status": "blocked_missing_inventory_sample", "summary": {}},
    )

    report = build_openreview_readiness_dashboard(paths=p)
    markdown = render_openreview_readiness_dashboard_markdown(report)

    assert "safe_pipeline" in report["freshness"]["stale_reports"]
    assert "scale_estimate" in report["freshness"]["stale_reports"]
    assert "snapshot_recovery" not in report["freshness"]["stale_reports"]
    assert "runbook" not in report["freshness"]["stale_reports"]
    assert report["next_commands"][0].startswith("python -m secondopinion.tools.openreview_local_refresh")
    assert "Stale reports:" in markdown
