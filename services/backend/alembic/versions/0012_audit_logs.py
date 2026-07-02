"""create audit_logs table for security audit logging

Revision ID: 0012
Revises: ed967c737376
Create Date: 2026-06-20 18:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | None = "ed967c737376"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the audit_logs table
    # Enum types (auditaction, auditstatus) are created automatically
    # by the column definitions below.
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("user_sub", sa.String(512), nullable=True, index=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("user_roles", JSONB, nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT",
                "EXPORT", "IMPORT", "BULK_OPERATION",
                name="auditaction",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("resource_type", sa.String(100), nullable=False, index=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("district_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("congregation_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column("old_values", JSONB, nullable=True),
        sa.Column("new_values", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True, index=True),
        sa.Column(
            "status",
            sa.Enum(
                "SUCCESS", "FAILED",
                name="auditstatus",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("extra_metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    sa.Enum(name="auditaction").drop(op.get_bind())
    sa.Enum(name="auditstatus").drop(op.get_bind())
