"""Allow only one service assignment per planning slot (#468).

The matrix shows one leader per slot, but nothing prevented a second
assignment row for the same slot; the matrix then picked one arbitrarily.

Steps (under a table lock, so no row can slip in between):

1. Backfill ``planning_slot_id`` from the legacy ``event_id`` where it still
   points at an existing planning slot, so legacy rows are covered too.
2. Resolve existing duplicates deterministically. Per planning slot the row
   kept is the "most confirmed" one, then the newest:
   status CONFIRMED > ASSIGNED > OPEN, then a linked leader (leader_id set)
   over a free-text name, then updated_at DESC, created_at DESC, id ASC.
   All other rows of that slot are deleted. The downgrade does not restore them.
3. Replace the plain index on ``planning_slot_id`` by a unique one.

service_assignments has no soft-delete column and every status (OPEN,
ASSIGNED, CONFIRMED) occupies the slot, so the index is not partial; rows
without planning_slot_id (unresolvable legacy rows) stay outside it because
NULLs are distinct.

Revision ID: 20261007_assignment_unique
Revises: 20261001_slot_gaps
"""

from __future__ import annotations

from alembic import op

revision = "20261007_assignment_unique"
down_revision = "20261001_slot_gaps"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_service_assignments_planning_slot_id"

BACKFILL_PLANNING_SLOT_SQL = """
UPDATE service_assignments sa
SET planning_slot_id = sa.event_id
WHERE sa.planning_slot_id IS NULL
  AND EXISTS (SELECT 1 FROM planning_slots ps WHERE ps.id = sa.event_id);
"""

DELETE_DUPLICATES_SQL = """
DELETE FROM service_assignments sa
USING (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY planning_slot_id
               ORDER BY
                   CASE status
                       WHEN 'CONFIRMED' THEN 0
                       WHEN 'ASSIGNED' THEN 1
                       ELSE 2
                   END,
                   (leader_id IS NULL),
                   updated_at DESC,
                   created_at DESC,
                   id::text ASC
           ) AS rank
    FROM service_assignments
    WHERE planning_slot_id IS NOT NULL
) ranked
WHERE sa.id = ranked.id
  AND ranked.rank > 1;
"""


def upgrade() -> None:
    op.execute("LOCK TABLE service_assignments IN SHARE ROW EXCLUSIVE MODE")
    op.execute(BACKFILL_PLANNING_SLOT_SQL)
    op.execute(DELETE_DUPLICATES_SQL)
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
    op.create_index(INDEX_NAME, "service_assignments", ["planning_slot_id"], unique=True)


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="service_assignments")
    op.create_index(INDEX_NAME, "service_assignments", ["planning_slot_id"])
