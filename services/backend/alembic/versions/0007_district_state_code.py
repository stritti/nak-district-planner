"""Add state_code to districts

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-07 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "districts",
        sa.Column("state_code", sa.String(2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("districts", "state_code")
