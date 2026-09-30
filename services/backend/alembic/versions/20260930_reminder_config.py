"""Create district reminders, delivery ledger, and tenant isolation policies.

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

# New tenant tables require explicit policies: migrations creating tables after
# the initial RLS rollout are not automatically covered by that rollout.
_REMINDER_ADMIN = """(
    current_setting('app.is_system_worker', true) = 'true'
    OR EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub', true) AND is_superadmin)
    OR EXISTS (
        SELECT 1 FROM memberships
        WHERE user_sub = current_setting('app.current_user_sub', true)
          AND scope_type = 'DISTRICT'
          AND role = 'DISTRICT_ADMIN'
          AND scope_id = district_reminder_config.district_id
    )
)"""
_DELIVERY_WORKER = "current_setting('app.is_system_worker', true) = 'true'"


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
    # Policies precede ENABLE ROW LEVEL SECURITY. Workers use an explicit
    # transaction-local system context and never expose the ledger to clients.
    op.execute(f"CREATE POLICY reminder_configs_select ON district_reminder_config FOR SELECT USING {_REMINDER_ADMIN}")
    op.execute(f"CREATE POLICY reminder_configs_insert ON district_reminder_config FOR INSERT WITH CHECK {_REMINDER_ADMIN}")
    op.execute(f"CREATE POLICY reminder_configs_update ON district_reminder_config FOR UPDATE USING {_REMINDER_ADMIN} WITH CHECK {_REMINDER_ADMIN}")
    op.execute(f"CREATE POLICY reminder_configs_delete ON district_reminder_config FOR DELETE USING {_REMINDER_ADMIN}")
    op.execute(f"CREATE POLICY reminder_deliveries_select ON reminder_deliveries FOR SELECT USING ({_DELIVERY_WORKER})")
    op.execute(f"CREATE POLICY reminder_deliveries_insert ON reminder_deliveries FOR INSERT WITH CHECK ({_DELIVERY_WORKER})")
    op.execute(f"CREATE POLICY reminder_deliveries_update ON reminder_deliveries FOR UPDATE USING ({_DELIVERY_WORKER}) WITH CHECK ({_DELIVERY_WORKER})")
    op.execute("ALTER TABLE district_reminder_config ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE reminder_deliveries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE district_reminder_config FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE reminder_deliveries FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("reminder_deliveries")
    op.drop_index("ix_district_reminder_config_district_id", table_name="district_reminder_config")
    op.drop_table("district_reminder_config")
