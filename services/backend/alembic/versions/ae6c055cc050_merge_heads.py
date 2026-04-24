"""merge heads

Revision ID: ae6c055cc050
Revises: 0010_leader_registrations, 4c9a2d7e8f10
Create Date: 2026-04-07 11:17:45.652612

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "ae6c055cc050"
down_revision: str | None = ("0010_leader_registrations", "4c9a2d7e8f10")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
