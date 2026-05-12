"""Add generation slot key for auto-generated services.

Revision ID: c9f2a4b1d3e0
Revises: b15c9d3e4f21
Create Date: 2026-04-07 13:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "c9f2a4b1d3e0"
down_revision: str | None = "b15c9d3e4f21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("generation_slot_key", sa.String(length=255), nullable=True))
    op.create_index(
        "ux_events_generation_slot_key",
        "events",
        ["district_id", "congregation_id", "generation_slot_key"],
        unique=True,
        postgresql_where=sa.text("generation_slot_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_events_generation_slot_key", table_name="events")
    op.drop_column("events", "generation_slot_key")
