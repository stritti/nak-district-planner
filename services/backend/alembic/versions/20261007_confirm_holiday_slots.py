"""Release imported holiday slots (category Feiertag) as CONFIRMED.

Holidays are reference data; since issue #466 district slots are only
distributed to congregations when approval_status=CONFIRMED. Imported holidays
used to have no approval status and would otherwise vanish from congregation
views. New imports set CONFIRMED in feiertage_service.

Downgrade is a deliberate no-op: the previous (NULL/PLANNED) values are not
recorded, and CONFIRMED holidays are valid under the old schema.

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


def downgrade() -> None:
    """No-op: previous approval values are not recoverable (see module docstring)."""
