# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Hash existing plaintext export tokens at rest.

New tokens are hashed by the application. This migration converts legacy
plaintext rows so a database leak never contains usable feed credentials.
"""

from alembic import op

revision = "20261015_hash_export_tokens"
down_revision = "20261013_event_duties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """UPDATE export_tokens
        SET token = encode(sha256(token::bytea), 'hex')
        WHERE token !~ '^[0-9a-f]{64}$'"""
    )


def downgrade() -> None:
    """Hashing is one-way; the plaintext secret cannot be restored."""

