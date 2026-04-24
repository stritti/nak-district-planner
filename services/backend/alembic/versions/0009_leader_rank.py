"""Add rank and special_role to leaders

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-08 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leaders", sa.Column("rank", sa.String(20), nullable=True))
    op.add_column("leaders", sa.Column("special_role", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("leaders", "special_role")
    op.drop_column("leaders", "rank")
