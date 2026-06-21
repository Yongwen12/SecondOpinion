import json

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from secondopinion.server.database import init_db, make_engine, make_session_factory, session_scope
from secondopinion.server.ingest import import_normalized_dataset
from secondopinion.server.repository import search_papers


def session_factory_for(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'server.db'}")
    init_db(engine)
    return make_session_factory(engine)


def write_normalized(tmp_path):
    payload = {
        "dataset": "iclr_2025",
        "papers": [
            {
                "paper_id": "paper1",
                "openreview_forum_id": "paper1",
                "venue": "ICLR",
                "year": 2025,
                "title": "A Careful Baseline Study",
                "abstract": "We study baselines.",
                "decision": "Accept",
                "pdf_url": "https://openreview.net/pdf?id=paper1",
                "reviews": [
                    {
                        "review_id": "review1",
                        "review_text": "The paper should compare against a standard baseline.",
                        "weaknesses": "Missing baseline comparison.",
                        "questions": "Can the authors report runtime?",
                        "rating_raw": "6",
                        "rating_normalized": 6.0,
                        "confidence_raw": "4",
                        "confidence_normalized": 8.0,
                    }
                ],
            }
        ],
    }
    path = tmp_path / "iclr_2025_sample.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_import_normalized_dataset_is_idempotent_and_searchable(tmp_path):
    factory = session_factory_for(tmp_path)
    path = write_normalized(tmp_path)

    with session_scope(factory) as session:
        first = import_normalized_dataset(session, path)
        second = import_normalized_dataset(session, path)
        results = search_papers(session, conference_id="ICLR", query="baseline")

    assert first["paper_count"] == 1
    assert second["review_count"] == 1
    assert results["items"][0]["paper_id"] == "paper1"
    assert results["items"][0]["review_count"] == 1
