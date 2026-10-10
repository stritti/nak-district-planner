# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Release imported holiday slots (category Feiertag) to all congregations.

Holidays are reference data; since issue #466 district slots are only
distributed to congregations when approval_status=CONFIRMED. Imported holidays
used to have no approval status and would otherwise vanish from congregation
views. District holidays also get the ``'all'`` applicability sentinel, so
holidays imported after a congregation was created reach it as well. New
imports set both in feiertage_service.

Downgrade is a deliberate no-op: the previous approval and applicability values
are not recorded, and the new values are valid under the old schema.

Revision ID: 20261007_confirm_holidays
Revises: 20261007_assignment_unique
"""

from __future__ import annotations

from alembic import op

revision = "20261007_confirm_holidays"
down_revision = "20261007_assignment_unique"
branch_labels = None
depends_on = None


# Rows the importers created: district-level, midnight, no approval status (the
# importers never set one; every other slot source does). Holiday slots a planner
# approved, planned or owns per congregation are left as they are. Applicability
# goes first, while approval_status still identifies the imported rows; their
# congregation ids were appended by reference_feiertage_for_congregation.
_IMPORTED_HOLIDAY = (
    "category = 'Feiertag' AND congregation_id IS NULL "
    "AND planning_time = '00:00:00' AND approval_status IS NULL"
)


def upgrade() -> None:
    op.execute(
        "UPDATE planning_slots SET applicability = ARRAY['all']::varchar[], updated_at = now() "
        f"WHERE {_IMPORTED_HOLIDAY} AND NOT ('all' = ANY(applicability))"
    )
    op.execute(
        "UPDATE planning_slots SET approval_status = 'CONFIRMED', updated_at = now() "
        f"WHERE {_IMPORTED_HOLIDAY}"
    )


def downgrade() -> None:
    """No-op: previous approval values are not recoverable (see module docstring)."""
