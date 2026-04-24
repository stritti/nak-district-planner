"""Add leader_registrations table for self-registration workflow

Revision ID: 0010_leader_registrations
Revises: 0009
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_leader_registrations"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leader_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "district_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("rank", sa.String(20), nullable=True),
        sa.Column(
            "congregation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("special_role", sa.String(50), nullable=True),
        sa.Column("phone", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("user_sub", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_leader_registrations_district_id",
        "leader_registrations",
        ["district_id"],
    )
    op.create_index(
        "ix_leader_registrations_status",
        "leader_registrations",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_leader_registrations_status", table_name="leader_registrations")
    op.drop_index("ix_leader_registrations_district_id", table_name="leader_registrations")
    op.drop_table("leader_registrations")
