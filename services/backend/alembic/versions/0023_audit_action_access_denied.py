"""Add ACCESS_DENIED to the audit action enum.

Denied requests (HTTP 403) are audited for every method, including reads, so
cross-tenant probing leaves a trace. They get their own action instead of
being recorded as a failed CREATE/UPDATE.

Revision ID: 0023
Revises: 0022
"""

from __future__ import annotations

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADD VALUE cannot be used in the transaction that adds it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'ACCESS_DENIED'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values; re-map the entries and keep the value.
    op.execute(
        "UPDATE audit_logs SET action = 'UPDATE', "
        "extra_metadata = coalesce(extra_metadata, '{}'::jsonb) || '{\"access_denied\": true}' "
        "WHERE action = 'ACCESS_DENIED'"
    )
