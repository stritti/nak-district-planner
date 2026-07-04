"""merge 0125 (with e5a2 dependency) and 0012 branches

Revision ID: ae6c055cc051
Revises: 0012, 0125
Create Date: 2026-06-29 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "ae6c055cc051"
down_revision: str | None = ("0012", "0125")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
