import tempfile

from secondopinion.snapshot import save_openreview_snapshot


def note(note_id):
    return {"id": note_id, "forum": note_id, "content": {"title": {"value": note_id}}, "details": {"replies": []}}


class PagingClient:
    base_url = "https://api2.openreview.net"

    def __init__(self):
        self.calls = []
        self.sleeps = []
        self.sleep_func = self.sleeps.append

    def get_notes(self, invitation, *, limit, offset, details):
        self.calls.append({"offset": offset, "limit": limit})
        if offset == 0:
            return {"notes": [note("paper1"), note("paper2")]}
        if offset == 2:
            return {"notes": [note("paper3")]}
        raise AssertionError(f"unexpected offset {offset}")


def test_save_openreview_snapshot_sleeps_between_pages_only():
    with tempfile.TemporaryDirectory() as tmp:
        client = PagingClient()
        result = save_openreview_snapshot(
            client,
            venue="ICLR",
            year=2025,
            invitation="ICLR.cc/2025/Conference/-/Submission",
            root=tmp,
            page_size=2,
            polite_delay=0.25,
        )

    assert [call["offset"] for call in client.calls] == [0, 2]
    assert client.sleeps == [0.25]
    assert result["manifest"]["query"]["polite_delay"] == 0.25
