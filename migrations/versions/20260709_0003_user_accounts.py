"""Add optional user accounts and saved items.

Revision ID: 20260709_0003
Revises: 20260707_0002
Create Date: 2026-07-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260709_0003"
down_revision = "20260707_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now_default = sa.text("CURRENT_TIMESTAMP")
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=80), primary_key=True),
        sa.Column("handle", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=240), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
    )
    op.create_index("ix_users_handle", "users", ["handle"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.String(length=80), primary_key=True),
        sa.Column("user_id", sa.String(length=80), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("session_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_session_id", "user_sessions", ["session_id"])

    op.create_table(
        "saved_papers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=80), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("paper_id", sa.String(length=120), sa.ForeignKey("papers.paper_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        sa.UniqueConstraint("user_id", "paper_id", name="uq_saved_paper_user_paper"),
    )
    op.create_index("ix_saved_papers_user_id", "saved_papers", ["user_id"])
    op.create_index("ix_saved_papers_paper_id", "saved_papers", ["paper_id"])

    op.create_table(
        "venue_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=80), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("venue", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False, server_default="2025"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        sa.UniqueConstraint("user_id", "venue", "year", name="uq_venue_subscription_user_venue_year"),
    )
    op.create_index("ix_venue_subscriptions_user_id", "venue_subscriptions", ["user_id"])
    op.create_index("ix_venue_subscriptions_venue", "venue_subscriptions", ["venue"])
    op.create_index("ix_venue_subscriptions_year", "venue_subscriptions", ["year"])

    op.add_column("reviewer_comments", sa.Column("user_id", sa.String(length=80), nullable=True))
    op.create_index("ix_reviewer_comments_user_id", "reviewer_comments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_reviewer_comments_user_id", table_name="reviewer_comments")
    op.drop_column("reviewer_comments", "user_id")
    op.drop_index("ix_venue_subscriptions_year", table_name="venue_subscriptions")
    op.drop_index("ix_venue_subscriptions_venue", table_name="venue_subscriptions")
    op.drop_index("ix_venue_subscriptions_user_id", table_name="venue_subscriptions")
    op.drop_table("venue_subscriptions")
    op.drop_index("ix_saved_papers_paper_id", table_name="saved_papers")
    op.drop_index("ix_saved_papers_user_id", table_name="saved_papers")
    op.drop_table("saved_papers")
    op.drop_index("ix_user_sessions_session_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_handle", table_name="users")
    op.drop_table("users")
