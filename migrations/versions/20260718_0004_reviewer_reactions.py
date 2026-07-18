"""Add reviewer_reactions table.

Revision ID: 20260718_0004
Revises: 20260709_0003
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op

from secondopinion.server.models import ReviewerReaction

revision = "20260718_0004"
down_revision = "20260709_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ReviewerReaction.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    ReviewerReaction.__table__.drop(op.get_bind(), checkfirst=True)
