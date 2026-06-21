import json

import pytest

pytest.importorskip("sqlalchemy")

from secondopinion.scoring_memory import build_memory_records
from secondopinion.server.config import ServerSettings
from secondopinion.server.database import init_db, make_engine, make_session_factory, session_scope
from secondopinion.server.ingest import import_normalized_dataset
from secondopinion.server.repository import create_scoring_job, latest_scorecard
from secondopinion.server.worker import run_next_scoring_job


def session_factory_for(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'worker.db'}")
    init_db(engine)
    return make_session_factory(engine)


def test_worker_runs_paper_to_public_scorecard_without_exposing_internal_fields(tmp_path):
    factory = session_factory_for(tmp_path)
    normalized = {
        "dataset": "iclr_2025",
        "papers": [
            {
                "paper_id": "paper1",
                "venue": "ICLR",
                "year": 2025,
                "title": "Runtime Baselines",
                "abstract": "A paper.",
                "reviews": [
                    {
                        "review_id": "review1",
                        "review_text": "The authors should add a retrieval baseline and report runtime.",
                        "weaknesses": "The paper lacks a retrieval baseline and runtime comparison.",
                        "rating_normalized": 6.0,
                        "confidence_normalized": 8.0,
                    }
                ],
            }
        ],
    }
    path = tmp_path / "normalized.json"
    path.write_text(json.dumps(normalized), encoding="utf-8")
    memory = build_memory_records(
        [
            {
                "task_id": "m1",
                "dataset": "ReAct",
                "input_text": "Add a baseline comparison and report runtime.",
                "gold_label": "actionable",
            }
        ],
        dimension="actionability",
        text_fields=["input_text"],
    )
    settings = ServerSettings(
        database_url=f"sqlite:///{tmp_path / 'worker.db'}",
        artifact_root=tmp_path / "artifacts",
        scoring_memory_path=tmp_path / "missing.jsonl",
    )

    with session_scope(factory) as session:
        import_normalized_dataset(session, path)
        create_scoring_job(
            session,
            paper_id="paper1",
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )

    result = run_next_scoring_job(factory, settings=settings, memory_records=memory)

    with session_scope(factory) as session:
        scorecard = latest_scorecard(session, "paper1")

    rendered = json.dumps(scorecard.public_json)
    assert result["status"] == "succeeded"
    assert scorecard.public_json["reviewers"][0]["reviewer_key"] == "R1"
    assert "hybrid_scores" not in rendered
    assert "memory_prior" not in rendered
    assert "mapped_score" not in rendered
