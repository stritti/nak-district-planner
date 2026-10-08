"""Let congregation export tokens read district slots distributed to them.

Issue #466: the SELECT policies on planning_slots (and the event_instances /
service_assignments rows derived from them) only allowed a congregation export
token to read slots whose congregation_id equals the token's congregation, so
district slots (congregation_id NULL) distributed via ``applicability`` never
reached congregation feeds. The new policies additionally allow district slots
of the token's district whose applicability contains 'all' or the token's
congregation id. Downgrade restores the previous policies.

Revision ID: 20261008_rls_distributed
Revises: 20261007_confirm_holidays
"""

from __future__ import annotations

from collections.abc import Callable

from alembic import op
from app.adapters.db.migrations.rls_policies import (
    planning_slot_read_sql,
    planning_slot_row_read_sql,
    related_planning_slot_sql,
)

revision = "20261008_rls_distributed"
down_revision = "20261007_confirm_holidays"
branch_labels = None
depends_on = None


def _recreate_select_policies(read_sql: Callable[[str], str]) -> None:
    policies = {
        "planning_slots": ("planning_slots_tenant_isolation_policy", read_sql("planning_slots")),
        "event_instances": (
            "event_instances_tenant_isolation_policy",
            related_planning_slot_sql("event_instances", read_sql),
        ),
        "service_assignments": (
            "service_assignments_tenant_isolation_policy",
            related_planning_slot_sql("service_assignments", read_sql),
        ),
    }
    for table, (policy, using) in policies.items():
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"CREATE POLICY {policy} ON {table} FOR SELECT USING {using}")  # nosec B608


def upgrade() -> None:
    _recreate_select_policies(planning_slot_row_read_sql)


def downgrade() -> None:
    _recreate_select_policies(planning_slot_read_sql)
