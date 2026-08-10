"""Add last_sync_error to calendar_integrations.

Revision ID: 0013
Revises: ae6c055cc051
Create Date: 2026-08-10 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "ae6c055cc051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("calendar_integrations", sa.Column("last_sync_error", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("calendar_integrations", "last_sync_error")
