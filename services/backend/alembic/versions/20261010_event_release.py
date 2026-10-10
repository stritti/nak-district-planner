"""Preserve publication history before allowing draft deletion.

Revision ID: 20261010_event_release
Revises: 20261008_slot_gen_key
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261010_event_release"
down_revision = "20261008_slot_gen_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("planning_slots", sa.Column("released_at", sa.DateTime(timezone=True), nullable=True))
    # Existing confirmed slots were already distributed before this migration.
    op.execute("""
        UPDATE planning_slots SET released_at = updated_at
        WHERE approval_status = 'CONFIRMED' AND released_at IS NULL
    """)


def downgrade() -> None:
    op.drop_column("planning_slots", "released_at")
