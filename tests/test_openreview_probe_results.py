import json
from pathlib import Path

from secondopinion.openreview_probe_results import resolve_probe_results


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def probe(path: Path, *, venue="AISTATS", invitation="x/-/Submission", status="success", reviews=0, coverage=0.0):
    write_json(
        path,
        {
            "venue_id": venue,
            "invitation": invitation,
            "status": status,
            "recommendation": "candidate_has_public_reviews" if reviews else "candidate_has_no_public_reviews_in_sample",
            "sample_stats": {
                "paper_count": 10,
                "review_count": reviews,
                "review_coverage_rate": coverage,
                "mean_reviews_per_paper": reviews / 10,
            },
        },
    )


def test_probe_results_selects_public_review_candidate(tmp_path):
    probe(tmp_path / "a_c1.json", venue="AISTATS", invitation="first/-/Submission", reviews=2, coverage=0.2)
    probe(tmp_path / "a_c2.json", venue="AISTATS", invitation="second/-/Submission", reviews=12, coverage=0.8)
    queue = {"items": [{"venue_id": "AISTATS"}, {"venue_id": "AISTATS"}]}

    report = resolve_probe_results(patterns=[str(tmp_path / "*.json")], queue=queue)
    row = report["venues"][0]

    assert row["status"] == "selected_public_reviews"
    assert row["selected_invitation"] == "second/-/Submission"
    assert report["summary"]["selected_for_scoring"] == ["AISTATS"]


def test_probe_results_marks_auth_blocked_when_all_results_auth(tmp_path):
    probe(tmp_path / "iclr.json", venue="ICLR", invitation="ICLR.cc/2025/Conference/-/Submission", status="challenge_required")

    report = resolve_probe_results(patterns=[str(tmp_path / "*.json")], queue={})

    assert report["venues"][0]["status"] == "blocked_auth"
    assert report["summary"]["blocked_auth"] == ["ICLR"]


def test_probe_results_marks_missing_queued_results(tmp_path):
    queue = {"items": [{"venue_id": "ICLR", "invitation": "ICLR.cc/2025/Conference/-/Submission"}]}

    report = resolve_probe_results(patterns=[str(tmp_path / "*.json")], queue=queue)

    assert report["venues"][0]["status"] == "missing_probe_results"
    assert report["summary"]["missing_results"] == ["ICLR"]


def test_probe_results_requires_coverage_before_selecting_for_scoring(tmp_path):
    probe(tmp_path / "a_c1.json", venue="AISTATS", invitation="first/-/Submission", reviews=2, coverage=0.2)
    queue = {"items": [{"venue_id": "AISTATS"}]}

    report = resolve_probe_results(patterns=[str(tmp_path / "*.json")], queue=queue, min_review_coverage=0.5)
    row = report["venues"][0]

    assert row["status"] == "needs_larger_probe"
    assert row["selected_invitation"] == "first/-/Submission"
    assert report["summary"]["selected_for_scoring"] == []
    assert report["summary"]["needs_larger_probe"] == ["AISTATS"]
