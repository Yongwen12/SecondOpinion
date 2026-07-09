import json
from pathlib import Path

from secondopinion.openreview_report_consistency import check_openreview_report_consistency


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_report_consistency_passes_for_matching_reports(tmp_path):
    dashboard = tmp_path / "dashboard.json"
    batch = tmp_path / "batch.json"
    scale = tmp_path / "scale.json"
    batch_root = tmp_path / "batch_root"
    write_json(
        dashboard,
        {
            "freshness": {"stale_reports": [], "missing_reports": []},
            "batch_cost": {"estimated_batch_cost_usd": 2.0},
            "scale_estimate": {"status": "blocked_missing_inventory_sample"},
        },
    )
    write_json(batch, {"summary": {"estimated_batch_cost_usd": 2.0}})
    write_json(scale, {"status": "blocked_missing_inventory_sample"})

    report = check_openreview_report_consistency(
        dashboard_path=str(dashboard),
        batch_cost_path=str(batch),
        scale_estimate_path=str(scale),
        batch_root=str(batch_root),
    )

    assert report["status"] == "ok"
    assert report["summary"]["error_count"] == 0


def test_report_consistency_fails_for_stale_and_cost_mismatch(tmp_path):
    dashboard = tmp_path / "dashboard.json"
    batch = tmp_path / "batch.json"
    scale = tmp_path / "scale.json"
    write_json(
        dashboard,
        {
            "freshness": {"stale_reports": ["scale_estimate"], "missing_reports": []},
            "batch_cost": {"estimated_batch_cost_usd": 2.5},
            "scale_estimate": {"status": "ready_for_budget_review"},
        },
    )
    write_json(batch, {"summary": {"estimated_batch_cost_usd": 2.0}})
    write_json(scale, {"status": "blocked_missing_inventory_sample"})

    report = check_openreview_report_consistency(
        dashboard_path=str(dashboard),
        batch_cost_path=str(batch),
        scale_estimate_path=str(scale),
        batch_root=str(tmp_path / "batch_root"),
    )

    assert report["status"] == "failed"
    codes = {issue["code"] for issue in report["issues"]}
    assert {"stale_reports", "batch_cost_mismatch", "scale_status_mismatch"} <= codes
