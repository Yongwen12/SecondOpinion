"""Add reviewer_comments table.

Revision ID: 20260707_0002
Revises: 20260621_0001
Create Date: 2026-07-07
"""

from __future__ import annotations

from alembic import op

from secondopinion.server.models import ReviewerComment

revision = "20260707_0002"
down_revision = "20260621_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ReviewerComment.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    ReviewerComment.__table__.drop(op.get_bind(), checkfirst=True)
