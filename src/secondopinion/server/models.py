from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Conference(Base):
    __tablename__ = "conferences"

    conference_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    venue: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    papers: Mapped[list["Paper"]] = relationship(back_populates="conference")


class Paper(Base):
    __tablename__ = "papers"

    paper_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    openreview_forum_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    conference_id: Mapped[str] = mapped_column(ForeignKey("conferences.conference_id"), index=True, nullable=False)
    venue: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str] = mapped_column(Text, default="", nullable=False)
    decision: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pdf_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    conference: Mapped[Conference] = relationship(back_populates="papers")
    reviews: Mapped[list["Review"]] = relationship(back_populates="paper", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True, nullable=False)
    reviewer_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reviewer_internal_id: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    review_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    strengths: Mapped[str] = mapped_column(Text, default="", nullable=False)
    weaknesses: Mapped[str] = mapped_column(Text, default="", nullable=False)
    questions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rating_raw: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    rating_normalized: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_raw: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    confidence_normalized: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_stage: Mapped[str] = mapped_column(String(80), default="initial", nullable=False)
    raw_invitation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    paper: Mapped[Paper] = relationship(back_populates="reviews")


class ReviewerAlias(Base):
    __tablename__ = "reviewer_aliases"
    __table_args__ = (UniqueConstraint("paper_id", "review_id", name="uq_reviewer_alias_paper_review"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True, nullable=False)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.review_id"), index=True, nullable=False)
    reviewer_key: Mapped[str] = mapped_column(String(40), nullable=False)
    nickname: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    avatar_key: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Scorecard(Base):
    __tablename__ = "scorecards"
    __table_args__ = (
        UniqueConstraint("paper_id", "scorer_version", "memory_index_version", name="uq_scorecard_paper_version"),
    )

    scorecard_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    scorer_version: Mapped[str] = mapped_column(String(120), nullable=False)
    memory_index_version: Mapped[str] = mapped_column(String(120), nullable=False)
    public_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    internal_artifact_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReviewerScore(Base):
    __tablename__ = "reviewer_scores"
    __table_args__ = (UniqueConstraint("scorecard_id", "reviewer_key", name="uq_reviewer_score_card_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scorecard_id: Mapped[str] = mapped_column(ForeignKey("scorecards.scorecard_id"), index=True, nullable=False)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True, nullable=False)
    conference_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    reviewer_key: Mapped[str] = mapped_column(String(40), nullable=False)
    nickname: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    avatar_key: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    social_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ScoringJob(Base):
    __tablename__ = "scoring_jobs"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, default="queued", nullable=False)
    requested_by_session: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    scorer_version: Mapped[str] = mapped_column(String(120), nullable=False)
    memory_index_version: Mapped[str] = mapped_column(String(120), nullable=False)
    input_artifact_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output_artifact_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("paper_id", "reviewer_key", "session_id", name="uq_vote_session_reviewer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True, nullable=False)
    reviewer_key: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    vote: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    conference_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    public_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MemoryIndex(Base):
    __tablename__ = "memory_indexes"

    version: Mapped[str] = mapped_column(String(120), primary_key=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dimensions_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    ingest_run_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="succeeded", nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    artifact_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
