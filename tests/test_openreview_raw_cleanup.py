from pathlib import Path

from secondopinion.openreview_raw_cleanup import CONFIRM_TOKEN, cleanup_raw_openreview


def make_raw_snapshot(root: Path) -> Path:
    raw_root = root / "data" / "raw" / "openreview"
    snap = raw_root / "iclr" / "2025" / "snap"
    snap.mkdir(parents=True)
    (snap / "notes_page_0000.json").write_text('{"notes": []}\n', encoding="utf-8")
    return raw_root


def test_raw_cleanup_dry_run_reports_without_deleting(tmp_path):
    raw_root = make_raw_snapshot(tmp_path)

    report = cleanup_raw_openreview(raw_root=raw_root, workspace_root=tmp_path)

    assert report["status"] == "dry_run"
    assert report["deleted"] is False
    assert report["before"]["raw_note_page_count"] == 1
    assert (raw_root / "iclr" / "2025" / "snap" / "notes_page_0000.json").exists()


def test_raw_cleanup_execute_requires_confirm_token(tmp_path):
    raw_root = make_raw_snapshot(tmp_path)

    report = cleanup_raw_openreview(raw_root=raw_root, workspace_root=tmp_path, execute=True)

    assert report["status"] == "failed"
    assert report["deleted"] is False
    assert report["errors"]
    assert (raw_root / "iclr" / "2025" / "snap" / "notes_page_0000.json").exists()


def test_raw_cleanup_execute_deletes_only_expected_openreview_root(tmp_path):
    raw_root = make_raw_snapshot(tmp_path)

    report = cleanup_raw_openreview(raw_root=raw_root, workspace_root=tmp_path, execute=True, confirm=CONFIRM_TOKEN)

    assert report["status"] == "deleted"
    assert report["deleted"] is True
    assert report["after"]["raw_note_page_count"] == 0
    assert (raw_root / "README.md").exists()
    assert not (raw_root / "iclr").exists()


def test_raw_cleanup_refuses_unexpected_path(tmp_path):
    outside = tmp_path / "data" / "raw" / "other"
    outside.mkdir(parents=True)

    report = cleanup_raw_openreview(raw_root=outside, workspace_root=tmp_path, execute=True, confirm=CONFIRM_TOKEN)

    assert report["status"] == "failed"
    assert report["errors"]
    assert outside.exists()
