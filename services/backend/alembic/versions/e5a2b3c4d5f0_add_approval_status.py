"""add approval_status to events

Revision ID: e5a2b3c4d5f0
Revises: e4b2a9d7f110
Create Date: 2026-05-31 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a2b3c4d5f0"
down_revision: str | None = "e4b2a9d7f110"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the enum type first
    sa.Enum("PLANNED", "CONFIRMED", name="event_approval_status").create(op.get_bind())

    # Add the column as nullable initially so we can backfill
    op.add_column(
        "events",
        sa.Column(
            "approval_status",
            sa.Enum("PLANNED", "CONFIRMED", name="event_approval_status", create_type=False),
            nullable=True,
        ),
    )

    # Backfill: existing non-cancelled events → CONFIRMED, cancelled events → PLANNED
    op.execute(
        "UPDATE events SET approval_status = 'CONFIRMED' WHERE status != 'CANCELLED'"
    )
    op.execute(
        "UPDATE events SET approval_status = 'PLANNED' WHERE status = 'CANCELLED'"
    )

    # Make the column NOT NULL now that it's backfilled
    op.alter_column("events", "approval_status", nullable=False)


def downgrade() -> None:
    op.drop_column("events", "approval_status")
    sa.Enum(name="event_approval_status").drop(op.get_bind(), if_exists=True)
