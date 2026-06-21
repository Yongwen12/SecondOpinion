from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from .models import Conference, IngestRun, Paper, Review
from .repository import register_memory_index, store_scorecard
from ..reviewer_public_scorecard import PUBLIC_SCORECARD_VERSION
from ..scoring_memory import read_jsonl as read_scoring_jsonl


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def import_normalized_dataset(session: Session, path: str | Path) -> dict[str, Any]:
    payload = read_json(path)
    venue = str(payload.get("venue") or payload.get("dataset", "ICLR").split("_")[0]).upper()
    year = int(payload.get("year") or str(payload.get("dataset", "")).split("_")[-1] or 0)
    conference_id = venue
    conference = session.get(Conference, conference_id)
    if conference is None:
        conference = Conference(conference_id=conference_id, name=venue, venue=venue)
        session.add(conference)
    papers = payload.get("papers") or []
    paper_count = 0
    review_count = 0
    for paper_item in papers:
        if not isinstance(paper_item, dict):
            continue
        paper_id = str(paper_item.get("paper_id") or paper_item.get("openreview_forum_id") or "").strip()
        if not paper_id:
            continue
        paper = session.get(Paper, paper_id)
        if paper is None:
            paper = Paper(
                paper_id=paper_id,
                openreview_forum_id=str(paper_item.get("openreview_forum_id") or paper_id),
                conference_id=conference_id,
                venue=str(paper_item.get("venue") or venue),
                year=int(paper_item.get("year") or year),
                title=str(paper_item.get("title") or "Untitled submission"),
            )
            session.add(paper)
        paper.openreview_forum_id = str(paper_item.get("openreview_forum_id") or paper_id)
        paper.conference_id = conference_id
        paper.venue = str(paper_item.get("venue") or venue)
        paper.year = int(paper_item.get("year") or year)
        paper.title = str(paper_item.get("title") or "Untitled submission")
        paper.abstract = str(paper_item.get("abstract") or "")
        paper.decision = str(paper_item.get("decision") or "")
        paper.pdf_url = str(paper_item.get("pdf_url") or "")
        paper.source_json = compact_paper_source(paper_item)
        paper_count += 1
        for index, review_item in enumerate(paper_item.get("reviews") or [], start=1):
            if not isinstance(review_item, dict):
                continue
            review_id = str(review_item.get("review_id") or f"{paper_id}:review:{index}")
            review = session.get(Review, review_id)
            if review is None:
                review = Review(review_id=review_id, paper_id=paper_id)
                session.add(review)
            review.paper_id = paper_id
            review.reviewer_index = index
            review.reviewer_internal_id = review_id
            review.review_text = str(review_item.get("review_text") or "")
            review.summary = str(review_item.get("summary") or "")
            review.strengths = str(review_item.get("strengths") or "")
            review.weaknesses = str(review_item.get("weaknesses") or "")
            review.questions = str(review_item.get("questions") or "")
            review.rating_raw = str(review_item.get("rating_raw") or "")
            review.rating_normalized = as_float(review_item.get("rating_normalized"))
            review.confidence_raw = str(review_item.get("confidence_raw") or "")
            review.confidence_normalized = as_float(review_item.get("confidence_normalized"))
            review.review_stage = str(review_item.get("review_stage") or "initial")
            review.raw_invitation = str(review_item.get("raw_invitation") or "")
            review.source_json = compact_review_source(review_item)
            review_count += 1
    run = IngestRun(
        ingest_run_id=f"ingest_{uuid.uuid4().hex[:16]}",
        source=str(path),
        status="succeeded",
        summary_json={"paper_count": paper_count, "review_count": review_count, "dataset": payload.get("dataset", "")},
    )
    session.add(run)
    session.flush()
    return run.summary_json | {"ingest_run_id": run.ingest_run_id}


def compact_paper_source(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "authors_anonymized": paper.get("authors_anonymized"),
        "rebuttals": paper.get("rebuttals", []),
        "decisions": paper.get("decisions", []),
    }


def compact_review_source(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_time": review.get("snapshot_time"),
        "raw_invitation": review.get("raw_invitation"),
    }


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def import_public_scorecard(
    session: Session,
    *,
    path: str | Path,
    paper_id: str = "second-opinion-demo",
    scorer_version: str,
    memory_index_version: str,
) -> dict[str, Any]:
    public = read_json(path)
    paper_info = public.get("paper") or {}
    venue = str(paper_info.get("venue") or "ICLR")
    year = int(paper_info.get("year") or 2026)
    conference = session.get(Conference, venue)
    if conference is None:
        conference = Conference(conference_id=venue, name=venue, venue=venue)
        session.add(conference)
    paper = session.get(Paper, paper_id)
    if paper is None:
        paper = Paper(
            paper_id=paper_id,
            openreview_forum_id=paper_id,
            conference_id=venue,
            venue=venue,
            year=year,
            title=str(paper_info.get("title") or "Reviewer Signal Demo Submission"),
        )
        session.add(paper)
    paper.conference_id = venue
    paper.venue = venue
    paper.year = year
    paper.title = str(paper_info.get("title") or paper.title)
    paper.source_json = {"source": "frontend_demo_scorecard", "path": str(path)}
    scorecard = store_scorecard(
        session,
        paper=paper,
        public_json=public,
        internal_artifact_path="",
        scorer_version=scorer_version,
        memory_index_version=memory_index_version,
    )
    return {
        "paper_id": paper.paper_id,
        "scorecard_id": scorecard.scorecard_id,
        "schema_version": public.get("schema_version", PUBLIC_SCORECARD_VERSION),
        "reviewer_count": len(public.get("reviewers", [])),
    }


def register_scoring_memory_from_file(
    session: Session,
    *,
    path: str | Path,
    version: str,
    active: bool = True,
) -> dict[str, Any]:
    records = read_scoring_jsonl(path)
    dimensions = Counter(str(record.get("dimension", "") or "unknown") for record in records)
    index = register_memory_index(
        session,
        version=version,
        path=str(path),
        record_count=len(records),
        dimensions=dict(dimensions),
        active=active,
    )
    return {
        "version": index.version,
        "path": index.path,
        "record_count": index.record_count,
        "dimensions": index.dimensions_json,
    }
