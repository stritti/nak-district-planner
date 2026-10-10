# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

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
    op.add_column("planning_slots", sa.Column("generation_key_detached", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table(
        "deleted_generation_keys",
        sa.Column("district_id", sa.UUID(as_uuid=True), sa.ForeignKey("districts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("generation_key", sa.String(255), primary_key=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
    )
    scope = """(
        current_setting('app.is_system_worker', true) = 'true'
        OR EXISTS (
            SELECT 1 FROM users
            WHERE sub = current_setting('app.current_user_sub', true)
              AND is_superadmin
        )
        OR EXISTS (
            SELECT 1 FROM memberships
            WHERE user_sub = current_setting('app.current_user_sub', true)
              AND scope_type = 'DISTRICT'
              AND scope_id = deleted_generation_keys.district_id
              AND role IN ('PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
        )
    )"""
    op.execute(f"CREATE POLICY deleted_generation_keys_tenant ON deleted_generation_keys FOR ALL USING {scope} WITH CHECK {scope}")
    op.execute("ALTER TABLE deleted_generation_keys ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE deleted_generation_keys FORCE ROW LEVEL SECURITY")
    # Existing confirmed slots were already distributed before this migration.
    op.execute("""
        UPDATE planning_slots SET released_at = updated_at
        WHERE approval_status = 'CONFIRMED' AND released_at IS NULL
    """)


def downgrade() -> None:
    op.drop_table("deleted_generation_keys")
    op.drop_column("planning_slots", "generation_key_detached")
    op.drop_column("planning_slots", "released_at")
