from secondopinion.openreview_client import OpenReviewAPIError
from secondopinion.openreview_probe_invitation import run_probe_invitation
from tests.test_openreview_venue_inventory import paper


class FakeClient:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {"notes": []}
        self.error = error

    def get_notes(self, invitation, *, limit=50, details="replies", offset=0):
        if self.error:
            raise self.error
        return self.payload


def test_probe_invitation_reports_public_reviews():
    report = run_probe_invitation(
        invitation="ICLR.cc/2025/Conference/-/Submission",
        venue_id="ICLR",
        client=FakeClient({"notes": [paper()]}),
    )

    assert report["status"] == "success"
    assert report["recommendation"] == "candidate_has_public_reviews"
    assert report["sample_stats"]["review_count"] == 2


def test_probe_invitation_reports_not_found_candidate():
    report = run_probe_invitation(
        invitation="bad/-/Submission",
        client=FakeClient(error=OpenReviewAPIError(404, '{"name":"NotFoundError","message":"not found"}', "url")),
    )

    assert report["status"] == "not_found"
    assert report["recommendation"] == "try_next_candidate"


def test_probe_invitation_reports_challenge_without_leaking_body():
    report = run_probe_invitation(
        invitation="ICLR.cc/2025/Conference/-/Submission",
        client=FakeClient(error=OpenReviewAPIError(403, '{"name":"ChallengeRequiredError","message":"Challenge verification required","challengeUrl":"secret-url"}', "url")),
    )

    assert report["status"] == "challenge_required"
    assert report["recommendation"] == "retry_with_browser_verified_cookie"
    assert report["attempt"]["error"]["challenge_url_present"] is True
