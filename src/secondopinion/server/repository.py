from __future__ import annotations

import copy
import datetime as dt
import hashlib
import hmac
import math
import re
import secrets
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
    ReviewerComment,
    ReviewerScore,
    SavedPaper,
    Scorecard,
    ScoringJob,
    UserAccount,
    UserSession,
    VenueSubscription,
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
        stmt = stmt.where(or_(Paper.conference_id == conference_id, Paper.venue == conference_id))
    if year is not None:
        stmt = stmt.where(Paper.year == year)
    if conference_id:
        rows = session.execute(stmt.order_by(Scorecard.created_at.desc()).limit(limit)).all()
    else:
        venue_stmt = select(Paper.venue).join(Scorecard, Scorecard.paper_id == Paper.paper_id)
        if year is not None:
            venue_stmt = venue_stmt.where(Paper.year == year)
        venues = [
            str(venue)
            for venue in session.execute(venue_stmt.group_by(Paper.venue).order_by(Paper.venue)).scalars()
            if venue
        ]
        per_venue_limit = max(2, math.ceil(limit / max(1, min(len(venues), limit))))
        rows = []
        for venue in venues:
            rows.extend(
                session.execute(
                    stmt.where(Paper.venue == venue).order_by(Scorecard.created_at.desc()).limit(per_venue_limit)
                ).all()
            )
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
                "signal_label": str(summary.get("signal_label") or "Review"),
                "comment_count": int(summary.get("comment_count") or 0),
                "topic_count": int(summary.get("topic_count") or 0),
                "topics": [item for item in topic_labels if item][:3],
                "social": votes_by_paper[paper.paper_id],
                "vote_total": votes_by_paper[paper.paper_id]["up"] + votes_by_paper[paper.paper_id]["down"],
                "created_at": scorecard.created_at.isoformat() if scorecard.created_at else "",
            }
        )
    return _venue_balanced(items, limit=limit) if not conference_id else items[:limit]


