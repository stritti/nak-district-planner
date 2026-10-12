# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Create tenant-isolated opt-in recurring templates and occurrence decisions.

Revision ID: 20261012_recurring_events
Revises: 20261011_sync_attempt
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from alembic import op

revision = "20261012_recurring_events"
down_revision = "20261011_sync_attempt"
branch_labels = None
depends_on = None


_COMMON = """(
    current_setting('app.is_system_worker', true) = 'true'
    OR EXISTS (
        SELECT 1 FROM users
        WHERE sub = current_setting('app.current_user_sub', true)
          AND is_superadmin
    )
)"""

_TEMPLATE_READ = f"""(
    {_COMMON}
    OR EXISTS (
        SELECT 1 FROM memberships m
        WHERE m.user_sub = current_setting('app.current_user_sub', true)
          AND m.scope_type = 'DISTRICT'
          AND m.scope_id = recurring_event_templates.district_id
    )
    OR EXISTS (
        SELECT 1 FROM memberships m
        WHERE m.user_sub = current_setting('app.current_user_sub', true)
          AND m.scope_type = 'CONGREGATION'
          AND (
              m.scope_id = recurring_event_templates.congregation_id
              OR (
                  recurring_event_templates.congregation_id IS NULL
                  AND (
                      'all' = ANY(recurring_event_templates.applicability)
                      OR m.scope_id::text = ANY(recurring_event_templates.applicability)
                  )
              )
          )
    )
)"""

_TEMPLATE_WRITE = f"""(
    {_COMMON}
    OR EXISTS (
        SELECT 1 FROM memberships m
        WHERE m.user_sub = current_setting('app.current_user_sub', true)
          AND m.scope_type = 'DISTRICT'
          AND m.scope_id = recurring_event_templates.district_id
          AND m.role = 'DISTRICT_ADMIN'
    )
    OR (
        recurring_event_templates.congregation_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM memberships m
            WHERE m.user_sub = current_setting('app.current_user_sub', true)
              AND m.scope_type = 'CONGREGATION'
              AND m.scope_id = recurring_event_templates.congregation_id
              AND m.role = 'CONGREGATION_ADMIN'
        )
    )
)"""

_DECISION_READ = f"""(
    {_COMMON}
    OR EXISTS (
        SELECT 1 FROM recurring_event_templates t
        WHERE t.id = recurring_event_decisions.template_id
          AND t.district_id = recurring_event_decisions.district_id
    )
)"""

_DECISION_WRITE = f"""(
    {_COMMON}
    OR EXISTS (
        SELECT 1 FROM recurring_event_templates t
        WHERE t.id = recurring_event_decisions.template_id
          AND t.district_id = recurring_event_decisions.district_id
          AND (
              EXISTS (
                  SELECT 1 FROM memberships m
                  WHERE m.user_sub = current_setting('app.current_user_sub', true)
                    AND m.scope_type = 'DISTRICT'
                    AND m.scope_id = t.district_id
                    AND m.role = 'DISTRICT_ADMIN'
              )
              OR (
                  t.congregation_id IS NOT NULL
                  AND EXISTS (
                      SELECT 1 FROM memberships m
                      WHERE m.user_sub = current_setting('app.current_user_sub', true)
                        AND m.scope_type = 'CONGREGATION'
                        AND m.scope_id = t.congregation_id
                        AND m.role = 'CONGREGATION_ADMIN'
                  )
              )
          )
    )
)"""


def _policies(table: str, read: str, write: str) -> None:
    for operation, clause in (
        ("select", f"FOR SELECT USING {read}"),
        ("insert", f"FOR INSERT WITH CHECK {write}"),
        ("update", f"FOR UPDATE USING {write} WITH CHECK {write}"),
        ("delete", f"FOR DELETE USING {write}"),
    ):
        # nosec B608: identifiers and SQL predicates are developer-owned constants.
        op.execute(f"CREATE POLICY {table}_{operation} ON {table} {clause}")
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    # Composite FKs disallow a valid UUID borrowed from a different district.
    op.create_unique_constraint(
        "uq_congregations_id_district", "congregations", ["id", "district_id"]
    )
    op.create_unique_constraint(
        "uq_planning_slots_id_district", "planning_slots", ["id", "district_id"]
    )
    op.create_table(
        "recurring_event_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "district_id", UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("congregation_id", UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("start_time", sa.Time(timezone=False), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("recurrence", JSONB(), nullable=False),
        sa.Column(
            "applicability", ARRAY(sa.String(64)), nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column(
            "excluded_dates", JSONB(), nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("active_from", sa.Date(), nullable=True),
        sa.Column("active_until", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["congregation_id", "district_id"],
            ["congregations.id", "congregations.district_id"],
            name="fk_recurring_templates_congregation_scope",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("id", "district_id", name="uq_recurring_templates_id_district"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_recurring_template_duration"),
        sa.CheckConstraint("revision > 0", name="ck_recurring_template_revision"),
        sa.CheckConstraint(
            "active_until IS NULL OR active_from IS NULL OR active_until >= active_from",
            name="ck_recurring_template_active_range",
        ),
    )
    op.create_index(
        "ix_recurring_templates_district_scope",
        "recurring_event_templates", ["district_id", "congregation_id"],
    )
    op.create_table(
        "recurring_event_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "district_id", UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("template_id", UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_local_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("planning_slot_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "template_id", "occurrence_local_date",
            name="uq_recurring_decision_occurrence",
        ),
        sa.ForeignKeyConstraint(
            ["template_id", "district_id"],
            ["recurring_event_templates.id", "recurring_event_templates.district_id"],
            ondelete="CASCADE", name="fk_recurring_decisions_template_scope",
        ),
        sa.ForeignKeyConstraint(
            ["planning_slot_id", "district_id"],
            ["planning_slots.id", "planning_slots.district_id"],
            ondelete="SET NULL (planning_slot_id)",
            name="fk_recurring_decisions_slot_scope",
        ),
        sa.CheckConstraint(
            "status IN ('ACCEPTED', 'SKIPPED')",
            name="ck_recurring_decision_status",
        ),
        sa.CheckConstraint(
            "status != 'SKIPPED' OR planning_slot_id IS NULL",
            name="ck_recurring_decision_skipped_slot",
        ),
    )
    op.create_index(
        "ix_recurring_decisions_district_date",
        "recurring_event_decisions", ["district_id", "occurrence_local_date"],
    )
    _policies("recurring_event_templates", _TEMPLATE_READ, _TEMPLATE_WRITE)
    _policies("recurring_event_decisions", _DECISION_READ, _DECISION_WRITE)


def downgrade() -> None:
    op.drop_table("recurring_event_decisions")
    op.drop_table("recurring_event_templates")
    op.drop_constraint("uq_planning_slots_id_district", "planning_slots", type_="unique")
    op.drop_constraint("uq_congregations_id_district", "congregations", type_="unique")
