import json
import uuid
from pathlib import Path

from secondopinion.openreview_pilot_readiness import build_openreview_pilot_readiness, render_pilot_readiness_markdown


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def sample_plan(root):
    return {
        "venues": [
            {
                "venue_id": "ICLR",
                "dataset_slug": "iclr_2025_sample50",
                "pull_limit": 50,
                "paths": {
                    "normalized": str(root / "iclr_2025_sample50.json"),
                    "quality_json": str(root / "iclr_2025_sample50_quality.json"),
                    "batch_manifest": str(root / "iclr_2025_sample50_batch_manifest.json"),
                },
            }
        ]
    }


def test_pilot_readiness_passes_when_sample_outputs_are_present():
    root = Path("data/test_tmp") / f"pilot_readiness_{uuid.uuid4().hex}"
    plan = sample_plan(root)
    write_json(root / "iclr_2025_sample50.json", {"papers": []})
    write_json(
        root / "iclr_2025_sample50_quality.json",
        {
            "paper_count": 50,
            "review_count": 190,
            "empty_core_review_rate": 0.0,
            "rating_coverage_rate": 1.0,
            "confidence_coverage_rate": 1.0,
        },
    )
    write_json(
        root / "iclr_2025_sample50_batch_manifest.json",
        {"request_count": 190, "estimated_batch_cost_usd": 0.05, "model": "gpt-5.4-nano"},
    )

    report = build_openreview_pilot_readiness(plan=plan, venue_id="ICLR", min_papers=50, min_reviews=100)
    markdown = render_pilot_readiness_markdown(report)

    assert report["status"] == "ready_for_full_pull"
    assert report["recommendation"] == "run_full_pull"
    assert report["next_commands"] == [
        "python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue ICLR --execute-safe"
    ]
    assert report["remediation_commands"] == []
    assert report["dataset_slug"] == "iclr_2025_sample50"
    assert report["quality_summary"]["paper_count"] == 50
    assert report["batch_summary"]["request_count"] == 190
    assert "OpenReview Pilot Readiness" in markdown
    assert "openreview_safe_pipeline" in markdown


def test_pilot_readiness_blocks_when_outputs_are_missing_or_low_quality():
    root = Path("data/test_tmp") / f"pilot_readiness_{uuid.uuid4().hex}"
    plan = sample_plan(root)
    write_json(root / "iclr_2025_sample50.json", {"papers": []})
    write_json(
        root / "iclr_2025_sample50_quality.json",
        {"paper_count": 10, "review_count": 0, "empty_core_review_rate": 0.2},
    )

    report = build_openreview_pilot_readiness(plan=plan, venue_id="ICLR", min_papers=50, min_reviews=1)

    assert report["status"] == "not_ready"
    assert report["recommendation"] == "fix_pilot_outputs"
    assert report["next_commands"] == []
    assert any("--pull-limit 50" in command for command in report["remediation_commands"])
    assert "missing_batch_manifest" in report["errors"]
    assert "paper_count_below_minimum" in report["errors"]
    assert "review_count_below_minimum" in report["errors"]
    assert "empty_core_review_rate_too_high" in report["errors"]
