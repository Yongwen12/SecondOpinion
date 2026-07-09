import json

from secondopinion.openreview_auth_check import run_openreview_auth_check
from secondopinion.openreview_client import OpenReviewAPIError


class FakeClient:
    def __init__(self, *, payload=None, error=None, cookie="", token="", user_agent="agent", base_url="api"):
        self.payload = payload if payload is not None else {"notes": [{"id": "paper1"}]}
        self.error = error
        self.cookie = cookie
        self.token = token
        self.user_agent = user_agent
        self.base_url = base_url

    def get_notes(self, invitation, *, limit=50, details="replies", offset=0):
        if self.error:
            raise self.error
        return self.payload


def test_auth_check_reports_ok_without_leaking_credentials():
    result = run_openreview_auth_check(
        client=FakeClient(cookie="secret-cookie", token="secret-token"),
        invitation="ICLR.cc/2025/Conference/-/Submission",
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["api_note_count"] == 1
    assert result["environment"]["cookie_set"] is True
    assert result["environment"]["token_set"] is True
    assert "secret" not in json.dumps(result)


def test_auth_check_classifies_challenge_required():
    body = json.dumps(
        {
            "name": "ChallengeRequiredError",
            "message": "Challenge verification required",
            "challengeUrl": "https://openreview.net/challenge",
        }
    )
    result = run_openreview_auth_check(client=FakeClient(error=OpenReviewAPIError(403, body, "url")))

    assert result["ok"] is False
    assert result["status"] == "challenge_required"
    assert result["recommendation"] == "set_openreview_cookie_after_browser_challenge"
    assert result["error"]["challenge_url_present"] is True


def test_auth_check_classifies_auth_required_with_existing_cookie():
    body = json.dumps({"name": "ForbiddenError", "message": "Forbidden"})
    result = run_openreview_auth_check(client=FakeClient(error=OpenReviewAPIError(403, body, "url"), cookie="stale"))

    assert result["status"] == "auth_required"
    assert result["recommendation"] == "refresh_openreview_cookie_or_token"
