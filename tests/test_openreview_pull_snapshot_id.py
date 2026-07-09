import json
from pathlib import Path

import secondopinion.batch_review_scoring as scoring


class FakeClient:
    base_url = "https://api2.openreview.net"


def test_pull_openreview_normalized_passes_snapshot_id(monkeypatch, tmp_path):
    seen = {}

    def fake_save_snapshot(client, **kwargs):
        seen.update(kwargs)
        snapshot_dir = tmp_path / "raw" / "openreview" / "iclr" / "2025" / kwargs["snapshot"]
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "snapshot_id": kwargs["snapshot"],
                    "source": "openreview",
                    "venue": "ICLR",
                    "year": 2025,
                    "raw_files": [],
                }
            ),
            encoding="utf-8",
        )
        return {"snapshot_dir": str(snapshot_dir), "manifest": {"snapshot_id": kwargs["snapshot"]}}

    def fake_normalize_snapshot(snapshot_dir, *, venue=None, year=None):
        return {"paper_count": 0, "review_count": 0, "source_snapshot": {"snapshot_dir": str(snapshot_dir)}}

    monkeypatch.setattr(scoring, "OpenReviewClient", FakeClient)
    monkeypatch.setattr(scoring, "save_openreview_snapshot", fake_save_snapshot)
    monkeypatch.setattr(scoring, "normalize_snapshot", fake_normalize_snapshot)

    summary = scoring.pull_openreview_normalized(
        venue="ICLR",
        year=2025,
        limit=50,
        output=tmp_path / "normalized.json",
        snapshot_id="resume-test",
        resume=True,
    )

    assert seen["snapshot"] == "resume-test"
    assert seen["resume"] is True
    assert summary["snapshot_id"] == "resume-test"
    assert Path(summary["normalized_path"]).exists()

class FakePagedClient:
    base_url = "https://api2.openreview.net"

    def __init__(self):
        self.calls = []
        self.sleep_func = lambda _seconds: None

    def get_notes(self, invitation, *, limit=50, offset=0, details="replies"):
        self.calls.append({"invitation": invitation, "limit": limit, "offset": offset, "details": details})
        if offset:
            return {"notes": []}
        return {
            "notes": [
                {
                    "id": "paper1",
                    "forum": "paper1",
                    "content": {
                        "title": {"value": "Paper"},
                        "abstract": {"value": "Abstract"},
                    },
                    "details": {
                        "replies": [
                            {
                                "id": "review1",
                                "invitations": ["ICLR.cc/2025/Conference/Submission1/-/Official_Review"],
                                "content": {"review": {"value": "Useful review text."}},
                            }
                        ]
                    },
                }
            ]
        }


def test_pull_openreview_normalized_default_does_not_write_raw_snapshot(monkeypatch, tmp_path):
    client = FakePagedClient()

    def fail_save_snapshot(*_args, **_kwargs):
        raise AssertionError("raw snapshot should be opt-in")

    monkeypatch.setattr(scoring, "OpenReviewClient", lambda: client)
    monkeypatch.setattr(scoring, "save_openreview_snapshot", fail_save_snapshot)

    summary = scoring.pull_openreview_normalized(
        venue="ICLR",
        year=2025,
        limit=1,
        output=tmp_path / "normalized.json",
        snapshot_id="no-raw-test",
    )

    payload = json.loads(Path(summary["normalized_path"]).read_text(encoding="utf-8"))
    assert summary["raw_snapshot_retained"] is False
    assert summary["snapshot_dir"] == ""
    assert payload["source_snapshot"]["raw_snapshot_retained"] is False
    assert payload["source_snapshot"]["snapshot_id"] == "no-raw-test"
    assert payload["paper_count"] == 1
    assert payload["review_count"] == 1
