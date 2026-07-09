import json

import pytest

pytest.importorskip("sqlalchemy")

from secondopinion.batch_review_scoring import (
    build_scoring_batch,
    load_custom_ids,
    normalized_quality_report,
    normalize_score_payload,
    split_scoring_batch,
    truncate_clean_text,
)
from secondopinion.server.database import init_db, make_engine, make_session_factory, session_scope
from secondopinion.server.ingest import import_normalized_dataset
from secondopinion.server.repository import build_leaderboards, store_scorecard


def normalized_payload():
    return {
        "dataset": "iclr_2025",
        "papers": [
            {
                "paper_id": "paper1",
                "openreview_forum_id": "paper1",
                "venue": "ICLR",
                "year": 2025,
                "title": "A Useful Paper",
                "abstract": "We test a method.",
                "decision": "Accept",
                "reviews": [
                    {
                        "review_id": "review1",
                        "summary": "Clear contribution.",
                        "weaknesses": "The paper should add an ablation.",
                        "rating_raw": "6",
                        "confidence_raw": "4",
                    },
                    {
                        "review_id": "review2",
                        "weaknesses": "This is vague and overclaims novelty.",
                    },
                    {
                        "review_id": "author-response",
                        "review_text": "We thank the reviewers and have uploaded a revised manuscript.",
                    },
                ],
            }
        ],
    }


def test_quality_report_counts_core_review_fields():
    report = normalized_quality_report(normalized_payload())

    assert report["paper_count"] == 1
    assert report["review_count"] == 3
    assert report["empty_core_review_count"] == 0
    assert report["decision_coverage_rate"] == 1.0
    assert report["rating_coverage_count"] == 1


def test_build_scoring_batch_writes_openai_batch_shape(tmp_path):
    source = tmp_path / "normalized.json"
    output = tmp_path / "batch.jsonl"
    manifest = tmp_path / "manifest.json"
    source.write_text(json.dumps(normalized_payload()), encoding="utf-8")

    summary = build_scoring_batch(
        normalized_path=source,
        output_jsonl=output,
        manifest_path=manifest,
        model="gpt-5.4-nano",
        limit_reviews=1,
    )

    line = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
    assert summary["request_count"] == 1
    assert line["method"] == "POST"
    assert line["url"] == "/v1/chat/completions"
    assert line["body"]["model"] == "gpt-5.4-nano"
    assert line["body"]["response_format"]["type"] == "json_schema"
    assert summary["tasks"][0]["paper_id"] == "paper1"


def test_new_leaderboards_read_batch_dimensions(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'server.db'}")
    init_db(engine)
    factory = make_session_factory(engine)
    source = tmp_path / "normalized.json"
    source.write_text(json.dumps(normalized_payload()), encoding="utf-8")

    with session_scope(factory) as session:
        import_normalized_dataset(session, source)
        paper = session.get(__import__("secondopinion.server.models", fromlist=["Paper"]).Paper, "paper1")
        store_scorecard(
            session,
            paper=paper,
            public_json={
                "schema_version": "reviewer-public-scorecard-v0.1",
                "reviewers": [
                    {
                        "reviewer_key": "R1",
                        "nickname": "Outrage Beacon",
                        "avatar_key": "r1",
                        "score": 91,
                        "dimensions": [
                            {"key": "outrage", "score": 91, "quote": "too vague", "verdict": "Overheated"},
                            {"key": "toxicity", "score": 10},
                            {"key": "helpfulness", "score": 35},
                        ],
                    },
                    {
                        "reviewer_key": "R2",
                        "nickname": "Actual Reviewer",
                        "avatar_key": "r2",
                        "score": 15,
                        "dimensions": [
                            {"key": "outrage", "score": 15},
                            {"key": "toxicity", "score": 2},
                            {"key": "helpfulness", "score": 88, "quote": "add an ablation", "verdict": "Useful"},
                        ],
                    },
                ],
            },
            internal_artifact_path="",
            scorer_version="batch-outrage-scorer-v0.1",
            memory_index_version="openreview-comments-v0.1",
        )
        boards = build_leaderboards(session, conference_id="ICLR", year=2025, limit=10)

    assert boards["overall"][0]["reviewer_key"] == "R1"
    assert boards["toxic"][0]["reviewer_key"] == "R1"
    assert boards["helpful"][0]["reviewer_key"] == "R2"
    assert boards["overall"][0]["quote"] == "too vague"


