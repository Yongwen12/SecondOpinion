"""Create SecondOpinion server schema.

Revision ID: 20260621_0001
Revises:
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op

from secondopinion.server.database import Base
from secondopinion.server import models  # noqa: F401

revision = "20260621_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
