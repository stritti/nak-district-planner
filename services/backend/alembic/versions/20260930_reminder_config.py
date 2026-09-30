"""Create district reminders and idempotent per-recipient monthly dispatch ledger.

Revision ID: 20260930_reminder
Revises: 0123
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "20260930_reminder"
down_revision = "0123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "district_reminder_config",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("district_id", UUID(as_uuid=True), sa.ForeignKey("districts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("time_of_day", sa.Time(timezone=False), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("recipient_role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("day_of_month BETWEEN 1 AND 31", name="ck_reminder_day"),
    )
    op.create_index("ix_district_reminder_config_district_id", "district_reminder_config", ["district_id"])
    op.create_table(
        "reminder_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reminder_id", UUID(as_uuid=True), sa.ForeignKey("district_reminder_config.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_month", sa.Date(), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("reminder_id", "scheduled_month", "recipient", name="uq_reminder_delivery"),
    )


def downgrade() -> None:
    op.drop_table("reminder_deliveries")
    op.drop_index("ix_district_reminder_config_district_id", table_name="district_reminder_config")
    op.drop_table("district_reminder_config")
