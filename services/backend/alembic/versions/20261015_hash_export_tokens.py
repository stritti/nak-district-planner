# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Expand phase: add a hash column for export tokens.

Expand/contract rollout for storing export tokens hashed: this revision
only adds the nullable ``token_hash`` column and backfills it. The
plaintext ``token`` column stays in place so an application rollback to
a hash-unaware release keeps every existing ICS subscription working.
A later contract revision removes the plaintext column once the rollback
window has closed.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261015_hash_export_tokens"
down_revision = "20261013_event_duties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "export_tokens",
        sa.Column("token_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_export_tokens_token_hash", "export_tokens", ["token_hash"], unique=True
    )
    op.execute(
        """UPDATE export_tokens
        SET token_hash = encode(sha256(token::bytea), 'hex')
        WHERE token_hash IS NULL"""
    )


def downgrade() -> None:
    op.drop_index("ix_export_tokens_token_hash", table_name="export_tokens")
    op.drop_column("export_tokens", "token_hash")

