from __future__ import annotations

import copy
import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from .models import (
    Conference,
    MemoryIndex,
    Paper,
    Review,
    ReviewerScore,
    Scorecard,
    ScoringJob,
    Vote,
    utcnow,
)
from ..reviewer_public_scorecard import PUBLIC_SCORECARD_VERSION


def stable_scorecard_id(paper_id: str, scorer_version: str, memory_index_version: str) -> str:
    return f"scorecard:{paper_id}:{scorer_version}:{memory_index_version}"


def create_scoring_job(
    session: Session,
    *,
    paper_id: str,
    requested_by_session: str = "",
    scorer_version: str,
    memory_index_version: str,
) -> ScoringJob:
    existing = session.execute(
        select(ScoringJob)
        .where(
            ScoringJob.paper_id == paper_id,
            ScoringJob.status.in_(["queued", "running"]),
            ScoringJob.scorer_version == scorer_version,
            ScoringJob.memory_index_version == memory_index_version,
        )
        .order_by(ScoringJob.created_at.desc())
    ).scalar_one_or_none()
    if existing:
        return existing
    job = ScoringJob(
        job_id=f"job_{uuid.uuid4().hex[:16]}",
        paper_id=paper_id,
        status="queued",
        requested_by_session=requested_by_session,
        scorer_version=scorer_version,
        memory_index_version=memory_index_version,
    )
    session.add(job)
    session.flush()
    return job


