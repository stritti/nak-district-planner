"""Index the foreign keys of service_assignments.

The table only had its primary key. Every matrix request looks assignments up
by ``planning_slot_id`` (``event_id`` as compatibility fallback) and therefore
scanned the assignments of all districts; deleting planning slots or leaders
scanned it again for the cascading foreign keys. Found by the RLS overhead
benchmark (tests/performance/test_rls_overhead.py), where the plan flipped to a
full scan depending on table statistics.

Built CONCURRENTLY so production writes are not blocked while indexing.

Revision ID: 0024
Revises: 0023
"""

from __future__ import annotations

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

_INDEXES = {
    "ix_service_assignments_planning_slot_id": "planning_slot_id",
    "ix_service_assignments_event_id": "event_id",
    "ix_service_assignments_leader_id": "leader_id",
}


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, column in _INDEXES.items():
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON service_assignments ({column})"
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name in _INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
