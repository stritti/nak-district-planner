"""Add leaders table

Revision ID: 0008
Revises: faecec299731
Create Date: 2026-03-08 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "faecec299731"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. CREATE TABLE leaders
    op.create_table(
        "leaders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "district_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "congregation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 2. ADD leader_id to service_assignments
    op.add_column(
        "service_assignments",
        sa.Column(
            "leader_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leaders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # 3. Make leader_name nullable in service_assignments
    op.alter_column("service_assignments", "leader_name", nullable=True)

    # 4. ADD leader_id to export_tokens
    op.add_column(
        "export_tokens",
        sa.Column(
            "leader_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leaders.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("export_tokens", "leader_id")
    op.alter_column("service_assignments", "leader_name", nullable=False)
    op.drop_column("service_assignments", "leader_id")
    op.drop_table("leaders")
