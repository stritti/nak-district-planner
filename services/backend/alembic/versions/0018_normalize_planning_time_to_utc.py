# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Normalize planning_slots.planning_time to UTC

Before this change, the slot generators stored planning_time as local
Europe/Berlin wall-clock time (draft service generation, planning series),
while all readers (matrix, sync, deviation, events API) interpreted it as
UTC. Slots migrated from the legacy events table (migration 0125) already
stored UTC, and invitation copies mirrored their (mislabeled) source.

Normalization rules (applied in order):

1. Series-generated instances (and invitation copies of series slots) were
   constructed as combine(date, local_time) labeled UTC — i.e. off by the
   Berlin UTC offset. Instances still exactly matching that mislabeled
   construction are shifted to the true UTC instant (DST-aware per date).
   Instances already edited or externally synced do not match and are left
   untouched.

2. Series-generated slots (series_id IS NOT NULL) convert their local
   wall-clock planning_time to the UTC instant (DST-aware per date).

3. Every slot with a non-deviating event_instance is aligned to the
   instance's authoritative UTC start: fixes draft-generated slots (whose
   instances were always true UTC) and invitation copies (mirroring rule 1),
   and is a no-op for already-aligned rows.

4. Draft-generated slots with a deviating instance (invitation_source_event_id
   IS NULL, category 'Gottesdienst') convert local wall-clock to UTC like
   series slots; their deviating instance is authoritative and untouched.

All-day markers (Feiertage / kirchliche Festtage: planning_time 00:00, no
instance, no series) are UTC-compatible and remain unchanged.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SHIFT_SERIES_LIKE_INSTANCES_SQL = """
UPDATE event_instances ei
SET actual_start_at = ei.actual_start_at + (
        ((ps.planning_date::timestamp + ps.planning_time)
            AT TIME ZONE 'Europe/Berlin' AT TIME ZONE 'UTC')
        - (ps.planning_date::timestamp + ps.planning_time)
    ),
    actual_end_at = ei.actual_end_at + (
        ((ps.planning_date::timestamp + ps.planning_time)
            AT TIME ZONE 'Europe/Berlin' AT TIME ZONE 'UTC')
        - (ps.planning_date::timestamp + ps.planning_time)
    )
FROM planning_slots ps
WHERE ps.id = ei.planning_slot_id
  AND (
        ps.series_id IS NOT NULL
        OR EXISTS (
            SELECT 1 FROM planning_slots src
            WHERE src.id = ps.invitation_source_event_id
              AND src.series_id IS NOT NULL
        )
      )
  AND ei.actual_start_at = (ps.planning_date::timestamp + ps.planning_time)
      AT TIME ZONE 'UTC';
"""

_CONVERT_SERIES_SLOTS_SQL = """
UPDATE planning_slots ps
SET planning_date = ((ps.planning_date::timestamp + ps.planning_time)
        AT TIME ZONE 'Europe/Berlin' AT TIME ZONE 'UTC')::date,
    planning_time = ((ps.planning_date::timestamp + ps.planning_time)
        AT TIME ZONE 'Europe/Berlin' AT TIME ZONE 'UTC')::time
WHERE ps.series_id IS NOT NULL;
"""

_ALIGN_NON_DEVIATING_SLOTS_SQL = """
UPDATE planning_slots ps
SET planning_date = (ei.actual_start_at AT TIME ZONE 'UTC')::date,
    planning_time = (ei.actual_start_at AT TIME ZONE 'UTC')::time
FROM event_instances ei
WHERE ei.planning_slot_id = ps.id
  AND ei.deviation_flag = FALSE
  AND (
        ps.planning_date <> (ei.actual_start_at AT TIME ZONE 'UTC')::date
        OR ps.planning_time <> (ei.actual_start_at AT TIME ZONE 'UTC')::time
      );
"""

_CONVERT_DEVIATING_DRAFT_SLOTS_SQL = """
UPDATE planning_slots ps
SET planning_date = ((ps.planning_date::timestamp + ps.planning_time)
        AT TIME ZONE 'Europe/Berlin' AT TIME ZONE 'UTC')::date,
    planning_time = ((ps.planning_date::timestamp + ps.planning_time)
        AT TIME ZONE 'Europe/Berlin' AT TIME ZONE 'UTC')::time
WHERE ps.series_id IS NULL
  AND ps.invitation_source_event_id IS NULL
  AND ps.category = 'Gottesdienst'
  AND EXISTS (
        SELECT 1 FROM event_instances ei
        WHERE ei.planning_slot_id = ps.id
          AND ei.deviation_flag = TRUE
      );
"""

_REVERT_SERIES_INSTANCES_SQL = """
UPDATE event_instances ei
SET actual_start_at = (ei.actual_start_at AT TIME ZONE 'Europe/Berlin')
        AT TIME ZONE 'UTC',
    actual_end_at = (ei.actual_end_at AT TIME ZONE 'Europe/Berlin')
        AT TIME ZONE 'UTC'
FROM planning_slots ps
WHERE ps.id = ei.planning_slot_id
  AND ps.series_id IS NOT NULL
  AND ei.actual_start_at = (ps.planning_date::timestamp + ps.planning_time)
      AT TIME ZONE 'UTC';
"""

_REVERT_SERIES_SLOTS_SQL = """
UPDATE planning_slots ps
SET planning_date = ((ps.planning_date::timestamp + ps.planning_time)
        AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Berlin')::date,
    planning_time = ((ps.planning_date::timestamp + ps.planning_time)
        AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Berlin')::time
WHERE ps.series_id IS NOT NULL;
"""


def upgrade() -> None:
    op.execute(_SHIFT_SERIES_LIKE_INSTANCES_SQL)
    op.execute(_CONVERT_SERIES_SLOTS_SQL)
    op.execute(_ALIGN_NON_DEVIATING_SLOTS_SQL)
    op.execute(_CONVERT_DEVIATING_DRAFT_SLOTS_SQL)


def downgrade() -> None:
    # The series conversion (slots + instances) is inverted exactly. The
    # alignment of draft-generated slots cannot be inverted because local
    # and UTC rows are indistinguishable afterwards; restoring those
    # requires a backup taken before the upgrade.
    op.execute(_REVERT_SERIES_INSTANCES_SQL)
    op.execute(_REVERT_SERIES_SLOTS_SQL)
