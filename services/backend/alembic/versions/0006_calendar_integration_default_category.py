"""Add default_category to calendar_integrations

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-07 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "calendar_integrations",
        sa.Column("default_category", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calendar_integrations", "default_category")
