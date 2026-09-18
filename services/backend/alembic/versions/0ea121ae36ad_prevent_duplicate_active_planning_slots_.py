"""Prevent duplicate active planning slots per congregation and time.

Guards against double-booking a congregation for the exact same date/time
slot (e.g. two Gottesdienst entries accidentally created for the same
congregation at the same time). Scoped to rows where congregation_id is
set (district-wide slots with congregation_id IS NULL are a separate case,
not covered here) and status='ACTIVE' (cancelled slots must not block a
legitimate reschedule onto the same date/time).

This does not model true time-range overlap (e.g. a 9:00-10:30 slot
conflicting with a 10:00-11:00 slot) — planning_slots has a single
planning_time, not a duration. See docs/schema.md for context and the
follow-up needed for real overlap detection once event_instances carries
its own congregation_id.

Revision ID: 0ea121ae36ad
Revises: 0016
Create Date: 2026-09-07 09:54:32.896002

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0ea121ae36ad"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "no_overlapping_planning_slots"

RANKED_DUPLICATE_ACTIVE_SLOTS_CTE = """
WITH duplicate_groups AS (
    SELECT congregation_id, planning_date, planning_time
    FROM planning_slots
    WHERE congregation_id IS NOT NULL
      AND status = 'ACTIVE'
    GROUP BY congregation_id, planning_date, planning_time
    HAVING COUNT(*) > 1
), ranked AS (
    SELECT
        ps.id,
        FIRST_VALUE(ps.id) OVER (
            PARTITION BY ps.congregation_id, ps.planning_date, ps.planning_time
            ORDER BY
                (ei.id IS NOT NULL) DESC,
                (ps.invitation_source_event_id IS NOT NULL) DESC,
                ps.updated_at DESC,
                ps.created_at DESC,
                ps.id::text ASC
        ) AS keep_id
    FROM planning_slots ps
    JOIN duplicate_groups dg
      ON dg.congregation_id = ps.congregation_id
     AND dg.planning_date = ps.planning_date
     AND dg.planning_time = ps.planning_time
    LEFT JOIN event_instances ei ON ei.planning_slot_id = ps.id
    WHERE ps.status = 'ACTIVE'
)
"""

LOCK_RECONCILIATION_TABLES_SQL = """
LOCK TABLE planning_slots, service_assignments, congregation_invitations,
    invitation_overwrite_requests, event_instances IN SHARE ROW EXCLUSIVE MODE;
"""

REJECT_AMBIGUOUS_DUPLICATES_SQL = """
DO $$
BEGIN
        IF EXISTS (
                SELECT 1
                FROM planning_slots ps
                LEFT JOIN event_instances ei ON ei.planning_slot_id = ps.id
                WHERE ps.congregation_id IS NOT NULL
                    AND ps.status = 'ACTIVE'
                GROUP BY ps.congregation_id, ps.planning_date, ps.planning_time
                                HAVING COUNT(*) > 1
                                     AND (
                                             COUNT(*) <> 2
                                             OR COUNT(ei.id) <> 1
                                             OR NOT EXISTS (
                                                     SELECT 1
                                                     FROM planning_slots instance_slot
                                                     JOIN event_instances instance
                                                         ON instance.planning_slot_id = instance_slot.id
                                                     JOIN planning_slots legacy_slot
                                                         ON legacy_slot.id <> instance_slot.id
                                                     WHERE instance_slot.congregation_id = ps.congregation_id
                                                         AND instance_slot.planning_date = ps.planning_date
                                                         AND instance_slot.planning_time = ps.planning_time
                                                         AND legacy_slot.congregation_id = ps.congregation_id
                                                         AND legacy_slot.planning_date = ps.planning_date
                                                         AND legacy_slot.planning_time = ps.planning_time
                                                         AND instance_slot.invitation_source_event_id = legacy_slot.id
                                             )
                                     )
        ) THEN
                RAISE EXCEPTION 'Cannot reconcile duplicate active planning slots with multiple event instances';
        END IF;
