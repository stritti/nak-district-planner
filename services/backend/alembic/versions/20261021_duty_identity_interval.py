# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Duty identity lookup v4: exact event intervals and symmetric name matching."""

from alembic import op
from app.adapters.db.migrations.duty_identity_schedule_v3 import FUNCTION_SQL as FUNCTION_SQL_V3
from app.adapters.db.migrations.duty_identity_schedule_v3 import SIGNATURE as SIGNATURE_V3
from app.adapters.db.migrations.duty_identity_schedule_v4 import (
    FUNCTION_NAME,
    FUNCTION_SQL,
    SIGNATURE,
)

revision = "20261021_duty_identity_interval"
down_revision = "20261020_duty_account_leaders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}({SIGNATURE_V3})")
    op.execute(FUNCTION_SQL)


def downgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}({SIGNATURE})")
    op.execute(FUNCTION_SQL_V3)
