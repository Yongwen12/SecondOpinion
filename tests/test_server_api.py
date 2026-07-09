import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from secondopinion.server.api import create_app
from secondopinion.server.config import ServerSettings
from secondopinion.server.database import init_db, make_engine, make_session_factory, session_scope
from secondopinion.server.ingest import import_normalized_dataset
from secondopinion.server.models import Paper
from secondopinion.server.repository import create_scoring_job, store_scorecard


def session_factory_for(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'api.db'}")
    init_db(engine)
    return make_session_factory(engine)


def seed(factory, tmp_path):
    normalized = {
        "dataset": "iclr_2025",
        "papers": [
            {
                "paper_id": "paper1",
                "venue": "ICLR",
                "year": 2025,
                "title": "Searchable Paper",
                "abstract": "A paper.",
                "reviews": [{"review_id": "review1", "review_text": "Add a baseline.", "weaknesses": "Missing baseline."}],
            },
            {"paper_id": "paper2", "venue": "ICLR", "year": 2025, "title": "No Scorecard Yet", "reviews": []},
            {
                "paper_id": "paper3",
                "venue": "TMLR",
                "year": 2025,
                "title": "Cross Venue Paper",
                "abstract": "A TMLR paper.",
                "reviews": [{"review_id": "review3", "review_text": "Good cross venue review."}],
            },
        ],
    }
    path = tmp_path / "normalized.json"
    path.write_text(json.dumps(normalized), encoding="utf-8")
    public = {
        "schema_version": "reviewer-public-scorecard-v0.1",
        "paper": {"title": "Searchable Paper", "venue": "ICLR", "year": 2025},
        "summary": {"overall_score": 80, "signal_label": "Solid review", "reviewer_count": 1, "comment_count": 0},
        "reviewers": [
            {
                "reviewer_key": "R1",
                "nickname": "Baseline Hawk",
                "avatar_key": "R1",
                "score": 80,
                "tone": "blue",
                "label": "Solid review",
                "summary": "Useful review.",
                "social": {"up": 1, "down": 0},
                "dimensions": [
                    {"key": "outrage", "score": 80, "quote": "Add a baseline.", "verdict": "Useful but direct"},
                    {"key": "toxicity", "score": 0},
                    {"key": "helpfulness", "score": 75},
                ],
            }
        ],
        "comments": [],
        "topics": [],
        "leaderboards": {"red": ["R1"], "black": ["R1"]},
    }
    with session_scope(factory) as session:
        import_normalized_dataset(session, path)
        paper = session.get(Paper, "paper1")
        store_scorecard(
            session,
            paper=paper,
            public_json=public,
            internal_artifact_path="",
            scorer_version="server-hybrid-scorer-v0.1",
            memory_index_version="external-full-lite-v0.1",
        )


