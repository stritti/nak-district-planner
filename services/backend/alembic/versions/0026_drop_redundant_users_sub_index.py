# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Drop ix_users_sub, which duplicates the index behind uq_users_sub.

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_users_sub", table_name="users")


def downgrade() -> None:
    op.create_index("ix_users_sub", "users", ["sub"])
