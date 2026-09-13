"""Merge app-role RLS chain with planning slot uniqueness index.

Revision ID: 5f4d3c2b1a09
Revises: 0016, 0ea121ae36ad
Create Date: 2026-09-13 22:15:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "5f4d3c2b1a09"
down_revision: str | tuple[str, str] | None = ("0016", "0ea121ae36ad")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