def test_leaderboards_filter_obvious_author_and_admin_noise(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'server.db'}")
    init_db(engine)
    factory = make_session_factory(engine)
    source = tmp_path / "normalized.json"
    source.write_text(json.dumps(normalized_payload()), encoding="utf-8")

    with session_scope(factory) as session:
        import_normalized_dataset(session, source)
        paper = session.get(__import__("secondopinion.server.models", fromlist=["Paper"]).Paper, "paper1")
        store_scorecard(
            session,
            paper=paper,
            public_json={
                "schema_version": "reviewer-public-scorecard-v0.1",
                "reviewers": [
                    {
                        "reviewer_key": "R1",
                        "nickname": "Author Noise",
                        "avatar_key": "r1",
                        "score": 100,
                        "dimensions": [
                            {"key": "outrage", "score": 100, "quote": "Weaknesses: Thank you for your helpful comments.", "verdict": "Non-substantive review"},
                            {"key": "toxicity", "score": 0},
                            {"key": "helpfulness", "score": 50},
                        ],
                    },
                    {
                        "reviewer_key": "R2",
                        "nickname": "Displayable Reviewer",
                        "avatar_key": "r2",
                        "score": 90,
                        "dimensions": [
                            {"key": "outrage", "score": 90, "quote": "The paper lacks baselines and the claims are unsupported.", "verdict": "Harsh but review-like"},
                            {"key": "toxicity", "score": 5},
                            {"key": "helpfulness", "score": 20},
                        ],
                    },
                ],
            },
            internal_artifact_path="",
            scorer_version="batch-outrage-scorer-v0.1",
            memory_index_version="openreview-comments-v0.1",
        )
        boards = build_leaderboards(session, conference_id="ICLR", year=2025, limit=10)

    assert [row["reviewer_key"] for row in boards["overall"]] == ["R2"]


def test_normalize_score_payload_clamps_scores():
    payload = normalize_score_payload({"outrage": 130, "toxicity": -2, "helpfulness": "77", "actionable": True})

    assert payload["outrage"] == 100
    assert payload["toxicity"] == 0
    assert payload["helpfulness"] == 77

def test_normalize_score_payload_rescales_zero_to_ten_outputs():
    payload = normalize_score_payload({"outrage": 7, "toxicity": 2, "helpfulness": 6, "actionable": True})

    assert payload["outrage"] == 70
    assert payload["toxicity"] == 20
    assert payload["helpfulness"] == 60


def test_truncate_clean_text_keeps_word_boundary():
    text = truncate_clean_text("alpha beta gamma delta", 15)

    assert text == "alpha beta..."
    assert len(text) <= 15


def test_build_scoring_batch_can_exclude_existing_custom_ids(tmp_path):
    source = tmp_path / "normalized.json"
    output = tmp_path / "batch.jsonl"
    manifest = tmp_path / "manifest.json"
    existing = tmp_path / "existing.jsonl"
    source.write_text(json.dumps(normalized_payload()), encoding="utf-8")
    first = build_scoring_batch(
        normalized_path=source,
        output_jsonl=tmp_path / "first.jsonl",
        manifest_path=tmp_path / "first_manifest.json",
        model="gpt-5.4-nano",
        limit_reviews=1,
    )
    existing.write_text(json.dumps({"custom_id": first["tasks"][0]["custom_id"]}) + "\n", encoding="utf-8")

    summary = build_scoring_batch(
        normalized_path=source,
        output_jsonl=output,
        manifest_path=manifest,
        model="gpt-5.4-nano",
        exclude_custom_ids=load_custom_ids([str(existing)]),
    )

    assert summary["request_count"] == 1
    assert summary["tasks"][0]["review_id"] == "review2"


def test_split_scoring_batch_writes_part_manifests(tmp_path):
    source = tmp_path / "normalized.json"
    batch = tmp_path / "batch.jsonl"
    manifest = tmp_path / "manifest.json"
    source.write_text(json.dumps(normalized_payload()), encoding="utf-8")
    build_scoring_batch(normalized_path=source, output_jsonl=batch, manifest_path=manifest, model="gpt-5.4-nano")

    summary = split_scoring_batch(
        batch_jsonl=batch,
        manifest_path=manifest,
        output_dir=tmp_path / "parts",
        prefix="sample",
        max_requests=1,
    )

    assert summary["chunk_count"] == 2
    for chunk in summary["chunks"]:
        part_manifest = json.loads(open(chunk["manifest_path"], encoding="utf-8").read())
        assert part_manifest["request_count"] == 1
        assert len(part_manifest["tasks"]) == 1