def test_api_search_scorecard_vote_and_job_flow(tmp_path):
    factory = session_factory_for(tmp_path)
    seed(factory, tmp_path)
    settings = ServerSettings(
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        artifact_root=tmp_path / "artifacts",
        scoring_memory_path=tmp_path / "memory.jsonl",
    )
    app = create_app(settings=settings, session_factory=factory)
    client = TestClient(app)

    conferences = client.get("/api/conferences")
    assert conferences.status_code == 200
    assert conferences.json()["items"][0]["conference_id"] == "ICLR"

    search = client.get("/api/conferences/ICLR/papers", params={"query": "Searchable"})
    assert search.status_code == 200
    assert search.json()["items"][0]["paper_id"] == "paper1"

    global_search = client.get("/api/papers", params={"query": "Cross Venue", "year": 2025})
    assert global_search.status_code == 200
    assert global_search.json()["items"][0]["paper_id"] == "paper3"
    assert global_search.json()["items"][0]["venue"] == "TMLR"

    static_home = client.get("/api/home", params={"year": 2025, "limit": 1})
    assert static_home.status_code == 200
    assert static_home.json()["source"] == "static_home_2025"
    assert len(static_home.json()["latest_papers"]) == 1

    custom_home_path = tmp_path / "custom_home.json"
    custom_home_path.write_text(
        json.dumps({
            "latest_papers": [{"paper_id": "custom1"}, {"paper_id": "custom2"}],
            "leaderboards": {"overall": [], "toxic": [], "helpful": [], "red": [], "black": []},
            "stats": {"paper_count": 2, "review_count": 2, "scored_review_count": 2, "audited_count": 2},
            "audited_count": 2,
            "paper_count": 2,
            "review_count": 2,
        }),
        encoding="utf-8",
    )
    custom_settings = ServerSettings(
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        artifact_root=tmp_path / "artifacts",
        scoring_memory_path=tmp_path / "memory.jsonl",
        home_snapshot_path=custom_home_path,
    )
    custom_client = TestClient(create_app(settings=custom_settings, session_factory=factory))
    custom_home = custom_client.get("/api/home", params={"year": 2025, "limit": 1})
    assert custom_home.status_code == 200
    assert custom_home.json()["latest_papers"] == [{"paper_id": "custom1"}]

    home = client.get("/api/home", params={"conference": "ICLR", "year": 2025})
    assert home.status_code == 200
    assert home.json()["latest_papers"][0]["paper_id"] == "paper1"
    assert home.json()["latest_papers"][0]["overall_score"] == 80
    assert home.json()["leaderboards"]["red"][0]["reviewer_key"] == "R1"
    assert home.json()["audited_count"] == 1
    assert home.json()["stats"] == {"paper_count": 2, "review_count": 1, "scored_review_count": 1, "audited_count": 1}
    # Home feed exposes only real vote totals, ignoring stored synthetic baselines.
    assert home.json()["latest_papers"][0]["social"] == {"up": 0, "down": 0}
    assert home.json()["latest_papers"][0]["vote_total"] == 0

    scorecard = client.get("/api/papers/paper1/scorecard")
    assert scorecard.status_code == 200
    rendered = json.dumps(scorecard.json())
    assert "hybrid_scores" not in rendered
    assert scorecard.json()["paper"]["paper_id"] == "paper1"

    vote = client.post("/api/papers/paper1/reviewers/R1/votes", json={"vote": "up"})
    assert vote.status_code == 200
    assert vote.json()["scorecard"]["reviewers"][0]["social"]["up"] == 1

    missing = client.get("/api/papers/paper2/scorecard")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "scorecard_not_ready"
    job = client.post("/api/papers/paper2/scoring-jobs")
    assert job.status_code == 200
    assert job.json()["status"] == "queued"

    outside_scorecard = client.get("/api/papers/not-a-real-paper/scorecard")
    assert outside_scorecard.status_code == 404
    assert outside_scorecard.json()["detail"]["code"] == "paper_not_found"
    outside_job = client.post("/api/papers/not-a-real-paper/scoring-jobs")
    assert outside_job.status_code == 404
    assert outside_job.json()["detail"]["code"] == "paper_not_found"


def test_reviewer_comment_flow(tmp_path):
    factory = session_factory_for(tmp_path)
    seed(factory, tmp_path)
    settings = ServerSettings(
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        artifact_root=tmp_path / "artifacts",
        scoring_memory_path=tmp_path / "memory.jsonl",
    )
    app = create_app(settings=settings, session_factory=factory)
    client = TestClient(app)

    empty = client.get("/api/papers/paper1/reviewers/R1/comments")
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    created = client.post(
        "/api/papers/paper1/reviewers/R1/comments",
        json={"body": "Reviewer 2 asked me to cite 15 of their own papers."},
    )
    assert created.status_code == 200
    assert created.json()["comment"]["body"] == "Reviewer 2 asked me to cite 15 of their own papers."
    assert created.json()["comment"]["author"].startswith("anon-")
    assert len(created.json()["items"]) == 1

    listed = client.get("/api/papers/paper1/reviewers/R1/comments")
    assert listed.json()["items"][0]["body"] == "Reviewer 2 asked me to cite 15 of their own papers."

    # Comments are embedded per reviewer in the public scorecard payload.
    scorecard = client.get("/api/papers/paper1/scorecard")
    reviewer = scorecard.json()["reviewers"][0]
    assert reviewer["comment_count"] == 1
    assert reviewer["comments"][0]["body"] == "Reviewer 2 asked me to cite 15 of their own papers."

    # Leaderboard rows surface the comment count so busy reviewers stand out.
    home = client.get("/api/home", params={"conference": "ICLR", "year": 2025})
    assert home.json()["leaderboards"]["red"][0]["comment_count"] == 1

    # Blank comments are rejected; unknown papers 404.
    blank = client.post("/api/papers/paper1/reviewers/R1/comments", json={"body": "   "})
    assert blank.status_code == 400
    missing = client.post("/api/papers/ghost/reviewers/R1/comments", json={"body": "hi"})
    assert missing.status_code == 404
