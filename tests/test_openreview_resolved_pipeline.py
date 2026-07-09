from pathlib import Path

from secondopinion.openreview_resolved_pipeline import run_openreview_resolved_pipeline


def test_resolved_pipeline_blocks_when_no_ready_venues(tmp_path):
    report = run_openreview_resolved_pipeline(
        resolved_inventory={
            "venues": [
                {
                    "venue_id": "ICLR",
                    "year": 2025,
                    "status": "missing_probe_results",
                    "recommendation": "run_probe_queue_commands",
                    "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
                }
            ]
        },
        paths={
            "plan_out": str(tmp_path / "plan.json"),
            "plan_markdown": str(tmp_path / "plan.md"),
            "runner_out": str(tmp_path / "runner.json"),
            "runner_markdown": str(tmp_path / "runner.md"),
            "summary_out": str(tmp_path / "summary.json"),
            "summary_markdown": str(tmp_path / "summary.md"),
        },
    )

    assert report["action"] == "blocked_no_resolved_ready_venues"
    assert report["plan_summary"]["needs_manual_inspection"] == ["ICLR"]
    assert report["openai_submit_used"] is False
    assert Path(report["paths"]["summary_out"]).exists()


def test_resolved_pipeline_dry_runs_ready_safe_stages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = run_openreview_resolved_pipeline(
        resolved_inventory={
            "venues": [
                {
                    "venue_id": "ICLR",
                    "year": 2025,
                    "status": "open_reviews_available",
                    "recommendation": "pull_and_score",
                    "selected_invitation": "ICLR.cc/2025/Conference/-/Submission",
                    "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
                    "sample_stats": {"paper_count": 50, "review_count": 150},
                }
            ]
        },
        pull_limit=50,
        paths={
            "plan_out": str(tmp_path / "plan.json"),
            "plan_markdown": str(tmp_path / "plan.md"),
            "runner_out": str(tmp_path / "runner.json"),
            "runner_markdown": str(tmp_path / "runner.md"),
            "summary_out": str(tmp_path / "summary.json"),
            "summary_markdown": str(tmp_path / "summary.md"),
        },
    )

    assert report["action"] == "dry_run_safe_stages"
    assert report["plan_summary"]["ready"] == ["ICLR"]
    assert report["runner_status_counts"].get("dry_run") == 1
    assert report["runner_status_counts"].get("blocked_missing_input") == 4
    assert report["openai_submit_used"] is False
