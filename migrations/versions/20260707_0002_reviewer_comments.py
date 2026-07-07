"""Add reviewer_comments table.

Revision ID: 20260707_0002
Revises: 20260621_0001
Create Date: 2026-07-07
"""

from __future__ import annotations

from alembic import op

from secondopinion.server.database import Base
from secondopinion.server import models  # noqa: F401

revision = "20260707_0002"
down_revision = "20260621_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # create_all is checkfirst by default, so only the new reviewer_comments table is created.
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    op.drop_table("reviewer_comments")
