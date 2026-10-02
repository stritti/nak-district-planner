"""Create event_mail_hooks with tenant isolation.

Revision ID: 20260930_event_hooks
Revises: 0026
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "20260930_event_hooks"
down_revision = "0026"
branch_labels = None
depends_on = None

# Same access rule as district_reminder_config: district admins manage hooks,
# the system worker reads them while dispatching.
_HOOK_ADMIN = """(
    current_setting('app.is_system_worker', true) = 'true'
    OR EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub', true) AND is_superadmin)
    OR EXISTS (
        SELECT 1 FROM memberships
        WHERE user_sub = current_setting('app.current_user_sub', true)
          AND scope_type = 'DISTRICT'
          AND role = 'DISTRICT_ADMIN'
          AND scope_id = event_mail_hooks.district_id
    )
)"""


def upgrade() -> None:
    op.create_table(
        "event_mail_hooks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "district_id",
            UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("recipient_role", sa.String(50), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_event_mail_hooks_dispatch",
        "event_mail_hooks",
        ["district_id", "event_type", "is_active"],
    )
    for action, clause in {
        "select": f"FOR SELECT USING {_HOOK_ADMIN}",
        "insert": f"FOR INSERT WITH CHECK {_HOOK_ADMIN}",
        "update": f"FOR UPDATE USING {_HOOK_ADMIN} WITH CHECK {_HOOK_ADMIN}",
        "delete": f"FOR DELETE USING {_HOOK_ADMIN}",
    }.items():
        op.execute(f"CREATE POLICY event_mail_hooks_{action} ON event_mail_hooks {clause}")
    op.execute("ALTER TABLE event_mail_hooks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE event_mail_hooks FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_event_mail_hooks_dispatch", table_name="event_mail_hooks")
    op.drop_table("event_mail_hooks")