def enqueue_scoring_jobs(
    session: Session,
    *,
    conference_id: str | None = None,
    year: int | None = None,
    paper_ids: list[str] | None = None,
    limit: int | None = None,
    requested_by_session: str = "server_batch",
    scorer_version: str,
    memory_index_version: str,
    missing_only: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    papers = list(_filtered_papers(session, conference_id=conference_id, year=year, paper_ids=paper_ids))
    created: list[str] = []
    skipped_scored = 0
    skipped_active = 0
    considered = 0
    for paper in papers:
        if limit is not None and considered >= limit:
            break
        considered += 1
        if missing_only and _has_scorecard_for_version(
            session,
            paper.paper_id,
            scorer_version=scorer_version,
            memory_index_version=memory_index_version,
        ):
            skipped_scored += 1
            continue
        if _has_active_scoring_job(
            session,
            paper.paper_id,
            scorer_version=scorer_version,
            memory_index_version=memory_index_version,
        ):
            skipped_active += 1
            continue
        if dry_run:
            created.append(paper.paper_id)
            continue
        job = create_scoring_job(
            session,
            paper_id=paper.paper_id,
            requested_by_session=requested_by_session,
            scorer_version=scorer_version,
            memory_index_version=memory_index_version,
        )
        created.append(job.paper_id)
    return {
        "conference_id": conference_id,
        "year": year,
        "paper_ids": paper_ids or [],
        "considered": considered,
        "created": len(created),
        "created_paper_ids": created,
        "skipped_scored": skipped_scored,
        "skipped_active": skipped_active,
        "dry_run": dry_run,
    }


def scoring_status(
    session: Session,
    *,
    conference_id: str | None = None,
    year: int | None = None,
    scorer_version: str,
    memory_index_version: str,
) -> dict[str, Any]:
    paper_ids = [
        paper.paper_id
        for paper in _filtered_papers(session, conference_id=conference_id, year=year, paper_ids=None)
    ]
    if not paper_ids:
        return {
            "conference_id": conference_id,
            "year": year,
            "total_papers": 0,
            "scored": 0,
            "queued": 0,
            "running": 0,
            "failed": 0,
            "not_queued": 0,
            "scorer_version": scorer_version,
            "memory_index_version": memory_index_version,
        }
    scored_ids = set(
        session.execute(
            select(Scorecard.paper_id).where(
                Scorecard.paper_id.in_(paper_ids),
                Scorecard.scorer_version == scorer_version,
                Scorecard.memory_index_version == memory_index_version,
            )
        ).scalars()
    )
    jobs = list(
        session.execute(
            select(ScoringJob).where(
                ScoringJob.paper_id.in_(paper_ids),
                ScoringJob.scorer_version == scorer_version,
                ScoringJob.memory_index_version == memory_index_version,
            )
        ).scalars()
    )
    latest_by_paper: dict[str, ScoringJob] = {}
    for job in jobs:
        current = latest_by_paper.get(job.paper_id)
        if current is None or job.created_at > current.created_at:
            latest_by_paper[job.paper_id] = job
    queued_ids = {paper_id for paper_id, job in latest_by_paper.items() if job.status == "queued" and paper_id not in scored_ids}
    running_ids = {paper_id for paper_id, job in latest_by_paper.items() if job.status == "running" and paper_id not in scored_ids}
    failed_ids = {paper_id for paper_id, job in latest_by_paper.items() if job.status == "failed" and paper_id not in scored_ids}
    pending_ids = set(paper_ids) - scored_ids - queued_ids - running_ids - failed_ids
    return {
        "conference_id": conference_id,
        "year": year,
        "total_papers": len(paper_ids),
        "scored": len(scored_ids),
        "queued": len(queued_ids),
        "running": len(running_ids),
        "failed": len(failed_ids),
        "not_queued": len(pending_ids),
        "scorer_version": scorer_version,
        "memory_index_version": memory_index_version,
    }


def retry_failed_scoring_jobs(
    session: Session,
    *,
    conference_id: str | None = None,
    year: int | None = None,
    limit: int | None = None,
    scorer_version: str,
    memory_index_version: str,
) -> dict[str, Any]:
    paper_ids = [
        paper.paper_id
        for paper in _filtered_papers(session, conference_id=conference_id, year=year, paper_ids=None)
    ]
    if not paper_ids:
        return {"conference_id": conference_id, "year": year, "retried": 0, "retried_paper_ids": []}
    jobs = list(
        session.execute(
            select(ScoringJob)
            .where(
                ScoringJob.status == "failed",
                ScoringJob.scorer_version == scorer_version,
                ScoringJob.memory_index_version == memory_index_version,
                ScoringJob.paper_id.in_(paper_ids),
            )
            .order_by(ScoringJob.completed_at.desc().nullslast(), ScoringJob.updated_at.desc())
        ).scalars()
    )
    retried: list[str] = []
    seen_papers: set[str] = set()
    for job in jobs:
        if limit is not None and len(retried) >= limit:
            break
        if job.paper_id in seen_papers:
            continue
        seen_papers.add(job.paper_id)
        if _has_scorecard_for_version(
            session,
            job.paper_id,
            scorer_version=scorer_version,
            memory_index_version=memory_index_version,
        ):
            continue
        if _has_active_scoring_job(
            session,
            job.paper_id,
            scorer_version=scorer_version,
            memory_index_version=memory_index_version,
        ):
            continue
        create_scoring_job(
            session,
            paper_id=job.paper_id,
            requested_by_session="server_retry_failed",
            scorer_version=scorer_version,
            memory_index_version=memory_index_version,
        )
        retried.append(job.paper_id)
    return {
        "conference_id": conference_id,
        "year": year,
        "retried": len(retried),
        "retried_paper_ids": retried,
    }

def latest_scorecard(session: Session, paper_id: str) -> Scorecard | None:
    return session.execute(
        select(Scorecard)
        .where(Scorecard.paper_id == paper_id)
        .order_by(Scorecard.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def store_scorecard(
    session: Session,
    *,
    paper: Paper,
    public_json: dict[str, Any],
    internal_artifact_path: str,
    scorer_version: str,
    memory_index_version: str,
) -> Scorecard:
    scorecard_id = stable_scorecard_id(paper.paper_id, scorer_version, memory_index_version)
    scorecard = session.get(Scorecard, scorecard_id)
    if scorecard is None:
        scorecard = Scorecard(
            scorecard_id=scorecard_id,
            paper_id=paper.paper_id,
            schema_version=str(public_json.get("schema_version") or PUBLIC_SCORECARD_VERSION),
            scorer_version=scorer_version,
            memory_index_version=memory_index_version,
            public_json=public_json,
            internal_artifact_path=internal_artifact_path,
        )
        session.add(scorecard)
    else:
        scorecard.schema_version = str(public_json.get("schema_version") or PUBLIC_SCORECARD_VERSION)
        scorecard.public_json = public_json
        scorecard.internal_artifact_path = internal_artifact_path
        scorecard.created_at = utcnow()

    session.flush()
    session.execute(delete(ReviewerScore).where(ReviewerScore.scorecard_id == scorecard_id))
    for reviewer in public_json.get("reviewers", []):
        if not isinstance(reviewer, dict):
            continue
        session.add(
            ReviewerScore(
                scorecard_id=scorecard_id,
                paper_id=paper.paper_id,
                conference_id=paper.conference_id,
                year=paper.year,
                reviewer_key=str(reviewer.get("reviewer_key", "")),
                nickname=str(reviewer.get("nickname", "")),
                avatar_key=str(reviewer.get("avatar_key", "")),
                score=int(reviewer.get("score") or 0),
                dimensions_json=list(reviewer.get("dimensions") or []),
                social_json=dict(reviewer.get("social") or {}),
            )
        )
    session.flush()
    return scorecard


def paper_to_public_dict(paper: Paper) -> dict[str, Any]:
    return {
        "paper_id": paper.paper_id,
        "openreview_forum_id": paper.openreview_forum_id,
        "conference_id": paper.conference_id,
        "venue": paper.venue,
        "year": paper.year,
        "title": paper.title,
        "abstract": paper.abstract,
        "decision": paper.decision,
        "pdf_url": paper.pdf_url,
        "review_count": len(paper.reviews),
    }


def job_to_public_dict(job: ScoringJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "paper_id": job.paper_id,
        "status": job.status,
        "scorer_version": job.scorer_version,
        "memory_index_version": job.memory_index_version,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "updated_at": job.updated_at.isoformat() if job.updated_at else "",
        "completed_at": job.completed_at.isoformat() if job.completed_at else "",
    }


def list_conferences(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Conference, func.count(Paper.paper_id), func.min(Paper.year), func.max(Paper.year))
        .join(Paper, Paper.conference_id == Conference.conference_id, isouter=True)
        .group_by(Conference.conference_id)
        .order_by(Conference.conference_id)
    ).all()
    return [
        {
            "conference_id": conference.conference_id,
            "name": conference.name,
            "venue": conference.venue,
            "paper_count": int(count or 0),
            "min_year": min_year,
            "max_year": max_year,
        }
        for conference, count, min_year, max_year in rows
    ]


def latest_scored_papers(
    session: Session,
    *,
    conference_id: str | None = None,
    year: int | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    limit = max(1, min(50, limit))
    stmt = select(Paper, Scorecard).join(Scorecard, Scorecard.paper_id == Paper.paper_id)
    if conference_id:
        stmt = stmt.where(Paper.conference_id == conference_id)
    if year is not None:
        stmt = stmt.where(Paper.year == year)
    rows = session.execute(stmt.order_by(Scorecard.created_at.desc()).limit(limit)).all()
    paper_ids = [paper.paper_id for paper, _ in rows]
    votes_by_paper: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    if paper_ids:
        vote_rows = session.execute(
            select(Vote.paper_id, Vote.vote, func.count(Vote.id))
            .where(Vote.paper_id.in_(paper_ids))
            .group_by(Vote.paper_id, Vote.vote)
        ).all()
        for pid, vote, count in vote_rows:
            if vote in ("up", "down"):
                votes_by_paper[str(pid)][str(vote)] = int(count)
    items = []
    for paper, scorecard in rows:
        public_json = scorecard.public_json or {}
        summary = public_json.get("summary") or {}
        topics = public_json.get("topics") or []
        reviewers = public_json.get("reviewers") or []
        topic_labels = [str(item.get("text") or item.get("label") or "") for item in topics if isinstance(item, dict)]

        items.append(
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "venue": paper.venue,
                "conference_id": paper.conference_id,
                "year": paper.year,
                "decision": paper.decision,
                "review_count": len(paper.reviews),
                "overall_score": int(summary.get("overall_score") or 0),
                "signal_label": str(summary.get("signal_label") or "Review signal"),
                "comment_count": int(summary.get("comment_count") or 0),
                "topic_count": int(summary.get("topic_count") or 0),
                "topics": [item for item in topic_labels if item][:3],
                "social": votes_by_paper[paper.paper_id],
                "vote_total": votes_by_paper[paper.paper_id]["up"] + votes_by_paper[paper.paper_id]["down"],
                "created_at": scorecard.created_at.isoformat() if scorecard.created_at else "",
            }
        )
    return items


def search_papers(
    session: Session,
    *,
    conference_id: str,
    query: str = "",
    year: int | None = None,
    limit: int = 20,
    cursor: str = "",
) -> dict[str, Any]:
    offset = max(0, int(cursor or "0"))
    limit = max(1, min(50, limit))
    stmt = select(Paper).where(Paper.conference_id == conference_id)
    if year is not None:
        stmt = stmt.where(Paper.year == year)
    clean_query = query.strip()
    if clean_query:
        like = f"%{clean_query}%"
        stmt = stmt.where(or_(Paper.title.ilike(like), Paper.paper_id.ilike(like), Paper.openreview_forum_id.ilike(like)))
    stmt = stmt.order_by(Paper.year.desc(), Paper.title.asc()).offset(offset).limit(limit + 1)
    papers = list(session.execute(stmt).scalars())
    items = [paper_to_public_dict(paper) for paper in papers[:limit]]
    return {
        "items": items,
        "next_cursor": str(offset + limit) if len(papers) > limit else None,
    }


def vote_counts_by_reviewer(session: Session, paper_id: str) -> dict[str, dict[str, int]]:
    rows = session.execute(
        select(Vote.reviewer_key, Vote.vote, func.count(Vote.id))
        .where(Vote.paper_id == paper_id)
        .group_by(Vote.reviewer_key, Vote.vote)
    ).all()
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for reviewer_key, vote, count in rows:
        if vote in {"up", "down"}:
            counts[str(reviewer_key)][str(vote)] = int(count)
    return counts


def apply_vote_counts(session: Session, paper_id: str, public_json: dict[str, Any]) -> dict[str, Any]:
    scorecard = copy.deepcopy(public_json)
    counts = vote_counts_by_reviewer(session, paper_id)
    for reviewer in scorecard.get("reviewers", []):
        if not isinstance(reviewer, dict):
            continue
        reviewer_key = str(reviewer.get("reviewer_key", ""))
        reviewer["social"] = {
            "up": counts[reviewer_key]["up"],
            "down": counts[reviewer_key]["down"],
        }
    scorecard["leaderboards"] = leaderboard_keys_from_public(scorecard)
    return scorecard


def leaderboard_keys_from_public(public_json: dict[str, Any]) -> dict[str, list[str]]:
    reviewers = [item for item in public_json.get("reviewers", []) if isinstance(item, dict)]
    red = sorted(reviewers, key=lambda item: (-int(item.get("score") or 0), str(item.get("reviewer_key") or "")))
    black = sorted(reviewers, key=lambda item: (int(item.get("score") or 0), str(item.get("reviewer_key") or "")))
    return {
        "red": [str(item.get("reviewer_key", "")) for item in red[:10]],
        "black": [str(item.get("reviewer_key", "")) for item in black[:10]],
    }


def upsert_vote(session: Session, *, paper_id: str, reviewer_key: str, session_id: str, vote: str) -> dict[str, Any]:
    if vote not in {"up", "down", "none"}:
        raise ValueError("vote must be one of: up, down, none")
    existing = session.execute(
        select(Vote).where(
            Vote.paper_id == paper_id,
            Vote.reviewer_key == reviewer_key,
            Vote.session_id == session_id,
        )
    ).scalar_one_or_none()
    if vote == "none":
        if existing is not None:
            session.delete(existing)
            session.flush()
        return {"paper_id": paper_id, "reviewer_key": reviewer_key, "selected": None}
    if existing is None:
        existing = Vote(paper_id=paper_id, reviewer_key=reviewer_key, session_id=session_id, vote=vote)
        session.add(existing)
    else:
        existing.vote = vote
        existing.updated_at = utcnow()
    session.flush()
    return {"paper_id": paper_id, "reviewer_key": reviewer_key, "selected": vote}


def build_leaderboards(
    session: Session,
    *,
    conference_id: str | None = None,
    year: int | None = None,
    limit: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    limit = max(1, min(50, limit))
    stmt = select(ReviewerScore, Paper.title).join(Paper, Paper.paper_id == ReviewerScore.paper_id)
    if conference_id:
        stmt = stmt.where(ReviewerScore.conference_id == conference_id)
    if year is not None:
        stmt = stmt.where(ReviewerScore.year == year)
    rows = session.execute(stmt).all()
    counts_by_paper: dict[str, dict[str, dict[str, int]]] = {}
    items = []
    for score, title in rows:
        if score.paper_id not in counts_by_paper:
            counts_by_paper[score.paper_id] = vote_counts_by_reviewer(session, score.paper_id)
        extra = counts_by_paper[score.paper_id][score.reviewer_key]
        up = extra["up"]
        down = extra["down"]
        items.append(
            {
                "paper_id": score.paper_id,
                "paper_title": title,
                "reviewer_key": score.reviewer_key,
                "nickname": score.nickname,
                "avatar_key": score.avatar_key,
                "score": score.score,
                "up": up,
                "down": down,
            }
        )
    red = sorted(items, key=lambda item: (-item["score"], item["reviewer_key"]))[:limit]
    black = sorted(items, key=lambda item: (item["score"], item["reviewer_key"]))[:limit]
    return {"red": red, "black": black}


def register_memory_index(
    session: Session,
    *,
    version: str,
    path: str,
    record_count: int,
    dimensions: dict[str, Any],
    active: bool = True,
) -> MemoryIndex:
    index = session.get(MemoryIndex, version)
    if index is None:
        index = MemoryIndex(version=version, path=path, record_count=record_count, dimensions_json=dimensions, active=active)
        session.add(index)
    else:
        index.path = path
        index.record_count = record_count
        index.dimensions_json = dimensions
        index.active = active
    session.flush()
    return index



def _filtered_papers(
    session: Session,
    *,
    conference_id: str | None,
    year: int | None,
    paper_ids: list[str] | None,
) -> list[Paper]:
    stmt = select(Paper)
    if conference_id:
        stmt = stmt.where(Paper.conference_id == conference_id)
    if year is not None:
        stmt = stmt.where(Paper.year == year)
    if paper_ids:
        stmt = stmt.where(Paper.paper_id.in_(paper_ids))
    return list(session.execute(stmt.order_by(Paper.year.desc(), Paper.title.asc())).scalars())


def _has_scorecard_for_version(
    session: Session,
    paper_id: str,
    *,
    scorer_version: str,
    memory_index_version: str,
) -> bool:
    return (
        session.execute(
            select(Scorecard.scorecard_id)
            .where(
                Scorecard.paper_id == paper_id,
                Scorecard.scorer_version == scorer_version,
                Scorecard.memory_index_version == memory_index_version,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _has_active_scoring_job(
    session: Session,
    paper_id: str,
    *,
    scorer_version: str,
    memory_index_version: str,
) -> bool:
    return (
        session.execute(
            select(ScoringJob.job_id)
            .where(
                ScoringJob.paper_id == paper_id,
                ScoringJob.status.in_(["queued", "running"]),
                ScoringJob.scorer_version == scorer_version,
                ScoringJob.memory_index_version == memory_index_version,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )
