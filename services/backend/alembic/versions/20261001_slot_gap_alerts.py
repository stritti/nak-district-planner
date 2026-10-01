"""Create slot_gap_alerts, the ledger of reported service gaps.

Only the daily scan (system worker) reads and writes it; RLS is forced so the
application role cannot touch it from a request.

Revision ID: 20261001_slot_gaps
Revises: 20261001_merge_heads
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "20261001_slot_gaps"
down_revision = "20261001_merge_heads"
branch_labels = None
depends_on = None

_SYSTEM_ONLY = """(
    current_setting('app.is_system_worker', true) = 'true'
    OR EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub', true) AND is_superadmin)
)"""


def upgrade() -> None:
    op.create_table(
        "slot_gap_alerts",
        sa.Column(
            "planning_slot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("planning_slots.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "district_id",
            UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("congregation_id", UUID(as_uuid=True), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        f"CREATE POLICY slot_gap_alerts_system ON slot_gap_alerts "
        f"FOR ALL USING {_SYSTEM_ONLY} WITH CHECK {_SYSTEM_ONLY}"
    )
    op.execute("ALTER TABLE slot_gap_alerts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE slot_gap_alerts FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("slot_gap_alerts")
