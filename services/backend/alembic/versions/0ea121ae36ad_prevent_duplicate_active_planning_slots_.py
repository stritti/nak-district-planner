"""Prevent duplicate active planning slots per congregation and time.

Guards against double-booking a congregation for the exact same date/time
slot (e.g. two Gottesdienst entries accidentally created for the same
congregation at the same time). Scoped to rows where congregation_id is
set (district-wide slots with congregation_id IS NULL are a separate case,
not covered here) and status='ACTIVE' (cancelled slots must not block a
legitimate reschedule onto the same date/time).

This does not model true time-range overlap (e.g. a 9:00-10:30 slot
conflicting with a 10:00-11:00 slot) — planning_slots has a single
planning_time, not a duration. See docs/schema.md for context and the
follow-up needed for real overlap detection once event_instances carries
its own congregation_id.

Revision ID: 0ea121ae36ad
Revises: change_applicability_to_text
Create Date: 2026-09-07 09:54:32.896002

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0ea121ae36ad"
down_revision: str | None = "change_applicability_to_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "no_overlapping_planning_slots"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "planning_slots",
        ["congregation_id", "planning_date", "planning_time"],
        unique=True,
        postgresql_where="congregation_id IS NOT NULL AND status = 'ACTIVE'",
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="planning_slots")
