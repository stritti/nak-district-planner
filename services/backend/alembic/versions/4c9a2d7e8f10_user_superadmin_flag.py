"""Add user superadmin flag.

Revision ID: 4c9a2d7e8f10
Revises: 3b7d9e1a4c20
Create Date: 2026-04-03 14:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4c9a2d7e8f10"
down_revision: Union[str, None] = "3b7d9e1a4c20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "is_superadmin")
