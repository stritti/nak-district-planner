# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Hash existing plaintext export tokens at rest.

New tokens are hashed by the application. This migration converts legacy
plaintext rows so a database leak never contains usable feed credentials.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261015_hash_export_tokens"
down_revision = "20261013_event_duties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """UPDATE export_tokens
        SET token = 'sha256:' || encode(sha256(token::bytea), 'hex')
        WHERE token NOT LIKE 'sha256:%'"""
    )
    op.alter_column(
        "export_tokens",
        "token",
        existing_type=sa.String(64),
        type_=sa.String(128),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "export_tokens",
        "token",
        existing_type=sa.String(128),
        type_=sa.String(64),
        existing_nullable=False,
    )
