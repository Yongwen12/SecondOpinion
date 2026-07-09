import json

from secondopinion.openreview_snapshot_recovery import (
    build_openreview_snapshot_recovery_report,
    render_openreview_snapshot_recovery_markdown,
)


def write_manifest(path, **values):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "raw-snapshot-v0.2",
        "source": "openreview",
        "venue": "ICLR",
        "year": 2025,
        "snapshot_id": path.parent.name,
        "updated_at": "2026-07-06T00:00:00+00:00",
        "query": {
            "invitation": "ICLR.cc/2025/Conference/-/Submission",
            "details": "replies",
            "limit": 50,
            "page_size": 25,
            "polite_delay": 0.2,
        },
        "paper_count": 25,
        "reply_count": 75,
        "raw_files": ["notes_page_0000.json"],
        "complete": False,
        "failed": False,
        "error": {},
        "next_offset": 25,
    }
    payload.update(values)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_snapshot_recovery_reports_failed_and_complete_snapshots(tmp_path):
    root = tmp_path / "data" / "raw" / "openreview"
    write_manifest(
        root / "iclr" / "2025" / "failed-snap" / "manifest.json",
        failed=True,
        error={"type": "RuntimeError", "message": "network interrupted", "offset": 25},
    )
    write_manifest(
        root / "iclr" / "2025" / "done-snap" / "manifest.json",
        complete=True,
        failed=False,
        paper_count=50,
        next_offset=50,
    )

    report = build_openreview_snapshot_recovery_report(root=root, raw_root="data/raw")
    markdown = render_openreview_snapshot_recovery_markdown(report)

    assert report["summary"]["snapshot_count"] == 2
    assert report["summary"]["recoverable_count"] == 1
    assert report["summary"]["status_counts"] == {"complete": 1, "failed_recoverable": 1}
    failed = next(record for record in report["snapshots"] if record["failed"])
    assert failed["next_offset"] == 25
    assert failed["error"]["type"] == "RuntimeError"
    assert "--resume" in failed["resume_command"]
    assert "--snapshot failed-snap" in failed["resume_command"]
    assert "--limit 50" in failed["resume_command"]
    assert "openreview_pull" in markdown



def test_snapshot_recovery_infers_legacy_limited_snapshot_complete(tmp_path):
    root = tmp_path / "data" / "raw" / "openreview"
    manifest = root / "iclr" / "2025" / "legacy-snap" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "raw-snapshot-v0.1",
                "source": "openreview",
                "venue": "ICLR",
                "year": 2025,
                "snapshot_id": "legacy-snap",
                "query": {
                    "invitation": "ICLR.cc/2025/Conference/-/Submission",
                    "details": "replies",
                    "limit": 5,
                    "page_size": 5,
                },
                "paper_count": 5,
                "reply_count": 10,
                "raw_files": ["notes_page_0000.json"],
            }
        ),
        encoding="utf-8",
    )

    report = build_openreview_snapshot_recovery_report(root=root)
    record = report["snapshots"][0]

    assert report["summary"]["recoverable_count"] == 0
    assert report["summary"]["status_counts"] == {"complete": 1}
    assert record["complete"] is True
    assert record["complete_source"] == "inferred_limit_reached"
    assert record["resume_command"] == ""
