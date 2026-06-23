import json

import pytest

pytest.importorskip("sqlalchemy")

from secondopinion.server.config import ServerSettings
from secondopinion.server.database import init_db, make_engine, make_session_factory, session_scope
from secondopinion.server.ingest import import_normalized_dataset
from secondopinion.server.models import Paper, ScoringJob, utcnow
from secondopinion.server.repository import (
    enqueue_scoring_jobs,
    retry_failed_scoring_jobs,
    scoring_status,
    store_scorecard,
)


def session_factory_for(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'batch.db'}")
    init_db(engine)
    return make_session_factory(engine)


def write_normalized(tmp_path):
    payload = {
        "dataset": "iclr_2025",
        "papers": [
            {
                "paper_id": f"paper{i}",
                "openreview_forum_id": f"paper{i}",
                "venue": "ICLR",
                "year": 2025,
                "title": f"Batch Paper {i}",
                "abstract": "A paper.",
                "reviews": [
                    {
                        "review_id": f"review{i}",
                        "review_text": "The paper should add a baseline.",
                        "weaknesses": "Missing baseline comparison.",
                    }
                ],
            }
            for i in range(1, 4)
        ],
    }
    path = tmp_path / "normalized.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_store_scorecard_flushes_parent_before_reviewer_scores():
    class RecordingSession:
        def __init__(self):
            self.events = []

        def get(self, *_args):
            return None

        def add(self, obj):
            self.events.append(("add", obj.__class__.__name__))

        def flush(self):
            self.events.append(("flush", ""))

        def execute(self, *_args):
            self.events.append(("execute", ""))

    session = RecordingSession()
    paper = Paper(paper_id="paper1", conference_id="ICLR", year=2025, title="Paper")
    store_scorecard(
        session,
        paper=paper,
        public_json={
            "schema_version": "reviewer-public-scorecard-v0.1",
            "reviewers": [{"reviewer_key": "R1", "score": 72}],
        },
        internal_artifact_path="artifact.json",
        scorer_version="s1",
        memory_index_version="m1",
    )

    first_flush = session.events.index(("flush", ""))
    first_execute = session.events.index(("execute", ""))
    assert first_flush < first_execute


def test_batch_enqueue_status_and_retry_failed(tmp_path):
    factory = session_factory_for(tmp_path)
    settings = ServerSettings(
        database_url=f"sqlite:///{tmp_path / 'batch.db'}",
        artifact_root=tmp_path / "artifacts",
        scoring_memory_path=tmp_path / "missing.jsonl",
    )

    with session_scope(factory) as session:
        import_normalized_dataset(session, write_normalized(tmp_path))
        dry_run = enqueue_scoring_jobs(
            session,
            conference_id="ICLR",
            year=2025,
            limit=2,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
            dry_run=True,
        )
        assert dry_run["created"] == 2
        assert scoring_status(
            session,
            conference_id="ICLR",
            year=2025,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )["queued"] == 0

        first = enqueue_scoring_jobs(
            session,
            conference_id="ICLR",
            year=2025,
            limit=2,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )
        assert first["created"] == 2
        status = scoring_status(
            session,
            conference_id="ICLR",
            year=2025,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )
        assert status["total_papers"] == 3
        assert status["queued"] == 2
        assert status["not_queued"] == 1

        failed_job = session.query(ScoringJob).filter_by(paper_id=first["created_paper_ids"][0]).one()
        failed_job.status = "failed"
        failed_job.error = "boom"
        failed_job.completed_at = utcnow()
        session.flush()

        retried = retry_failed_scoring_jobs(
            session,
            conference_id="ICLR",
            year=2025,
            limit=1,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )
        assert retried["retried"] == 1


def test_enqueue_missing_only_skips_existing_scorecard(tmp_path):
    factory = session_factory_for(tmp_path)
    settings = ServerSettings(
        database_url=f"sqlite:///{tmp_path / 'batch.db'}",
        artifact_root=tmp_path / "artifacts",
        scoring_memory_path=tmp_path / "missing.jsonl",
    )

    with session_scope(factory) as session:
        import_normalized_dataset(session, write_normalized(tmp_path))
        paper = session.get(Paper, "paper1")
        store_scorecard(
            session,
            paper=paper,
            public_json={"schema_version": "reviewer-public-scorecard-v0.1", "reviewers": []},
            internal_artifact_path="artifact.json",
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )
        summary = enqueue_scoring_jobs(
            session,
            conference_id="ICLR",
            year=2025,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )

    assert summary["created"] == 2
    assert summary["skipped_scored"] == 1
