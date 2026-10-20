# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Duties may reference a leader as a third identity (step 2.2b)."""

import sqlalchemy as sa

from alembic import op
from app.adapters.db.migrations.duty_identity_schedule import (
    FUNCTION_NAME,
)
from app.adapters.db.migrations.duty_identity_schedule import (
    FUNCTION_SQL as FUNCTION_SQL_V1,
)
from app.adapters.db.migrations.duty_identity_schedule_v2 import FUNCTION_SQL, V1_SIGNATURE

revision = "20261020_duty_leader_identity"
down_revision = "20261019_duty_identity_schedule"
branch_labels = None
depends_on = None

_OLD_CHECK = (
    "(linked_user_sub IS NOT NULL AND normalized_name IS NULL) OR "
    "(linked_user_sub IS NULL AND normalized_name IS NOT NULL)"
)
_NEW_CHECK = (
    "(linked_user_sub IS NOT NULL)::int + (normalized_name IS NOT NULL)::int "
    "+ (leader_id IS NOT NULL)::int = 1"
)


def upgrade() -> None:
    op.add_column(
        "event_duty_assignments",
        sa.Column("leader_id", sa.UUID(), sa.ForeignKey("leaders.id"), nullable=True),
    )
    op.drop_constraint("ck_duty_assignment_identity", "event_duty_assignments", type_="check")
    op.create_check_constraint("ck_duty_assignment_identity", "event_duty_assignments", _NEW_CHECK)
    op.create_index(
        "uq_duty_assignment_leader",
        "event_duty_assignments",
        ["planning_slot_id", "duty_category_id", "leader_id"],
        unique=True,
        postgresql_where=sa.text("leader_id IS NOT NULL"),
    )
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}({V1_SIGNATURE})")
    op.execute(FUNCTION_SQL)


def downgrade() -> None:
    op.execute(
        f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}(uuid, text, text, uuid, uuid, date, date)"
    )
    op.execute(FUNCTION_SQL_V1)
    # Leader-identified duties have no name or account to fall back to.
    op.execute("DELETE FROM event_duty_assignments WHERE leader_id IS NOT NULL")
    op.drop_index("uq_duty_assignment_leader", table_name="event_duty_assignments")
    op.drop_constraint("ck_duty_assignment_identity", "event_duty_assignments", type_="check")
    op.create_check_constraint("ck_duty_assignment_identity", "event_duty_assignments", _OLD_CHECK)
    op.drop_column("event_duty_assignments", "leader_id")
