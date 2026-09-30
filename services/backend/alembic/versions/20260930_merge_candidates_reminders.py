"""Merge the parallel heads of #376 (0021) and #378 (20260930_reminder).

Revision ID: 20260930_merge_heads
Revises: 0021, 20260930_reminder

Kept schema-free so that ``alembic downgrade -1`` from the following revision
stays unambiguous. If either branch is rebased onto a newer head before this
lands, adjust ``down_revision`` accordingly.
"""

from __future__ import annotations

revision = "20260930_merge_heads"
down_revision = ("0021", "20260930_reminder")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
