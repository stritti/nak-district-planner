"""Create memberships table for RBAC.

Revision ID: 2a9c4d5e6f70
Revises: 1f8a9b0c3d10
Create Date: 2026-04-02 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2a9c4d5e6f70"
down_revision: Union[str, None] = "1f8a9b0c3d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("user_sub", sa.String(512), nullable=False),
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "scope_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "scope_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_sub"], ["users.sub"], name="fk_memberships_user_sub"),
        sa.UniqueConstraint(
            "user_sub", "role", "scope_type", "scope_id", name="uq_memberships_user_role_scope"
        ),
    )
    # Create indexes for frequently queried columns
    op.create_index("ix_memberships_user_sub", "memberships", ["user_sub"])
    op.create_index("ix_memberships_scope", "memberships", ["scope_type", "scope_id"])
    op.create_index("ix_memberships_role", "memberships", ["role"])


def downgrade() -> None:
    op.drop_table("memberships")
