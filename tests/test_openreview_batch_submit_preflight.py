import json
from pathlib import Path

from secondopinion.openreview_batch_submit_preflight import build_batch_submit_preflight


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def seed_reports(tmp_path: Path, *, consistency_status="ok", cost=2.0, requests=10, manifests=1):
    consistency = tmp_path / "consistency.json"
    batch = tmp_path / "batch.json"
    write_json(consistency, {"status": consistency_status})
    write_json(
        batch,
        {
            "status": "ready_for_cost_review",
            "summary": {
                "estimated_batch_cost_usd": cost,
                "request_count": requests,
                "included_manifest_count": manifests,
            },
        },
    )
    return consistency, batch


def test_batch_submit_preflight_requires_explicit_approval(tmp_path):
    consistency, batch = seed_reports(tmp_path)

    report = build_batch_submit_preflight(
        consistency_path=consistency,
        batch_cost_path=batch,
        max_total_cost_usd=25.0,
    )

    assert report["status"] == "blocked_explicit_approval_required"
    assert report["openai_submit_used"] is False
    assert {"code": "explicit_approval_required"} in report["issues"]


def test_batch_submit_preflight_blocks_failed_consistency(tmp_path):
    consistency, batch = seed_reports(tmp_path, consistency_status="failed")

    report = build_batch_submit_preflight(
        consistency_path=consistency,
        batch_cost_path=batch,
        max_total_cost_usd=25.0,
        allow_submit=True,
    )

    assert report["status"] == "blocked_consistency_failed"


def test_batch_submit_preflight_blocks_cost_limit(tmp_path):
    consistency, batch = seed_reports(tmp_path, cost=26.0)

    report = build_batch_submit_preflight(
        consistency_path=consistency,
        batch_cost_path=batch,
        max_total_cost_usd=25.0,
        allow_submit=True,
    )

    assert report["status"] == "blocked_cost_limit"


def test_batch_submit_preflight_blocks_empty_manifests(tmp_path):
    consistency, batch = seed_reports(tmp_path, requests=0, manifests=0)

    report = build_batch_submit_preflight(
        consistency_path=consistency,
        batch_cost_path=batch,
        max_total_cost_usd=25.0,
        allow_submit=True,
    )

    assert report["status"] == "blocked_no_batch_manifests"


def test_batch_submit_preflight_ready_when_all_checks_pass(tmp_path):
    consistency, batch = seed_reports(tmp_path)

    report = build_batch_submit_preflight(
        consistency_path=consistency,
        batch_cost_path=batch,
        max_total_cost_usd=25.0,
        allow_submit=True,
    )

    assert report["status"] == "ready_for_submit"
    assert report["issues"] == []
