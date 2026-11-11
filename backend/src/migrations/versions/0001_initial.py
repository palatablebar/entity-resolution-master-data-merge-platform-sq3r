"""initial baseline: 所有表由 src.models.Base 声明（public schema）。

Revision ID: 0001
"""
from __future__ import annotations

from alembic import op

from src.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
