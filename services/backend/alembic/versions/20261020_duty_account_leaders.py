# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""The duty identity lookup matches an account's linked leaders (version 3)."""

from alembic import op
from app.adapters.db.migrations.duty_identity_schedule_v2 import FUNCTION_SQL as FUNCTION_SQL_V2
from app.adapters.db.migrations.duty_identity_schedule_v3 import (
    FUNCTION_NAME,
    FUNCTION_SQL,
    SIGNATURE,
)

revision = "20261020_duty_account_leaders"
down_revision = "20261020_duty_leader_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}({SIGNATURE})")
    op.execute(FUNCTION_SQL)


def downgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}({SIGNATURE})")
    op.execute(FUNCTION_SQL_V2)
