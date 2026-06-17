"""merge planning model with main chain

Revision ID: ed967c737376
Revises: 0011_planning_model_foundation, e4b2a9d7f110
Create Date: 2026-06-10 13:53:19.975904

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ed967c737376'
down_revision: Union[str, None] = ('0011_planning_model_foundation', 'e4b2a9d7f110')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
