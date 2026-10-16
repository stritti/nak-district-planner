# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Separate mutable notification acknowledgement state per OIDC subject (#601).

Legacy global timestamps cannot be attributed to users. They are deliberately
not migrated into this table: alerts become visible once again to all users,
who can independently mark them read/dismissed after deployment.
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "20261016_notification_user_states"
down_revision = "20261015_hash_export_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_user_states",
        sa.Column("notification_id", sa.UUID(), sa.ForeignKey("notifications.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_sub", sa.String(512), sa.ForeignKey("users.sub", ondelete="CASCADE"), primary_key=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("ALTER TABLE notification_user_states ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notification_user_states FORCE ROW LEVEL SECURITY")
    scope = """(
        (
          user_sub = current_setting('app.current_user_sub', true)
          AND EXISTS (
            SELECT 1 FROM notifications n
            WHERE n.id = notification_user_states.notification_id
          )
        )
        OR current_setting('app.is_system_worker', true) = 'true'
    )"""
    for action in ("SELECT", "DELETE"):
        op.execute(
            f"CREATE POLICY notification_user_states_{action.lower()} "
            f"ON notification_user_states FOR {action} USING {scope}"
        )
    op.execute(
        f"CREATE POLICY notification_user_states_insert ON notification_user_states "
        f"FOR INSERT WITH CHECK {scope}"
    )
    op.execute(
        f"CREATE POLICY notification_user_states_update ON notification_user_states "
        f"FOR UPDATE USING {scope} WITH CHECK {scope}"
    )
    role = os.getenv("APP_DB_USER", "nak_app").replace('"', '""')
    op.execute(
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON notification_user_states TO "{role}"'
    )


def downgrade() -> None:
    op.drop_table("notification_user_states")
