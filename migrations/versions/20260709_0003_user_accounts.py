"""Add optional user accounts and saved items.

Revision ID: 20260709_0003
Revises: 20260707_0002
Create Date: 2026-07-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from secondopinion.server.models import SavedPaper, UserAccount, UserSession, VenueSubscription

revision = "20260709_0003"
down_revision = "20260707_0002"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    for table in (UserAccount.__table__, UserSession.__table__, SavedPaper.__table__, VenueSubscription.__table__):
        table.create(bind, checkfirst=True)

    if _has_table("reviewer_comments") and "user_id" not in _columns("reviewer_comments"):
        op.add_column("reviewer_comments", sa.Column("user_id", sa.String(length=80), nullable=True))
    if _has_table("reviewer_comments") and "ix_reviewer_comments_user_id" not in _indexes("reviewer_comments"):
        op.create_index("ix_reviewer_comments_user_id", "reviewer_comments", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table("reviewer_comments") and "ix_reviewer_comments_user_id" in _indexes("reviewer_comments"):
        op.drop_index("ix_reviewer_comments_user_id", table_name="reviewer_comments")
    if _has_table("reviewer_comments") and "user_id" in _columns("reviewer_comments"):
        op.drop_column("reviewer_comments", "user_id")
    for table in (VenueSubscription.__table__, SavedPaper.__table__, UserSession.__table__, UserAccount.__table__):
        table.drop(bind, checkfirst=True)
