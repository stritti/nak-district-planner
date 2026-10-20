# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Cross-congregation lookup of a person's other duties (step 2.2c)."""

from alembic import op
from app.adapters.db.migrations.duty_identity_schedule import FUNCTION_NAME, FUNCTION_SQL

revision = "20261019_duty_identity_schedule"
down_revision = "20261016_contract_export_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(FUNCTION_SQL)


def downgrade() -> None:
    op.execute(
        f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}(uuid, text, text, uuid, date, date)"
    )
