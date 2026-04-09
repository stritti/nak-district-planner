"""Add IDP provisioning fields to leader registrations.

Revision ID: e4b2a9d7f110
Revises: d2c4f8a9b1e0
Create Date: 2026-04-09 18:15:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4b2a9d7f110"
down_revision: Union[str, None] = "d2c4f8a9b1e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leader_registrations",
        sa.Column("idp_provision_status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "leader_registrations",
        sa.Column("idp_provision_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "leader_registrations",
        sa.Column("idp_provisioned_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leader_registrations", "idp_provisioned_at")
    op.drop_column("leader_registrations", "idp_provision_error")
    op.drop_column("leader_registrations", "idp_provision_status")
