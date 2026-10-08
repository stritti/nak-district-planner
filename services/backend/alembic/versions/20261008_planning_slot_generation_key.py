"""Add planning_slots.generation_key, the stable identity of generated drafts.

The draft generator used to recognise its own slots by (date, time) only, so a
draft that a planner moved was re-created on the next nightly run (#488). The
key survives such edits. The partial unique index makes concurrent generator
runs safe and keeps cancelled generated slots from being recreated. Existing
rows stay NULL; the generator backfills them when it matches them by date/time.

The table's RLS policies are row-based and need no change for a new column.

Revision ID: 20261008_slot_gen_key
Revises: 20261001_slot_gaps
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261008_slot_gen_key"
down_revision = "20261001_slot_gaps"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_planning_slots_generation_key"


def upgrade() -> None:
    op.add_column(
        "planning_slots", sa.Column("generation_key", sa.String(length=255), nullable=True)
    )
    op.create_index(
        INDEX_NAME,
        "planning_slots",
        ["district_id", "generation_key"],
        unique=True,
        postgresql_where=sa.text("generation_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="planning_slots")
    op.drop_column("planning_slots", "generation_key")
