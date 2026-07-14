from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from .config import ServerSettings, settings_from_env
from .database import init_db, make_engine, make_session_factory
from .models import Paper, ReviewerComment, ScoringJob, UserAccount, Vote, utcnow
from .repository import (
    add_reviewer_comment,
    apply_reviewer_comments,
    apply_vote_counts,
    authenticate_user,
    build_leaderboards,
    create_scoring_job,
    create_user_account,
    create_user_session,
    home_stats,
    job_to_public_dict,
    latest_scorecard,
    latest_scored_papers,
    list_conferences,
    list_reviewer_comments,
    list_saved_papers,
    list_venue_subscriptions,
    paper_to_public_dict,
    remove_saved_paper,
    revoke_user_session,
    save_paper_for_user,
    search_papers,
    subscribe_user_to_venue,
    unsubscribe_user_from_venue,
    update_reviewer_comment,
    delete_reviewer_comment,
    delete_user_account,
    upsert_vote,
    user_from_token,
    user_to_public_dict,
)


SESSION_COOKIE = "so_session"
USER_TOKEN_COOKIE = "so_user_token"


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
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.session_factory = session_factory
    auth_attempts: dict[str, deque[dt.datetime]] = defaultdict(deque)

    def enforce_auth_rate_limit(request: Request) -> None:
        peer = request.client.host if request.client else "unknown"
        forwarded = (request.headers.get("x-real-ip") or "").strip()
        client_ip = forwarded[:80] if forwarded and peer in {"127.0.0.1", "::1", "testclient"} else peer[:80]
        now = utcnow()
        cutoff = now - dt.timedelta(minutes=15)
        bucket = auth_attempts[client_ip]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= 10:
            raise HTTPException(status_code=429, detail={"code": "auth_rate_limited"})
        bucket.append(now)

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

    @app.get("/api/me")
    def me(request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
        user = current_user_from_request(session, request)
        return me_payload(session, user)

    @app.post("/api/auth/register")
    async def register(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
        enforce_auth_rate_limit(request)
        body = await parse_json_body(request)
        try:
            user = create_user_account(
                session,
                handle=str(body.get("handle") or ""),
                email=str(body.get("email") or ""),
                password=str(body.get("password") or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": str(exc)})
        token, _ = create_user_session(session, user=user, session_id=session_id_from_request(request))
        return auth_response(session, user, token)

    @app.post("/api/auth/login")
    async def login(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
        enforce_auth_rate_limit(request)
        body = await parse_json_body(request)
        user = authenticate_user(
            session,
            identity=str(body.get("identity") or body.get("email") or body.get("handle") or ""),
            password=str(body.get("password") or ""),
        )
        if user is None:
            raise HTTPException(status_code=401, detail={"code": "invalid_credentials"})
        token, _ = create_user_session(session, user=user, session_id=session_id_from_request(request))
        return auth_response(session, user, token)

    @app.post("/api/auth/logout")
    def logout(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
        revoke_user_session(session, auth_token_from_request(request))
        response = JSONResponse({"ok": True})
        response.delete_cookie(USER_TOKEN_COOKIE)
        return response

    @app.delete("/api/auth/account")
    def delete_account(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
        user = require_user(session, request)
        delete_user_account(session, user_id=user.user_id)
        response = JSONResponse({"ok": True})
        response.delete_cookie(USER_TOKEN_COOKIE)
        return response

    @app.post("/api/me/saved-papers/{paper_id}")
    def save_paper(paper_id: str, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
        user = require_user(session, request)
        try:
            item = save_paper_for_user(session, user_id=user.user_id, paper_id=paper_id)
        except ValueError:
            raise HTTPException(status_code=404, detail={"code": "paper_not_found"})
        return {"item": item, **me_payload(session, user)}

    @app.delete("/api/me/saved-papers/{paper_id}")
    def unsave_paper(paper_id: str, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
        user = require_user(session, request)
        remove_saved_paper(session, user_id=user.user_id, paper_id=paper_id)
        return me_payload(session, user)

    @app.post("/api/me/venue-subscriptions/{venue}")
    async def subscribe_venue(venue: str, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
        user = require_user(session, request)
        body = await parse_json_body(request)
        try:
            item = subscribe_user_to_venue(session, user_id=user.user_id, venue=venue, year=int(body.get("year") or 2025))
        except ValueError:
            raise HTTPException(status_code=400, detail={"code": "invalid_venue"})
        return {"item": item, **me_payload(session, user)}

    @app.delete("/api/me/venue-subscriptions/{venue}")
    def unsubscribe_venue(venue: str, request: Request, year: int = 2025, session: Session = Depends(get_session)) -> dict[str, Any]:
        user = require_user(session, request)
        unsubscribe_user_from_venue(session, user_id=user.user_id, venue=venue, year=year)
        return me_payload(session, user)

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
            "leaderboards": build_leaderboards(session, conference_id=conference, year=year, limit=min(50, max(1, limit))),
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
    def paper_scorecard(paper_id: str, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail={"code": "paper_not_found"})
        scorecard = latest_scorecard(session, paper_id)
        if scorecard is None:
            raise HTTPException(status_code=404, detail={"code": "scorecard_not_ready"})
        user = current_user_from_request(session, request)
        payload = apply_reviewer_comments(
            session,
            paper_id,
            apply_vote_counts(session, paper_id, scorecard.public_json),
            viewer_session_id=session_id_from_request(request),
            viewer_user_id=user.user_id if user else None,
        )
        paper_payload = payload.setdefault("paper", {})
        paper_payload["paper_id"] = paper_id
        paper_payload["abstract"] = paper.abstract
        paper_payload["openreview_forum_id"] = paper.openreview_forum_id

        review_ids_by_key: dict[str, str] = {}
        source_reviews = sorted(paper.reviews, key=lambda item: item.reviewer_index)
        for index, reviewer in enumerate(payload.get("reviewers") or []):
            if not isinstance(reviewer, dict) or index >= len(source_reviews):
                continue
            reviewer.setdefault("official_review", source_reviews[index].review_text)
            reviewer.setdefault("review_chunks", [item for item in payload.get("comments") or [] if isinstance(item, dict) and item.get("reviewer_key") == reviewer.get("reviewer_key")])
            review_id = source_reviews[index].review_id
            reviewer.setdefault("review_id", review_id)
            review_ids_by_key[str(reviewer.get("reviewer_key") or f"R{index + 1}")] = review_id
        for comment in payload.get("comments") or []:
            if isinstance(comment, dict):
                comment.setdefault("review_id", review_ids_by_key.get(str(comment.get("reviewer_key") or ""), ""))
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
        user = current_user_from_request(session, request)
        result["scorecard"] = (
            apply_reviewer_comments(
                session,
                paper_id,
                apply_vote_counts(session, paper_id, scorecard.public_json),
                viewer_session_id=session_id,
                viewer_user_id=user.user_id if user else None,
            )
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
        request: Request,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        user = current_user_from_request(session, request)
        return {
            "items": list_reviewer_comments(
                session,
                paper_id,
                reviewer_key,
                viewer_session_id=session_id_from_request(request),
                viewer_user_id=user.user_id if user else None,
            )
        }

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
        user = current_user_from_request(session, request)
        enforce_comment_rate_limit(session, session_id)
        try:
            comment = add_reviewer_comment(
                session,
                paper_id=paper_id,
                reviewer_key=reviewer_key,
                session_id=session_id,
                user_id=user.user_id if user else None,
                body=str(body.get("body") or body.get("text") or ""),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail={"code": "comment_empty"})
        result = {
            "comment": comment,
            "items": list_reviewer_comments(
                session,
                paper_id,
                reviewer_key,
                viewer_session_id=session_id,
                viewer_user_id=user.user_id if user else None,
            ),
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

    @app.patch("/api/papers/{paper_id}/reviewers/{reviewer_key}/comments/{comment_id}")
    async def edit_reviewer_comment(
        paper_id: str,
        reviewer_key: str,
        comment_id: int,
        request: Request,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        body = await parse_json_body(request)
        user = current_user_from_request(session, request)
        session_id = session_id_from_request(request)
        try:
            comment = update_reviewer_comment(
                session,
                comment_id=comment_id,
                session_id=session_id,
                user_id=user.user_id if user else None,
                body=str(body.get("body") or body.get("text") or ""),
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail={"code": "comment_forbidden"})
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=404 if code == "comment_not_found" else 400, detail={"code": code})
        return {
            "comment": comment,
            "items": list_reviewer_comments(
                session,
                paper_id,
                reviewer_key,
                viewer_session_id=session_id,
                viewer_user_id=user.user_id if user else None,
            ),
        }

    @app.delete("/api/papers/{paper_id}/reviewers/{reviewer_key}/comments/{comment_id}")
    def remove_reviewer_comment(
        paper_id: str,
        reviewer_key: str,
        comment_id: int,
        request: Request,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        user = current_user_from_request(session, request)
        session_id = session_id_from_request(request)
        try:
            delete_reviewer_comment(
                session,
                comment_id=comment_id,
                session_id=session_id,
                user_id=user.user_id if user else None,
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail={"code": "comment_forbidden"})
        except ValueError:
            raise HTTPException(status_code=404, detail={"code": "comment_not_found"})
        return {
            "items": list_reviewer_comments(
                session,
                paper_id,
                reviewer_key,
                viewer_session_id=session_id,
                viewer_user_id=user.user_id if user else None,
            ),
        }

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
    header_session = (request.headers.get("x-secondopinion-session") or "").strip()
    if header_session:
        return header_session[:160]
    existing = request.cookies.get(SESSION_COOKIE)
    return existing or f"session_{uuid.uuid4().hex}"


def auth_token_from_request(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return request.cookies.get(USER_TOKEN_COOKIE) or ""


def current_user_from_request(session: Session, request: Request) -> UserAccount | None:
    return user_from_token(session, auth_token_from_request(request))


def require_user(session: Session, request: Request) -> UserAccount:
    user = current_user_from_request(session, request)
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "login_required"})
    return user


def me_payload(session: Session, user: UserAccount | None) -> dict[str, Any]:
    if user is None:
        return {"user": None, "saved_papers": [], "venue_subscriptions": []}
    return {
        "user": user_to_public_dict(user),
        "saved_papers": list_saved_papers(session, user.user_id),
        "venue_subscriptions": list_venue_subscriptions(session, user.user_id),
    }


def auth_response(session: Session, user: UserAccount, token: str) -> JSONResponse:
    payload = {"token": token, **me_payload(session, user)}
    response = JSONResponse(payload)
    response.set_cookie(
        USER_TOKEN_COOKIE,
        token,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=True,
        samesite="none",
    )
    return response


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

