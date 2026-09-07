"""apply tenant isolation RLS policies

Revision ID: 0014
Revises: change_applicability_to_text
Create Date: 2026-09-07 21:45:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.adapters.db.migrations.rls_policies import get_all_rls_sql, get_drop_rls_sql

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | None = "change_applicability_to_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize_sql(statement: str) -> str:
    """Return SQL without a trailing semicolon for Alembic execution."""
    return statement.strip().rstrip(";")


def upgrade() -> None:
    """Enable RLS and create tenant-isolation policies."""
    for statement in get_all_rls_sql():
        op.execute(_normalize_sql(statement))


def downgrade() -> None:
    """Drop tenant-isolation policies and disable RLS."""
    for statement in get_drop_rls_sql():
        op.execute(_normalize_sql(statement))