END $$;
"""

REWIRE_SERVICE_ASSIGNMENTS_SQL = RANKED_DUPLICATE_ACTIVE_SLOTS_CTE + """
UPDATE service_assignments sa
SET event_id = ranked.keep_id,
        planning_slot_id = ranked.keep_id
FROM ranked
WHERE COALESCE(sa.planning_slot_id, sa.event_id) = ranked.id
    AND ranked.id <> ranked.keep_id;
"""

REWIRE_CONGREGATION_INVITATIONS_SQL = RANKED_DUPLICATE_ACTIVE_SLOTS_CTE + """
UPDATE congregation_invitations ci
SET source_event_id = COALESCE(
        (SELECT ranked.keep_id FROM ranked WHERE ranked.id = ci.source_event_id),
        ci.source_event_id
    ),
    source_planning_slot_id = COALESCE(
        (SELECT ranked.keep_id FROM ranked WHERE ranked.id = ci.source_planning_slot_id),
        ci.source_planning_slot_id
    ),
    linked_event_id = COALESCE(
        (SELECT ranked.keep_id FROM ranked WHERE ranked.id = ci.linked_event_id),
        ci.linked_event_id
    )
WHERE EXISTS (
    SELECT 1
    FROM ranked
    WHERE ranked.id <> ranked.keep_id
      AND (
          ranked.id = ci.source_event_id
          OR ranked.id = ci.source_planning_slot_id
          OR ranked.id = ci.linked_event_id
      )
);
"""

REWIRE_INVITATION_COPIES_SQL = RANKED_DUPLICATE_ACTIVE_SLOTS_CTE + """
UPDATE planning_slots ps
SET invitation_source_event_id = ranked.keep_id
FROM ranked
WHERE ps.invitation_source_event_id = ranked.id
    AND ranked.id <> ranked.keep_id;
"""

REWIRE_OVERWRITE_REQUESTS_SQL = RANKED_DUPLICATE_ACTIVE_SLOTS_CTE + """
UPDATE invitation_overwrite_requests ior
SET source_event_id = COALESCE(
        (SELECT ranked.keep_id FROM ranked WHERE ranked.id = ior.source_event_id),
        ior.source_event_id
    ),
    target_event_id = COALESCE(
        (SELECT ranked.keep_id FROM ranked WHERE ranked.id = ior.target_event_id),
        ior.target_event_id
    )
WHERE EXISTS (
    SELECT 1
    FROM ranked
    WHERE ranked.id <> ranked.keep_id
      AND (ranked.id = ior.source_event_id OR ranked.id = ior.target_event_id)
);
"""

DELETE_DUPLICATE_LOSERS_SQL = RANKED_DUPLICATE_ACTIVE_SLOTS_CTE + """
    DELETE FROM planning_slots duplicate
    USING ranked
    WHERE duplicate.id = ranked.id
      AND ranked.id <> ranked.keep_id
    AND EXISTS (
        SELECT 1
        FROM planning_slots instance_slot
        JOIN event_instances instance ON instance.planning_slot_id = instance_slot.id
        JOIN planning_slots legacy_slot ON legacy_slot.id = duplicate.id
        WHERE instance_slot.id = ranked.keep_id
        AND instance_slot.invitation_source_event_id = legacy_slot.id
    )
            AND NOT EXISTS (
                    SELECT 1
                    FROM event_instances ei
                    WHERE ei.planning_slot_id = duplicate.id
            );
"""


def upgrade() -> None:
    op.execute(LOCK_RECONCILIATION_TABLES_SQL)
    op.execute(REJECT_AMBIGUOUS_DUPLICATES_SQL)
    op.execute(REWIRE_SERVICE_ASSIGNMENTS_SQL)
    op.execute(REWIRE_CONGREGATION_INVITATIONS_SQL)
    op.execute(REWIRE_INVITATION_COPIES_SQL)
    op.execute(REWIRE_OVERWRITE_REQUESTS_SQL)
    op.execute(DELETE_DUPLICATE_LOSERS_SQL)
    op.create_index(
        INDEX_NAME,
        "planning_slots",
        ["congregation_id", "planning_date", "planning_time"],
        unique=True,
        postgresql_where="congregation_id IS NOT NULL AND status = 'ACTIVE'",
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="planning_slots")
