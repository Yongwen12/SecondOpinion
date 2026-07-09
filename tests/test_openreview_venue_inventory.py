import json

from secondopinion.openreview_client import OpenReviewAPIError
from secondopinion.openreview_venue_inventory import (
    load_venue_specs,
    probe_venue,
    render_venue_inventory_markdown,
    run_openreview_venue_inventory,
)


def content(**values):
    return {key: {"value": value} for key, value in values.items()}


def review(note_id):
    return {
        "id": note_id,
        "forum": "paper1",
        "invitations": ["ICLR.cc/2025/Conference/Submission1/-/Official_Review"],
        "signatures": ["ICLR.cc/2025/Conference/Submission1/Reviewer_abc"],
        "content": content(summary="Good paper.", weaknesses="Needs more baselines.", rating="6: marginal accept"),
        "cdate": 1000,
        "tcdate": 1000,
        "mdate": 1000,
        "tmdate": 1000,
    }


def decision(note_id):
    return {
        "id": note_id,
        "forum": "paper1",
        "invitations": ["ICLR.cc/2025/Conference/Submission1/-/Decision"],
        "signatures": ["ICLR.cc/2025/Conference/Program_Chairs"],
        "content": content(decision="Accept"),
        "cdate": 2000,
        "tcdate": 2000,
    }


def paper():
    return {
        "id": "paper1",
        "forum": "paper1",
        "content": content(title="A public review paper"),
        "details": {"replies": [review("review1"), review("review2"), decision("decision1")]},
    }


class FakeClient:
    def __init__(self, payloads=None, errors=None):
        self.payloads = payloads or {}
        self.errors = errors or {}

    def get_notes(self, invitation, *, limit=50, details="replies", offset=0):
        if invitation in self.errors:
            raise self.errors[invitation]
        return self.payloads.get(invitation, {"notes": []})


def test_probe_venue_detects_open_reviews():
    result = probe_venue(
        FakeClient({"ICLR.cc/2025/Conference/-/Submission": {"notes": [paper()]}}),
        {
            "venue_id": "ICLR",
            "year": 2025,
            "category": "top_conference",
            "scope": "all_submissions",
            "review_policy": "fully_open_public_reviews",
            "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
        },
        sample_limit=10,
        details="replies",
        min_review_coverage=0.5,
    )

    assert result["status"] == "open_reviews_available"
    assert result["recommendation"] == "pull_and_score"
    assert result["scope"] == "all_submissions"
    assert result["review_policy"] == "fully_open_public_reviews"
    assert result["public_review_evidence"]["state"] == "api_confirmed_public_reviews"
    assert result["review_invitation_counts"] == {"ICLR.cc/2025/Conference/Submission1/-/Official_Review": 2}
    assert result["sample_stats"]["review_count"] == 2
    assert result["sample_stats"]["decision_coverage_rate"] == 1.0


def test_probe_venue_marks_openreview_challenge():
    body = json.dumps(
        {
            "name": "ChallengeRequiredError",
            "message": "Challenge verification required",
            "challengeUrl": "https://openreview.net/challenge",
        }
    )
    result = probe_venue(
        FakeClient(errors={"ICML.cc/2025/Conference/-/Submission": OpenReviewAPIError(403, body, "url")}),
        {
            "venue_id": "ICML",
            "year": 2025,
            "priority": 1,
            "review_policy": "partially_open_public_reviews",
            "scope_decision": "score_public_reviews",
            "invitation_candidates": ["ICML.cc/2025/Conference/-/Submission"],
        },
        sample_limit=10,
        details="replies",
        min_review_coverage=0.5,
    )

    assert result["status"] == "challenge_required"
    assert result["recommendation"] == "retry_with_openreview_cookie"
    assert result["attempts"][0]["error"]["challenge_url_present"] is True
    assert result["public_review_evidence"]["state"] == "expected_public_reviews_api_verification_required"


def test_run_inventory_renders_markdown_summary():
    report = run_openreview_venue_inventory(
        specs=[
            {
                "venue_id": "ICLR",
                "year": 2025,
                "category": "top_conference",
                "scope": "all_submissions",
                "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
            }
        ],
        client=FakeClient({"ICLR.cc/2025/Conference/-/Submission": {"notes": [paper()]}}),
        sample_limit=10,
    )
    markdown = render_venue_inventory_markdown(report)

    assert report["summary"]["ready_to_pull_and_score"] == ["ICLR"]
    assert "| ICLR | top_conference | all_submissions | open_reviews_available | pull_and_score |" in markdown
    assert "Official_Review" in markdown


def test_load_default_venue_specs_has_core_scope_metadata():
    specs = load_venue_specs()
    by_id = {spec["venue_id"]: spec for spec in specs}

    assert {"ICLR", "ICML", "NEURIPS", "TMLR"}.issubset(by_id)
    assert by_id["TMLR"]["category"] == "top_journal"
    assert by_id["TMLR"]["rolling_venue"] is True
    assert by_id["ICLR"]["scope"] == "all_submissions"

def test_manual_excluded_journal_is_not_probed():
    client = FakeClient(payloads={"SHOULD/NOT/BE/CALLED": {"notes": [paper()]}})
    result = probe_venue(
        client,
        {
            "venue_id": "JMLR",
            "year": 2025,
            "category": "top_journal",
            "include_in_inventory": False,
            "manual_status": "excluded_no_public_reviews",
            "manual_recommendation": "skip_no_public_reviews",
            "source_notes": ["No public OpenReview official-review corpus is expected."],
            "invitation_candidates": ["SHOULD/NOT/BE/CALLED"],
        },
        sample_limit=10,
        details="replies",
        min_review_coverage=0.5,
    )

    assert result["status"] == "excluded_no_public_reviews"
    assert result["recommendation"] == "skip_no_public_reviews"
    assert result["attempts"] == []
    assert result["sample_stats"]["paper_count"] == 0
    assert result["public_review_evidence"]["state"] == "excluded_no_public_openreview_corpus"
    assert "JMLR" in run_openreview_venue_inventory(
        specs=[{"venue_id": "JMLR", "include_in_inventory": False}],
        client=client,
        sample_limit=10,
    )["summary"]["skipped_not_open_review"]
