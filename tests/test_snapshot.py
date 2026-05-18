import tempfile
import unittest
from pathlib import Path

from secondopinion.snapshot import load_snapshot_notes, normalize_snapshot, save_openreview_snapshot


class FakeClient:
    base_url = "https://api2.openreview.net"

    def __init__(self):
        self.calls = []

    def get_notes(self, invitation, *, limit, offset, details):
        self.calls.append({"invitation": invitation, "limit": limit, "offset": offset, "details": details})
        if offset > 0:
            return {"notes": []}
        return {
            "notes": [
                {
                    "id": "paper1",
                    "forum": "paper1",
                    "invitations": ["ICLR.cc/2024/Conference/-/Submission"],
                    "content": {
                        "title": {"value": "Snapshot Paper"},
                        "abstract": {"value": "Abstract."}
                    },
                    "details": {
                        "replies": [
                            {
                                "id": "review1",
                                "invitations": ["ICLR.cc/2024/Conference/Submission1/-/Official_Review"],
                                "content": {
                                    "summary": {"value": "Summary."},
                                    "weaknesses": {"value": "The paper lacks baselines."},
                                    "rating": {"value": "3: reject"}
                                }
                            },
                            {
                                "id": "decision1",
                                "invitations": ["ICLR.cc/2024/Conference/Submission1/-/Decision"],
                                "content": {"decision": {"value": "Reject"}}
                            }
                        ]
                    }
                }
            ]
        }


class SnapshotTests(unittest.TestCase):
    def test_save_and_normalize_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = save_openreview_snapshot(
                FakeClient(),
                venue="ICLR",
                year=2024,
                invitation="ICLR.cc/2024/Conference/-/Submission",
                root=tmp,
                snapshot="20260518T120000Z",
            )
            snapshot_dir = Path(result["snapshot_dir"])
            self.assertTrue((snapshot_dir / "manifest.json").exists())
            self.assertTrue((snapshot_dir / "notes_page_0000.json").exists())
            self.assertEqual(result["manifest"]["paper_count"], 1)
            self.assertEqual(result["manifest"]["reply_count"], 2)

            notes = load_snapshot_notes(snapshot_dir)
            self.assertEqual(len(notes), 1)

            normalized = normalize_snapshot(snapshot_dir)
            self.assertEqual(normalized["paper_count"], 1)
            self.assertEqual(normalized["review_count"], 1)
            self.assertEqual(normalized["source_snapshot"]["snapshot_id"], "20260518T120000Z")


if __name__ == "__main__":
    unittest.main()

