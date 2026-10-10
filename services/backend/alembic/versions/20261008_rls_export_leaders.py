# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Let export tokens read the leaders their feed names.

Issue #466 / PR #485: the leaders SELECT policy only allowed user memberships,
so unauthenticated ICS exports could not resolve leader_id-only assignments
under the NOBYPASSRLS application role: personal and INTERNAL feeds lost the
leader name, and leader renames could not advance the event revision. A
personal leader token may now read its own leader, an INTERNAL token the
leaders of its district; PUBLIC tokens anonymize names and read none.
Downgrade restores the previous policy.

Revision ID: 20261008_rls_export_leaders
Revises: 20261008_rls_distributed
"""

from __future__ import annotations

from alembic import op
from app.adapters.db.migrations.rls_policies import leader_read_sql, leader_row_read_sql

revision = "20261008_rls_export_leaders"
down_revision = "20261008_rls_distributed"
branch_labels = None
depends_on = None

_POLICY = "leaders_tenant_isolation_policy"


def _recreate(using: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS {_POLICY} ON leaders")
    op.execute(f"CREATE POLICY {_POLICY} ON leaders FOR SELECT USING {using}")  # nosec B608


def upgrade() -> None:
    _recreate(leader_row_read_sql())


def downgrade() -> None:
    _recreate(leader_read_sql())
