from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from .config import ServerSettings, settings_from_env
from .database import init_db, make_engine, make_session_factory
from .models import Paper, ReviewerComment, ScoringJob, Vote, utcnow
from .repository import (
    add_reviewer_comment,
    apply_reviewer_comments,
    apply_vote_counts,
    build_leaderboards,
    create_scoring_job,
    home_stats,
    job_to_public_dict,
    latest_scorecard,
    latest_scored_papers,
    list_conferences,
    list_reviewer_comments,
    paper_to_public_dict,
    search_papers,
    upsert_vote,
)


SESSION_COOKIE = "so_session"


def create_app(
    *,
    settings: ServerSettings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    settings = settings or settings_from_env()
    if session_factory is None:
        engine = make_engine(settings.database_url)
        if os.environ.get("SECONDOPINION_AUTO_INIT_DB", "1") == "1":
            init_db(engine)
        session_factory = make_session_factory(engine)

    app = FastAPI(title="SecondOpinion API", version="0.1.0")
    origins = list(settings.cors_origins) or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(settings.cors_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.session_factory = session_factory

    def get_session() -> Session:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "secondopinion-api"}

    @app.get("/api/home")
    def home(
        conference: str | None = None,
        year: int | None = 2025,
        limit: int = 12,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        static_payload = load_static_home_payload(
            conference=conference,
            year=year,
            limit=limit,
            home_snapshot_path=settings.home_snapshot_path,
        )
        if static_payload is not None:
            return static_payload
        stats = home_stats(session, conference_id=conference, year=year)
        return {
            "latest_papers": latest_scored_papers(session, conference_id=conference, year=year, limit=limit),
            "leaderboards": build_leaderboards(session, conference_id=conference, year=year, limit=20),
            "stats": stats,
            "audited_count": stats["audited_count"],
            "paper_count": stats["paper_count"],
            "review_count": stats["review_count"],
        }

    @app.get("/api/conferences")
    def conferences(session: Session = Depends(get_session)) -> dict[str, Any]:
        return {"items": list_conferences(session)}

    @app.get("/api/conferences/{conference_id}/papers")
    def papers(
        conference_id: str,
        query: str = "",
        year: int | None = None,
        cursor: str = "",
        limit: int = 20,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        return search_papers(session, conference_id=conference_id, query=query, year=year, cursor=cursor, limit=limit)

    @app.get("/api/papers")
    def papers_global(
        query: str = "",
        conference: str | None = None,
        year: int | None = 2025,
        cursor: str = "",
        limit: int = 20,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        return search_papers(session, conference_id=conference, query=query, year=year, cursor=cursor, limit=limit)

    @app.get("/api/papers/{paper_id}")
    def paper_detail(paper_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail={"code": "paper_not_found"})
        return paper_to_public_dict(paper)

    @app.get("/api/papers/{paper_id}/scorecard")
    def paper_scorecard(paper_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
        if session.get(Paper, paper_id) is None:
            raise HTTPException(status_code=404, detail={"code": "paper_not_found"})
        scorecard = latest_scorecard(session, paper_id)
        if scorecard is None:
            raise HTTPException(status_code=404, detail={"code": "scorecard_not_ready"})
        payload = apply_reviewer_comments(
            session, paper_id, apply_vote_counts(session, paper_id, scorecard.public_json)
        )
        payload.setdefault("paper", {})["paper_id"] = paper_id
        return payload

    @app.post("/api/papers/{paper_id}/scoring-jobs")
    def create_job(
        paper_id: str,
        request: Request,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail={"code": "paper_not_found"})
        job = create_scoring_job(
            session,
            paper_id=paper_id,
            requested_by_session=session_id_from_request(request),
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )
        return job_to_public_dict(job)

    @app.get("/api/scoring-jobs/{job_id}")
    def scoring_job(job_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
        job = session.get(ScoringJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail={"code": "job_not_found"})
        return job_to_public_dict(job)

    @app.post("/api/papers/{paper_id}/reviewers/{reviewer_key}/votes")
    async def reviewer_vote(
        paper_id: str,
        reviewer_key: str,
        request: Request,
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail={"code": "paper_not_found"})
        body = await parse_json_body(request)
        session_id = session_id_from_request(request)
        selected = str(body.get("vote") or "none")
        if selected in {"up", "down"}:
            enforce_vote_rate_limit(session, session_id)
        result = upsert_vote(
            session,
            paper_id=paper_id,
            reviewer_key=reviewer_key,
            session_id=session_id,
            vote=selected,
        )
        scorecard = latest_scorecard(session, paper_id)
        result["scorecard"] = (
            apply_reviewer_comments(session, paper_id, apply_vote_counts(session, paper_id, scorecard.public_json))
            if scorecard
            else None
        )
        if result["scorecard"]:
            result["scorecard"].setdefault("paper", {})["paper_id"] = paper_id
        response = JSONResponse(result)
        response.set_cookie(
            SESSION_COOKIE,
            session_id,
            max_age=60 * 60 * 24 * 365,
            httponly=False,
            samesite="lax",
        )
        return response

    @app.get("/api/papers/{paper_id}/reviewers/{reviewer_key}/comments")
    def reviewer_comments(
        paper_id: str,
        reviewer_key: str,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        return {"items": list_reviewer_comments(session, paper_id, reviewer_key)}

    @app.post("/api/papers/{paper_id}/reviewers/{reviewer_key}/comments")
    async def create_reviewer_comment(
        paper_id: str,
        reviewer_key: str,
        request: Request,
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail={"code": "paper_not_found"})
        body = await parse_json_body(request)
        session_id = session_id_from_request(request)
        enforce_comment_rate_limit(session, session_id)
        try:
            comment = add_reviewer_comment(
                session,
                paper_id=paper_id,
                reviewer_key=reviewer_key,
                session_id=session_id,
                body=str(body.get("body") or body.get("text") or ""),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail={"code": "comment_empty"})
        result = {
            "comment": comment,
            "items": list_reviewer_comments(session, paper_id, reviewer_key),
        }
        response = JSONResponse(result)
        response.set_cookie(
            SESSION_COOKIE,
            session_id,
            max_age=60 * 60 * 24 * 365,
            httponly=False,
            samesite="lax",
        )
        return response

    @app.get("/api/leaderboards")
    def leaderboards(
        conference: str | None = None,
        year: int | None = None,
        limit: int = 10,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        return build_leaderboards(session, conference_id=conference, year=year, limit=limit)

    return app


def load_static_home_payload(
    *,
    conference: str | None,
    year: int | None,
    limit: int,
    home_snapshot_path: Path,
) -> dict[str, Any] | None:
    if conference or year != 2025:
        return None
    path = home_snapshot_path
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    capped_limit = max(1, min(50, int(limit or 12)))
    latest = payload.get("latest_papers")
    if isinstance(latest, list):
        payload = dict(payload)
        payload["latest_papers"] = latest[:capped_limit]
    payload.setdefault("source", "static_home_2025")
    return payload


async def parse_json_body(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def session_id_from_request(request: Request) -> str:
    existing = request.cookies.get(SESSION_COOKIE)
    return existing or f"session_{uuid.uuid4().hex}"


VOTE_RATE_LIMIT = 60
VOTE_RATE_WINDOW = dt.timedelta(hours=1)


def enforce_vote_rate_limit(session: Session, session_id: str) -> None:
    window_start = utcnow() - VOTE_RATE_WINDOW
    recent_votes = session.execute(
        select(func.count(Vote.id)).where(
            Vote.session_id == session_id,
            Vote.updated_at >= window_start,
        )
    ).scalar_one()
    if int(recent_votes or 0) >= VOTE_RATE_LIMIT:
        raise HTTPException(status_code=429, detail={"code": "vote_rate_limited"})


COMMENT_RATE_LIMIT = 20
COMMENT_RATE_WINDOW = dt.timedelta(hours=1)


def enforce_comment_rate_limit(session: Session, session_id: str) -> None:
    window_start = utcnow() - COMMENT_RATE_WINDOW
    recent_comments = session.execute(
        select(func.count(ReviewerComment.id)).where(
            ReviewerComment.session_id == session_id,
            ReviewerComment.created_at >= window_start,
        )
    ).scalar_one()
    if int(recent_comments or 0) >= COMMENT_RATE_LIMIT:
        raise HTTPException(status_code=429, detail={"code": "comment_rate_limited"})


app = create_app()

