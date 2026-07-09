import io
import urllib.error
from email.message import Message

import pytest

from secondopinion.openreview_client import OpenReviewAPIError, OpenReviewClient


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


def http_error(status: int, body: bytes = b"{}", *, retry_after: str | None = None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("https://api2.openreview.net/notes", status, "error", headers, io.BytesIO(body))


def test_openreview_client_retries_retryable_http_errors():
    calls = []
    sleeps = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise http_error(500, b'{"message":"temporary"}')
        return FakeResponse(b'{"notes":[{"id":"paper1"}]}')

    client = OpenReviewClient(urlopen_func=fake_urlopen, sleep_func=sleeps.append, retry_backoff=0.25, max_retries=2)
    payload = client.get_notes("ICLR.cc/2025/Conference/-/Submission", limit=1)

    assert payload["notes"][0]["id"] == "paper1"
    assert len(calls) == 2
    assert sleeps == [0.25]


def test_openreview_client_uses_retry_after_header():
    calls = []
    sleeps = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise http_error(429, b'{"message":"rate limit"}', retry_after="3")
        return FakeResponse(b'{"notes":[]}')

    client = OpenReviewClient(urlopen_func=fake_urlopen, sleep_func=sleeps.append, retry_backoff=0.25, max_retries=1)

    assert client.get_notes("ICLR.cc/2025/Conference/-/Submission") == {"notes": []}
    assert sleeps == [3.0]


def test_openreview_client_does_not_retry_challenge_errors():
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise http_error(403, b'{"name":"ChallengeRequiredError","message":"Challenge verification required"}')

    client = OpenReviewClient(urlopen_func=fake_urlopen, sleep_func=lambda _: None, max_retries=3)

    with pytest.raises(OpenReviewAPIError) as excinfo:
        client.get_notes("ICLR.cc/2025/Conference/-/Submission")

    assert excinfo.value.status_code == 403
    assert len(calls) == 1


def test_openreview_client_retries_url_errors():
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise urllib.error.URLError("temporary dns failure")
        return FakeResponse(b'{"notes":[]}')

    client = OpenReviewClient(urlopen_func=fake_urlopen, sleep_func=lambda _: None, max_retries=1)

    assert client.get_notes("ICLR.cc/2025/Conference/-/Submission") == {"notes": []}
    assert len(calls) == 2


def test_openreview_client_reads_cookie_and_token_files(tmp_path):
    cookie_file = tmp_path / "openreview.cookie"
    token_file = tmp_path / "openreview.token"
    cookie_file.write_text("sesh=abc\n", encoding="utf-8")
    token_file.write_text("tok123\n", encoding="utf-8")
    headers = {}

    def fake_urlopen(request, timeout):
        headers.update(dict(request.header_items()))
        return FakeResponse(b'{"notes":[]}')

    client = OpenReviewClient(
        cookie_file=cookie_file,
        token_file=token_file,
        urlopen_func=fake_urlopen,
        sleep_func=lambda _: None,
    )

    assert client.get_notes("ICLR.cc/2025/Conference/-/Submission") == {"notes": []}
    assert headers["Cookie"] == "sesh=abc"
    assert headers["Authorization"] == "Bearer tok123"


def test_openreview_client_explicit_cookie_overrides_cookie_file(tmp_path):
    cookie_file = tmp_path / "openreview.cookie"
    cookie_file.write_text("sesh=file", encoding="utf-8")
    headers = {}

    def fake_urlopen(request, timeout):
        headers.update(dict(request.header_items()))
        return FakeResponse(b'{"notes":[]}')

    client = OpenReviewClient(cookie="sesh=explicit", cookie_file=cookie_file, urlopen_func=fake_urlopen)

    assert client.get_notes("ICLR.cc/2025/Conference/-/Submission") == {"notes": []}
    assert headers["Cookie"] == "sesh=explicit"


def test_openreview_client_converts_netscape_cookie_jar(tmp_path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".openreview.net\tTRUE\t/\tTRUE\t1893456000\topenreview_session\tabc\n"
        "api2.openreview.net\tFALSE\t/\tTRUE\t1893456000\tcf_clearance\tclear\n"
        ".example.com\tTRUE\t/\tTRUE\t1893456000\tignored\tx\n",
        encoding="utf-8",
    )
    headers = {}

    def fake_urlopen(request, timeout):
        headers.update(dict(request.header_items()))
        return FakeResponse(b'{"notes":[]}')

    client = OpenReviewClient(cookie_file=cookie_file, urlopen_func=fake_urlopen)

    assert client.get_notes("ICLR.cc/2025/Conference/-/Submission") == {"notes": []}
    assert headers["Cookie"] == "openreview_session=abc; cf_clearance=clear"


def test_openreview_client_keeps_raw_cookie_file_text(tmp_path):
    cookie_file = tmp_path / "cookie-header.txt"
    cookie_file.write_text("openreview_session=abc; cf_clearance=clear\n", encoding="utf-8")
    headers = {}

    def fake_urlopen(request, timeout):
        headers.update(dict(request.header_items()))
        return FakeResponse(b'{"notes":[]}')

    client = OpenReviewClient(cookie_file=cookie_file, urlopen_func=fake_urlopen)

    assert client.get_notes("ICLR.cc/2025/Conference/-/Submission") == {"notes": []}
    assert headers["Cookie"] == "openreview_session=abc; cf_clearance=clear"

def test_openreview_client_loads_dotenv_cookie_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENREVIEW_COOKIE", raising=False)
    monkeypatch.delenv("OPENREVIEW_COOKIE_FILE", raising=False)
    cookie_file = tmp_path / "openreview.cookie"
    cookie_file.write_text("openreview_session=abc\n", encoding="utf-8")
    (tmp_path / ".env").write_text(f"OPENREVIEW_COOKIE_FILE={cookie_file}\n", encoding="utf-8")
    headers = {}

    def fake_urlopen(request, timeout):
        headers.update(dict(request.header_items()))
        return FakeResponse(b'{"notes":[]}')

    client = OpenReviewClient(urlopen_func=fake_urlopen, sleep_func=lambda _: None)

    assert client.get_notes("ICLR.cc/2025/Conference/-/Submission") == {"notes": []}
    assert headers["Cookie"] == "openreview_session=abc"


def test_openreview_get_all_notes_uses_injected_sleep():
    calls = []
    sleeps = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            return FakeResponse(b'{"notes":[{"id":"paper1"}]}')
        return FakeResponse(b'{"notes":[]}')

    client = OpenReviewClient(urlopen_func=fake_urlopen, sleep_func=sleeps.append)

    assert client.get_all_notes("ICLR.cc/2025/Conference/-/Submission", page_size=1, polite_delay=0.2) == [
        {"id": "paper1"}
    ]
    assert sleeps == [0.2]
