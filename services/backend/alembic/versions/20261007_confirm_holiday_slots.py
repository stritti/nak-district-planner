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
Revises: 20261007_celery_tables
"""

from __future__ import annotations

from alembic import op

revision = "20261007_confirm_holidays"
down_revision = "20261007_celery_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE planning_slots SET approval_status = 'CONFIRMED', updated_at = now() "
        "WHERE category = 'Feiertag' "
        "AND approval_status IS DISTINCT FROM 'CONFIRMED'"
    )
    op.execute(
        "UPDATE planning_slots SET applicability = ARRAY['all']::varchar[], updated_at = now() "
        "WHERE category = 'Feiertag' AND congregation_id IS NULL "
        "AND NOT ('all' = ANY(applicability))"
    )


def downgrade() -> None:
    """No-op: previous approval values are not recoverable (see module docstring)."""
