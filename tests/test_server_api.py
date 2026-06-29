import json

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
                "dimensions": [],
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

    home = client.get("/api/home", params={"conference": "ICLR", "year": 2025})
    assert home.status_code == 200
    assert home.json()["latest_papers"][0]["paper_id"] == "paper1"
    assert home.json()["latest_papers"][0]["overall_score"] == 80
    assert home.json()["leaderboards"]["red"][0]["reviewer_key"] == "R1"
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
    job = client.post("/api/papers/paper2/scoring-jobs")
    assert job.status_code == 200
    assert job.json()["status"] == "queued"
