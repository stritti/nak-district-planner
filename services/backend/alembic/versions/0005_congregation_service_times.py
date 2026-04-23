"""Add service_times to congregations

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-07 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT = '[{"weekday": 6, "time": "09:30"}, {"weekday": 2, "time": "20:00"}]'


def upgrade() -> None:
    op.add_column(
        "congregations",
        sa.Column(
            "service_times",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(f"'{_DEFAULT}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("congregations", "service_times")