def search_papers(
    session: Session,
    *,
    conference_id: str | None = None,
    query: str = "",
    year: int | None = None,
    limit: int = 20,
    cursor: str = "",
) -> dict[str, Any]:
    offset = max(0, int(cursor or "0"))
    limit = max(1, min(50, limit))
    stmt = select(Paper)
    if conference_id:
        stmt = stmt.where(or_(Paper.conference_id == conference_id, Paper.venue == conference_id))
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
    overall = sorted(reviewers, key=lambda item: (-_public_dimension_score(item, "outrage"), str(item.get("reviewer_key") or "")))
    toxic = sorted(reviewers, key=lambda item: (-_public_dimension_score(item, "toxicity"), str(item.get("reviewer_key") or "")))
    helpful = sorted(reviewers, key=lambda item: (-_public_dimension_score(item, "helpfulness"), str(item.get("reviewer_key") or "")))
    return {
        "overall": [str(item.get("reviewer_key", "")) for item in overall[:10]],
        "toxic": [str(item.get("reviewer_key", "")) for item in toxic[:10]],
        "helpful": [str(item.get("reviewer_key", "")) for item in helpful[:10]],
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


HANDLE_RE = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
PASSWORD_ITERATIONS = 600_000


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def normalize_handle(handle: str) -> str:
    return (handle or "").strip().lower()


def make_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, digest = stored_hash.split("$", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate, digest)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def user_to_public_dict(user: UserAccount) -> dict[str, Any]:
    return {
        "user_id": user.user_id,
        "handle": user.handle,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


def create_user_account(session: Session, *, handle: str, email: str, password: str) -> UserAccount:
    clean_handle = normalize_handle(handle)
    clean_email = normalize_email(email)
    if not HANDLE_RE.match(clean_handle):
        raise ValueError("invalid_handle")
    if "@" not in clean_email or len(clean_email) > 240:
        raise ValueError("invalid_email")
    if len(password or "") < 8:
        raise ValueError("weak_password")
    existing = session.execute(
        select(UserAccount).where(or_(UserAccount.handle == clean_handle, UserAccount.email == clean_email))
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("user_exists")
    user = UserAccount(
        user_id=f"user_{uuid.uuid4().hex[:16]}",
        handle=clean_handle,
        email=clean_email,
        password_hash=make_password_hash(password),
    )
    session.add(user)
    session.flush()
    return user


def authenticate_user(session: Session, *, identity: str, password: str) -> UserAccount | None:
    clean_identity = (identity or "").strip()
    if not clean_identity or not password:
        return None
    lower_identity = clean_identity.lower()
    user = session.execute(
        select(UserAccount).where(or_(UserAccount.email == lower_identity, UserAccount.handle == clean_identity))
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    try:
        stored_iterations = int(user.password_hash.split("$", 3)[1])
    except (IndexError, ValueError):
        stored_iterations = 0
    if stored_iterations < PASSWORD_ITERATIONS:
        user.password_hash = make_password_hash(password)
    return user


def create_user_session(session: Session, *, user: UserAccount, session_id: str) -> tuple[str, UserSession]:
    token = secrets.token_urlsafe(32)
    row = UserSession(
        token_hash=token_digest(token),
        user_id=user.user_id,
        session_id=session_id,
    )
    session.add(row)
    session.flush()
    return token, row


def user_from_token(session: Session, token: str) -> UserAccount | None:
    if not token:
        return None
    row = session.get(UserSession, token_digest(token))
    if row is None:
        return None
    now = utcnow()
    last_seen = row.last_seen_at
    if last_seen and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=dt.timezone.utc)
    if last_seen and last_seen < now - dt.timedelta(days=30):
        session.delete(row)
        session.flush()
        return None
    row.last_seen_at = now
    return session.get(UserAccount, row.user_id)


def delete_user_account(session: Session, *, user_id: str) -> None:
    user = session.get(UserAccount, user_id)
    if user is None:
        return
    session_ids = list(
        session.execute(select(UserSession.session_id).where(UserSession.user_id == user_id)).scalars()
    )
    session.execute(delete(ReviewerComment).where(ReviewerComment.user_id == user_id))
    if session_ids:
        session.execute(delete(Vote).where(Vote.session_id.in_(session_ids)))
        session.execute(delete(ReviewerComment).where(ReviewerComment.session_id.in_(session_ids)))
    session.execute(delete(SavedPaper).where(SavedPaper.user_id == user_id))
    session.execute(delete(VenueSubscription).where(VenueSubscription.user_id == user_id))
    session.execute(delete(UserSession).where(UserSession.user_id == user_id))
    session.delete(user)
    session.flush()


def revoke_user_session(session: Session, token: str) -> None:
    if not token:
        return
    row = session.get(UserSession, token_digest(token))
    if row is not None:
        session.delete(row)
        session.flush()


def list_saved_papers(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.execute(
        select(SavedPaper, Paper)
        .join(Paper, Paper.paper_id == SavedPaper.paper_id)
        .where(SavedPaper.user_id == user_id)
        .order_by(SavedPaper.created_at.desc())
    ).all()
    return [{**paper_to_public_dict(paper), "saved_at": saved.created_at.isoformat()} for saved, paper in rows]


def save_paper_for_user(session: Session, *, user_id: str, paper_id: str) -> dict[str, Any]:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise ValueError("paper_not_found")
    existing = session.execute(
        select(SavedPaper).where(SavedPaper.user_id == user_id, SavedPaper.paper_id == paper_id)
    ).scalar_one_or_none()
    if existing is None:
        existing = SavedPaper(user_id=user_id, paper_id=paper_id)
        session.add(existing)
        session.flush()
    return {**paper_to_public_dict(paper), "saved_at": existing.created_at.isoformat()}


def remove_saved_paper(session: Session, *, user_id: str, paper_id: str) -> None:
    existing = session.execute(
        select(SavedPaper).where(SavedPaper.user_id == user_id, SavedPaper.paper_id == paper_id)
    ).scalar_one_or_none()
    if existing is not None:
        session.delete(existing)
        session.flush()


def list_venue_subscriptions(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.execute(
        select(VenueSubscription)
        .where(VenueSubscription.user_id == user_id)
        .order_by(VenueSubscription.year.desc(), VenueSubscription.venue.asc())
    ).scalars().all()
    return [
        {"venue": row.venue, "year": row.year, "subscribed_at": row.created_at.isoformat()}
        for row in rows
    ]


def subscribe_user_to_venue(session: Session, *, user_id: str, venue: str, year: int = 2025) -> dict[str, Any]:
    clean_venue = (venue or "").strip().upper()
    if not clean_venue:
        raise ValueError("invalid_venue")
    existing = session.execute(
        select(VenueSubscription).where(
            VenueSubscription.user_id == user_id,
            VenueSubscription.venue == clean_venue,
            VenueSubscription.year == year,
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = VenueSubscription(user_id=user_id, venue=clean_venue, year=year)
        session.add(existing)
        session.flush()
    return {"venue": existing.venue, "year": existing.year, "subscribed_at": existing.created_at.isoformat()}


def unsubscribe_user_from_venue(session: Session, *, user_id: str, venue: str, year: int = 2025) -> None:
    clean_venue = (venue or "").strip().upper()
    existing = session.execute(
        select(VenueSubscription).where(
            VenueSubscription.user_id == user_id,
            VenueSubscription.venue == clean_venue,
            VenueSubscription.year == year,
        )
    ).scalar_one_or_none()
    if existing is not None:
        session.delete(existing)
        session.flush()


COMMENT_MAX_LENGTH = 1000


def comment_author_handle(session_id: str) -> str:
    digest = hashlib.sha1(session_id.encode("utf-8")).hexdigest()[:6]
    return f"anon-{digest}"


def comment_to_public_dict(
    comment: ReviewerComment,
    *,
    user: UserAccount | None = None,
    viewer_session_id: str = "",
    viewer_user_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": comment.id,
        "body": comment.body,
        "author": user.handle if user else comment_author_handle(comment.session_id),
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "can_edit": bool(
            (viewer_user_id and comment.user_id and viewer_user_id == comment.user_id)
            or (viewer_session_id and viewer_session_id == comment.session_id)
        ),
    }


def _comment_user_map(session: Session, comments: list[ReviewerComment]) -> dict[str, UserAccount]:
    user_ids = sorted({str(comment.user_id) for comment in comments if comment.user_id})
    if not user_ids:
        return {}
    rows = session.execute(select(UserAccount).where(UserAccount.user_id.in_(user_ids))).scalars().all()
    return {user.user_id: user for user in rows}


def list_reviewer_comments(
    session: Session,
    paper_id: str,
    reviewer_key: str,
    *,
    viewer_session_id: str = "",
    viewer_user_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = session.execute(
        select(ReviewerComment)
        .where(ReviewerComment.paper_id == paper_id, ReviewerComment.reviewer_key == reviewer_key)
        .order_by(ReviewerComment.created_at.desc(), ReviewerComment.id.desc())
    ).scalars().all()
    users = _comment_user_map(session, rows)
    return [
        comment_to_public_dict(
            row,
            user=users.get(str(row.user_id or "")),
            viewer_session_id=viewer_session_id,
            viewer_user_id=viewer_user_id,
        )
        for row in rows
    ]


def comments_by_reviewer(
    session: Session,
    paper_id: str,
    *,
    viewer_session_id: str = "",
    viewer_user_id: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    rows = session.execute(
        select(ReviewerComment)
        .where(ReviewerComment.paper_id == paper_id)
        .order_by(ReviewerComment.created_at.desc(), ReviewerComment.id.desc())
    ).scalars().all()
    users = _comment_user_map(session, rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.reviewer_key)].append(
            comment_to_public_dict(
                row,
                user=users.get(str(row.user_id or "")),
                viewer_session_id=viewer_session_id,
                viewer_user_id=viewer_user_id,
            )
        )
    return grouped


COMMENT_PREVIEW_LIMIT = 2


def comment_previews_by_reviewer(
    session: Session,
    paper_id: str,
    *,
    limit: int = COMMENT_PREVIEW_LIMIT,
) -> dict[str, dict[str, Any]]:
    """Total count plus the newest public comments for each reviewer on a paper.

    Returns ``reviewer_key -> {"count": int, "items": [<=limit newest public dicts]}``.
    Previews are display-only, so they carry no viewer edit context. Used to embed a
    few community comments directly in leaderboard rows and spare the client a
    per-row round trip.
    """
    rows = session.execute(
        select(ReviewerComment)
        .where(ReviewerComment.paper_id == paper_id)
        .order_by(ReviewerComment.created_at.desc(), ReviewerComment.id.desc())
    ).scalars().all()
    users = _comment_user_map(session, rows)
    grouped: dict[str, dict[str, Any]] = {}
    keep = max(0, limit)
    for row in rows:
        bucket = grouped.setdefault(str(row.reviewer_key), {"count": 0, "items": []})
        bucket["count"] += 1
        if len(bucket["items"]) < keep:
            bucket["items"].append(comment_to_public_dict(row, user=users.get(str(row.user_id or ""))))
    return grouped


def apply_reviewer_comments(
    session: Session,
    paper_id: str,
    public_json: dict[str, Any],
    *,
    viewer_session_id: str = "",
    viewer_user_id: str | None = None,
) -> dict[str, Any]:
    scorecard = copy.deepcopy(public_json)
    grouped = comments_by_reviewer(
        session,
        paper_id,
        viewer_session_id=viewer_session_id,
        viewer_user_id=viewer_user_id,
    )
    for reviewer in scorecard.get("reviewers", []):
        if not isinstance(reviewer, dict):
            continue
        reviewer_key = str(reviewer.get("reviewer_key", ""))
        items = grouped.get(reviewer_key, [])
        reviewer["comments"] = items
        reviewer["comment_count"] = len(items)
    return scorecard


def add_reviewer_comment(
    session: Session,
    *,
    paper_id: str,
    reviewer_key: str,
    session_id: str,
    body: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    text = (body or "").strip()
    if not text:
        raise ValueError("comment_empty")
    comment = ReviewerComment(
        paper_id=paper_id,
        reviewer_key=reviewer_key,
        session_id=session_id,
        user_id=user_id,
        body=text[:COMMENT_MAX_LENGTH],
    )
    session.add(comment)
    session.flush()
    user = session.get(UserAccount, user_id) if user_id else None
    return comment_to_public_dict(comment, user=user, viewer_session_id=session_id, viewer_user_id=user_id)


def _owns_comment(comment: ReviewerComment, *, session_id: str, user_id: str | None) -> bool:
    if user_id and comment.user_id and user_id == comment.user_id:
        return True
    return bool(session_id and comment.session_id == session_id)


def update_reviewer_comment(
    session: Session,
    *,
    comment_id: int,
    session_id: str,
    user_id: str | None,
    body: str,
) -> dict[str, Any]:
    comment = session.get(ReviewerComment, comment_id)
    if comment is None:
        raise ValueError("comment_not_found")
    if not _owns_comment(comment, session_id=session_id, user_id=user_id):
        raise PermissionError("comment_forbidden")
    text = (body or "").strip()
    if not text:
        raise ValueError("comment_empty")
    comment.body = text[:COMMENT_MAX_LENGTH]
    session.flush()
    user = session.get(UserAccount, comment.user_id) if comment.user_id else None
    return comment_to_public_dict(comment, user=user, viewer_session_id=session_id, viewer_user_id=user_id)


def delete_reviewer_comment(session: Session, *, comment_id: int, session_id: str, user_id: str | None) -> None:
    comment = session.get(ReviewerComment, comment_id)
    if comment is None:
        raise ValueError("comment_not_found")
    if not _owns_comment(comment, session_id=session_id, user_id=user_id):
        raise PermissionError("comment_forbidden")
    session.delete(comment)
    session.flush()

def _venue_balanced(items: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    venues: list[str] = []
    for item in items:
        venue = str(item.get("venue") or item.get("conference_id") or "")
        if venue and venue not in buckets:
            venues.append(venue)
        buckets[venue].append(item)
    if len(venues) <= 1:
        return items[:limit]

    max_per_venue = max(2, math.ceil(limit / min(len(venues), limit)))
    selected: list[dict[str, Any]] = []
    used: set[tuple[str, str]] = set()
    for index in range(max(len(bucket) for bucket in buckets.values())):
        for venue in venues:
            bucket = buckets[venue]
            if index >= len(bucket):
                continue
            item = bucket[index]
            key = (str(item.get("paper_id") or ""), str(item.get("reviewer_key") or item.get("created_at") or len(used)))
            if key in used:
                continue
            if sum(1 for selected_item in selected if str(selected_item.get("venue") or selected_item.get("conference_id") or "") == venue) >= max_per_venue:
                continue
            selected.append(item)
            used.add(key)
            if len(selected) >= limit:
                return selected
    for item in items:
        key = (str(item.get("paper_id") or ""), str(item.get("reviewer_key") or item.get("created_at") or len(used)))
        if key in used:
            continue
        selected.append(item)
        used.add(key)
        if len(selected) >= limit:
            break
    return selected

def build_leaderboards(
    session: Session,
    *,
    conference_id: str | None = None,
    year: int | None = None,
    limit: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    limit = max(1, min(50, limit))
    vote_counts = _vote_counts_for_leaderboard(session, conference_id=conference_id, year=year)
    comment_previews: dict[str, dict[str, dict[str, Any]]] = {}
    balance = conference_id is None

    def candidates(metric: str, *, ascending: bool = False) -> list[dict[str, Any]]:
        rows = _leaderboard_candidate_rows(
            session,
            conference_id=conference_id,
            year=year,
            metric=metric,
            ascending=ascending,
            limit=limit,
            balance=balance,
        )
        items = []
        for paper_id, reviewer_key, nickname, avatar_key, score_value, dimensions_json, title, venue, paper_year in rows:
            paper_key = str(paper_id)
            reviewer_key_text = str(reviewer_key)
            extra = vote_counts[(paper_key, reviewer_key_text)]
            if paper_key not in comment_previews:
                comment_previews[paper_key] = comment_previews_by_reviewer(session, paper_key)
            comment_bucket = comment_previews[paper_key].get(reviewer_key_text) or {}
            metrics = _reviewer_score_metrics_from_values(score_value, dimensions_json)
            item = {
                "paper_id": paper_id,
                "paper_title": title,
                "venue": venue,
                "year": paper_year,
                "reviewer_key": reviewer_key,
                "nickname": nickname,
                "avatar_key": avatar_key,
                "score": score_value,
                "attention": metrics["attention"],
                "outrage": metrics["outrage"],
                "toxicity": metrics["toxicity"],
                "helpfulness": metrics["helpfulness"],
                "quote": metrics["quote"],
                "verdict": metrics["verdict"],
                "up": extra["up"],
                "down": extra["down"],
                "comment_count": int(comment_bucket.get("count", 0)),
                "latest_comments": list(comment_bucket.get("items", [])),
            }
            if _leaderboard_display_eligible(item, metric=metric):
                items.append(item)
        if balance:
            return _venue_balanced(items, limit=limit)
        return items[:limit]

    return {
        "overall": candidates("attention"),
        "toxic": candidates("toxicity"),
        "helpful": candidates("helpfulness"),
        "red": candidates("score"),
        "black": candidates("score", ascending=True),
    }


def _leaderboard_candidate_rows(
    session: Session,
    *,
    conference_id: str | None,
    year: int | None,
    metric: str,
    ascending: bool,
    limit: int,
    balance: bool,
) -> list[Any]:
    candidate_limit = max(limit * 8, 80)
    stmt = (
        select(
            ReviewerScore.paper_id,
            ReviewerScore.reviewer_key,
            ReviewerScore.nickname,
            ReviewerScore.avatar_key,
            ReviewerScore.score,
            ReviewerScore.dimensions_json,
            Paper.title,
            Paper.venue,
            Paper.year,
        )
        .join(Paper, Paper.paper_id == ReviewerScore.paper_id)
    )
    if conference_id:
        stmt = stmt.where(ReviewerScore.conference_id == conference_id)
    if year is not None:
        stmt = stmt.where(ReviewerScore.year == year)
    rows = list(session.execute(stmt).all())

    def metric_value(row: Any) -> float:
        metrics = _reviewer_score_metrics_from_values(row[4], row[5])
        if metric == "toxicity":
            return float(metrics["toxicity"])
        if metric == "helpfulness":
            return float(metrics["helpfulness"])
        if metric == "outrage":
            return float(metrics["outrage"])
        if metric == "attention":
            return float(metrics["attention"])
        return float(row[4] or 0)

    sorted_rows = sorted(rows, key=lambda row: (metric_value(row), str(row[1] or "")), reverse=not ascending)
    if not balance:
        return sorted_rows[:candidate_limit]

    venue_rows: dict[str, list[Any]] = defaultdict(list)
    for row in sorted_rows:
        venue_rows[str(row[7] or "")].append(row)
    per_venue = max(limit * 4, 40)
    balanced: list[Any] = []
    for venue in sorted(venue_rows):
        balanced.extend(venue_rows[venue][:per_venue])
    return balanced

_LEADERBOARD_NOISE_PHRASES = (
    "author-reviewer discussion",
    "we are currently in the author",
    "dear authors",
    "thank you for your helpful",
    "thank you again for your helpful",
    "thank you for trying",
    "we are delighted",
    "our responses",
    "updating the manuscript",
    "we will definitely",
    "we will update",
    "final state of the manuscript",
    "updating updating",
    "my concern has been addressed",
    "we sincerely thank",
    "thank you for the comments",
    "thank you for your comments",
)

_HELPFULNESS_CONTRADICTION_PHRASES = (
    "not informative",
    "non-informative",
    "insufficient review",
    "no substantive",
    "not a substantive",
    "no actionable",
    "unhelpful",
    "low usefulness",
    "mostly summary",
    "uninformative summary",
    "too summary-like",
    "too vague",
)


_REVIEWER_RECUSAL_PHRASES = (
    "find another reviewer and disregard",
    "disregard my comments",
    "disregard my review",
    "unable to provide a meaningful review",
    "cannot provide a meaningful review",
    "outside my expertise",
    "out of my expertise",
)

def _leaderboard_display_eligible(item: dict[str, Any], *, metric: str = "") -> bool:
    text = " ".join(str(item.get(key) or "") for key in ("quote", "verdict")).lower()
    if not text.strip():
        return False
    if any(phrase in text for phrase in _LEADERBOARD_NOISE_PHRASES):
        return False
    if any(phrase in text for phrase in _REVIEWER_RECUSAL_PHRASES):
        return False
    if metric == "helpfulness":
        if int(item.get("helpfulness") or 0) < 55 or int(item.get("toxicity") or 0) > 35:
            return False
        if any(phrase in text for phrase in _HELPFULNESS_CONTRADICTION_PHRASES):
            return False
    return True


def _vote_counts_for_leaderboard(
    session: Session,
    *,
    conference_id: str | None = None,
    year: int | None = None,
) -> dict[tuple[str, str], dict[str, int]]:
    stmt = select(Vote.paper_id, Vote.reviewer_key, Vote.vote, func.count(Vote.id)).join(Paper, Paper.paper_id == Vote.paper_id)
    if conference_id:
        stmt = stmt.where(Paper.venue == conference_id)
    if year is not None:
        stmt = stmt.where(Paper.year == year)
    rows = session.execute(stmt.group_by(Vote.paper_id, Vote.reviewer_key, Vote.vote)).all()
    counts: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for paper_id, reviewer_key, vote, count in rows:
        if vote in {"up", "down"}:
            counts[(str(paper_id), str(reviewer_key))][str(vote)] = int(count)
    return counts


def home_stats(
    session: Session,
    *,
    conference_id: str | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    paper_stmt = select(func.count(Paper.paper_id))
    review_stmt = select(func.count(Review.review_id)).join(Paper, Paper.paper_id == Review.paper_id)
    score_stmt = select(func.count(ReviewerScore.reviewer_key))
    if conference_id:
        paper_stmt = paper_stmt.where(Paper.venue == conference_id)
        review_stmt = review_stmt.where(Paper.venue == conference_id)
        score_stmt = score_stmt.where(ReviewerScore.conference_id == conference_id)
    if year is not None:
        paper_stmt = paper_stmt.where(Paper.year == year)
        review_stmt = review_stmt.where(Paper.year == year)
        score_stmt = score_stmt.where(ReviewerScore.year == year)
    paper_count = int(session.execute(paper_stmt).scalar() or 0)
    review_count = int(session.execute(review_stmt).scalar() or 0)
    scored_review_count = int(session.execute(score_stmt).scalar() or 0)
    return {
        "paper_count": paper_count,
        "review_count": review_count,
        "scored_review_count": scored_review_count,
        "audited_count": scored_review_count or review_count,
    }


def _reviewer_score_metrics(score: ReviewerScore) -> dict[str, Any]:
    return _reviewer_score_metrics_from_values(score.score, score.dimensions_json)


def _reviewer_score_metrics_from_values(score_value: Any, dimensions_json: list[dict[str, Any]] | None) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "outrage": 0,
        "toxicity": 0,
        "helpfulness": int(score_value or 0),
        "quote": "",
        "verdict": "",
    }
    for item in dimensions_json or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        if key in {"outrage", "toxicity", "helpfulness"}:
            metrics[key] = _clamp_int(item.get("score"))
        if not metrics["quote"] and item.get("quote"):
            metrics["quote"] = str(item.get("quote") or "")
        if not metrics["verdict"] and item.get("verdict"):
            metrics["verdict"] = str(item.get("verdict") or "")
    metrics["attention"] = _clamp_int(
        0.75 * metrics["outrage"]
        + 0.15 * (100 - metrics["helpfulness"])
        + 0.10 * metrics["toxicity"]
    )
    return metrics


def _public_dimension_score(reviewer: dict[str, Any], key: str) -> int:
    for item in reviewer.get("dimensions") or []:
        if isinstance(item, dict) and item.get("key") == key:
            return _clamp_int(item.get("score"))
    return _clamp_int(reviewer.get("score")) if key == "helpfulness" else 0


def _clamp_int(value: Any) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, number))

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
