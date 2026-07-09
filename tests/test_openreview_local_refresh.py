import json
from pathlib import Path

from secondopinion.openreview_local_refresh import refresh_openreview_local_reports


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_local_refresh_writes_local_reports_without_network(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENREVIEW_COOKIE", raising=False)
    monkeypatch.delenv("OPENREVIEW_COOKIE_FILE", raising=False)
    monkeypatch.delenv("OPENREVIEW_TOKEN", raising=False)
    monkeypatch.delenv("OPENREVIEW_TOKEN_FILE", raising=False)
    inventory = tmp_path / "inventory.json"
    write_json(
        inventory,
        {
            "venues": [
                {
                    "venue_id": "ICLR",
                    "status": "open_reviews_available",
                    "include_in_inventory": True,
                    "sample_stats": {"paper_count": 10, "review_count": 40, "mean_reviews_per_paper": 4.0},
                }
            ]
        },
    )
    venues = tmp_path / "venues.json"
    write_json(venues, {"venues": [{"venue_id": "ICLR", "priority": 1, "scope_decision": "score_public_reviews", "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"], "evidence_urls": ["https://openreview.net/group?id=ICLR.cc/2025/Conference"]}]})
    manifest = tmp_path / "batch" / "manifest.json"
    write_json(manifest, {"request_count": 40, "estimated_batch_cost_usd": 0.04})
    snapshot_manifest = tmp_path / "raw" / "openreview" / "iclr" / "2025" / "snap" / "manifest.json"
    write_json(
        snapshot_manifest,
        {
            "venue": "ICLR",
            "year": 2025,
            "snapshot_id": "snap",
            "query": {"invitation": "ICLR.cc/2025/Conference/-/Submission", "limit": 10, "page_size": 10},
            "paper_count": 10,
            "reply_count": 40,
            "raw_files": ["notes_page_0000.json"],
        },
    )
    root = tmp_path / "out"
    paths = {
        "invitation_audit_out": str(root / "invitation_audit.json"),
        "invitation_audit_markdown": str(root / "invitation_audit.md"),
        "probe_queue_out": str(root / "probe_queue.json"),
        "probe_queue_markdown": str(root / "probe_queue.md"),
        "probe_queue_runner_out": str(root / "probe_queue_runner.json"),
        "probe_queue_runner_markdown": str(root / "probe_queue_runner.md"),
        "challenge_resume_out": str(root / "challenge_resume.json"),
        "cookie_handoff_out": str(root / "cookie_handoff.json"),
        "cookie_preflight_out": str(root / "cookie_preflight.json"),
        "cookie_preflight_markdown": str(root / "cookie_preflight.md"),
        "cookie_handoff_markdown": str(root / "cookie_handoff.md"),
        "scope_audit_out": str(root / "scope_audit.json"),
        "scope_audit_markdown": str(root / "scope_audit.md"),
        "data_minimization_out": str(root / "data_minimization.json"),
        "data_minimization_markdown": str(root / "data_minimization.md"),
        "probe_results_out": str(root / "probe_results.json"),
        "probe_results_markdown": str(root / "probe_results.md"),
        "resolved_inventory_out": str(root / "resolved_inventory.json"),
        "resolved_inventory_markdown": str(root / "resolved_inventory.md"),
        "resolved_pipeline_out": str(root / "resolved_pipeline.json"),
        "resolved_pipeline_markdown": str(root / "resolved_pipeline.md"),
        "resolved_plan_out": str(root / "resolved_plan.json"),
        "resolved_plan_markdown": str(root / "resolved_plan.md"),
        "resolved_runner_out": str(root / "resolved_runner.json"),
        "resolved_runner_markdown": str(root / "resolved_runner.md"),
        "snapshot_recovery_out": str(root / "recovery.json"),
        "snapshot_recovery_markdown": str(root / "recovery.md"),
        "batch_cost_out": str(root / "cost.json"),
        "batch_cost_markdown": str(root / "cost.md"),
        "scale_estimate_out": str(root / "scale.json"),
        "scale_estimate_markdown": str(root / "scale.md"),
        "dashboard_out": str(root / "dashboard.json"),
        "dashboard_markdown": str(root / "dashboard.md"),
        "consistency_out": str(root / "consistency.json"),
        "consistency_markdown": str(root / "consistency.md"),
        "submit_preflight_out": str(root / "submit_preflight.json"),
        "submit_preflight_markdown": str(root / "submit_preflight.md"),
        "refresh_out": str(root / "refresh.json"),
    }

    write_json(root / "challenge_resume.json", {"created_at": "2026-07-06T00:00:00+00:00", "status": "blocked_auth_check"})

    report = refresh_openreview_local_reports(
        inventory_path=str(inventory),
        venues_path=str(venues),
        snapshot_root=str(tmp_path / "raw" / "openreview"),
        raw_root=str(tmp_path / "raw"),
        batch_manifest_patterns=[str(manifest)],
        probe_result_patterns=[str(tmp_path / "probe-results" / "*.json")],
        data_minimization_normalized_patterns=[str(tmp_path / "normalized" / "*.json")],
        data_minimization_batch_patterns=[str(tmp_path / "batch" / "*.jsonl")],
        paths=paths,
    )

    assert report["network_used"] is False
    assert report["openai_submit_used"] is False
    assert report["summary"]["invitation_audit_needs_attention"] == []
    assert report["summary"]["probe_queue_count"] == 1
    assert report["summary"]["probe_queue_runner_counts"] == {"dry_run": 1}
    assert report["summary"]["challenge_resume_status"] == "blocked_auth_check"
    assert report["summary"]["cookie_handoff_status"] == "ready_for_cookie_export"
    assert report["summary"]["cookie_preflight_status"] == "missing_cookie_or_token"
    assert report["summary"]["scope_audit_status"] == "failed"
    assert report["summary"]["scope_target_count"] == 1
    assert report["summary"]["data_minimization_status"] == "passed"
    assert report["summary"]["probe_results_selected"] == []
    assert report["summary"]["probe_results_missing"] == ["ICLR"]
    assert report["summary"]["resolved_ready_to_pull"] == []
    assert report["summary"]["resolved_needs_probe_results"] == ["ICLR"]
    assert report["summary"]["resolved_pipeline_action"] == "blocked_no_resolved_ready_venues"
    assert report["summary"]["snapshot_recoverable_count"] == 0
    assert report["summary"]["batch_estimated_cost_usd"] == 0.04
    assert report["summary"]["scale_estimate_status"] == "ready_for_budget_review"
    assert report["summary"]["consistency_status"] == "failed"
    for path in paths.values():
        assert Path(path).exists()
