"""change applicability from UUID[] to TEXT[]

Revision ID: change_applicability_to_text
Revises: e5a2b3c4d5f0
Create Date: 2026-08-12 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "change_applicability_to_text"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Change applicability column from UUID[] to TEXT[]
    # PostgreSQL can cast UUID[] to TEXT[] directly
    op.alter_column(
        "planning_slots",
        "applicability",
        existing_type=sa.ARRAY(sa.UUID(as_uuid=True)),
        type_=sa.ARRAY(sa.String()),
        existing_nullable=False,
        postgresql_using="applicability::text[]",
    )


def downgrade() -> None:
    # Change back from TEXT[] to UUID[]
    # Filter out "all" sentinel before casting to UUID[]
    op.alter_column(
        "planning_slots",
        "applicability",
        existing_type=sa.ARRAY(sa.String()),
        type_=sa.ARRAY(sa.UUID(as_uuid=True)),
        existing_nullable=False,
        postgresql_using="array_remove(applicability::text[], 'all')::uuid[]",
    )
