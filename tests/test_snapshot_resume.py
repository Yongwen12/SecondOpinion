import json
import tempfile
from pathlib import Path

import pytest

from secondopinion.snapshot import load_snapshot_notes, save_openreview_snapshot


def note(note_id):
    return {"id": note_id, "forum": note_id, "content": {"title": {"value": note_id}}, "details": {"replies": []}}


class InterruptingClient:
    base_url = "https://api2.openreview.net"

    def __init__(self):
        self.calls = []

    def get_notes(self, invitation, *, limit, offset, details):
        self.calls.append({"offset": offset, "limit": limit})
        if offset == 0:
            return {"notes": [note("paper1"), note("paper2")]}
        raise RuntimeError("network interrupted")


class ResumingClient:
    base_url = "https://api2.openreview.net"

    def __init__(self):
        self.calls = []

    def get_notes(self, invitation, *, limit, offset, details):
        self.calls.append({"offset": offset, "limit": limit})
        if offset == 2:
            return {"notes": [note("paper3")]}
        if offset == 3:
            return {"notes": []}
        raise AssertionError(f"unexpected offset {offset}")


def test_save_openreview_snapshot_can_resume_existing_pages():
    with tempfile.TemporaryDirectory() as tmp:
        first = InterruptingClient()
        with pytest.raises(RuntimeError):
            save_openreview_snapshot(
                first,
                venue="ICLR",
                year=2025,
                invitation="ICLR.cc/2025/Conference/-/Submission",
                root=tmp,
                snapshot="resume-test",
                page_size=2,
            )
        snapshot_dir = Path(tmp) / "openreview" / "iclr" / "2025" / "resume-test"
        assert (snapshot_dir / "manifest.json").exists()
        assert (snapshot_dir / "notes_page_0000.json").exists()
        failed_manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
        assert failed_manifest["complete"] is False
        assert failed_manifest["failed"] is True
        assert failed_manifest["next_offset"] == 2
        assert failed_manifest["error"]["type"] == "RuntimeError"
        assert failed_manifest["error"]["offset"] == 2

        second = ResumingClient()
        result = save_openreview_snapshot(
            second,
            venue="ICLR",
            year=2025,
            invitation="ICLR.cc/2025/Conference/-/Submission",
            root=tmp,
            snapshot="resume-test",
            page_size=2,
            resume=True,
        )

        assert second.calls[0]["offset"] == 2
        assert result["manifest"]["paper_count"] == 3
        assert result["manifest"]["complete"] is True
        assert result["manifest"]["failed"] is False
        assert result["manifest"]["error"] == {}
        assert result["manifest"]["resumed"] is True
        assert [item["id"] for item in load_snapshot_notes(snapshot_dir)] == ["paper1", "paper2", "paper3"]
