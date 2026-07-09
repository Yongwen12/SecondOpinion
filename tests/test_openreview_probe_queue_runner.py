from pathlib import Path

from secondopinion.openreview_probe_queue_runner import run_probe_queue
from tests.test_openreview_probe_invitation import FakeClient
from tests.test_openreview_venue_inventory import paper


def queue(tmp_path: Path):
    return {
        "items": [
            {
                "venue_id": "ICLR",
                "candidate_index": 0,
                "invitation": "ICLR.cc/2025/Conference/-/Submission",
                "result_json": str(tmp_path / "iclr.json"),
                "result_markdown": str(tmp_path / "iclr.md"),
                "command": "probe iclr",
            },
            {
                "venue_id": "UAI",
                "candidate_index": 0,
                "invitation": "UAI.cc/2025/Conference/-/Submission",
                "result_json": str(tmp_path / "uai.json"),
                "result_markdown": str(tmp_path / "uai.md"),
                "command": "probe uai",
            },
        ]
    }


def test_probe_queue_runner_dry_run_does_not_write_outputs(tmp_path):
    report = run_probe_queue(queue=queue(tmp_path), execute=False)

    assert report["execute"] is False
    assert report["status_counts"] == {"dry_run": 2}
    assert report["openai_submit_used"] is False
    assert not (tmp_path / "iclr.json").exists()


def test_probe_queue_runner_executes_and_writes_outputs(tmp_path):
    report = run_probe_queue(queue=queue(tmp_path), execute=True, venue_filter=["ICLR"], client=FakeClient({"notes": [paper()]}))

    assert report["execute"] is True
    assert report["probe_count"] == 1
    assert report["status_counts"] == {"success": 1}
    assert (tmp_path / "iclr.json").exists()
    assert (tmp_path / "iclr.md").exists()
    assert not (tmp_path / "uai.json").exists()


def test_probe_queue_runner_limits_items(tmp_path):
    report = run_probe_queue(queue=queue(tmp_path), execute=False, max_items=1)

    assert report["probe_count"] == 1
    assert report["status_counts"] == {"dry_run": 1}
    assert report["max_items"] == 1


def test_probe_queue_runner_skips_existing_probe_result(tmp_path):
    existing = tmp_path / "iclr.json"
    existing.write_text(
        '{"schema_version":"openreview-probe-invitation-v0.1","status":"success","recommendation":"candidate_has_public_reviews"}',
        encoding="utf-8",
    )

    report = run_probe_queue(
        queue=queue(tmp_path),
        execute=True,
        venue_filter=["ICLR"],
        client=FakeClient({"notes": []}),
        skip_existing=True,
    )

    assert report["skip_existing"] is True
    assert report["status_counts"] == {"success": 1}
    assert report["results"][0]["skipped_existing"] is True
    assert report["results"][0]["recommendation"] == "candidate_has_public_reviews"
