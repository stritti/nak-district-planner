# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Track every calendar synchronization attempt.

Revision ID: 20261011_sync_attempt
Revises: 20261010_event_release
"""
from alembic import op
import sqlalchemy as sa

revision = "20261011_sync_attempt"
down_revision = "20261010_event_release"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calendar_integrations",
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calendar_integrations", "last_attempt_at")
