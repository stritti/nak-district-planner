"""Add approval scope fields to leader registrations.

Revision ID: d2c4f8a9b1e0
Revises: c9f2a4b1d3e0
Create Date: 2026-04-09 10:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d2c4f8a9b1e0"
down_revision: str | None = "c9f2a4b1d3e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "leader_registrations", sa.Column("assigned_role", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "leader_registrations",
        sa.Column("assigned_scope_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "leader_registrations",
        sa.Column("assigned_scope_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "leader_registrations", sa.Column("approved_by_sub", sa.String(length=512), nullable=True)
    )
    op.add_column(
        "leader_registrations", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("leader_registrations", "approved_at")
    op.drop_column("leader_registrations", "approved_by_sub")
    op.drop_column("leader_registrations", "assigned_scope_id")
    op.drop_column("leader_registrations", "assigned_scope_type")
    op.drop_column("leader_registrations", "assigned_role")
