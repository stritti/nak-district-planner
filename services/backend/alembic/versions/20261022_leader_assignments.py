# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Leader assignments replace the home congregation and special role (step 4).

One revision, one transaction: create ``leader_assignments``, backfill one home assignment
per leader from ``(congregation_id, special_role)``, swap the leader policies that read
``leaders.congregation_id`` for assignment-based ones, drop both columns. The downgrade
restores both columns from the home assignment; further assignments are lost.
"""

import os

import sqlalchemy as sa

from alembic import op
from app.adapters.db.migrations import leader_assignment_rls as rls

revision = "20261022_leader_assignments"
down_revision = "20261021_duty_identity_interval"
branch_labels = None
depends_on = None


def _app_role() -> str:
    return os.getenv("APP_DB_USER", "nak_app").replace('"', '""')


def upgrade() -> None:
    op.create_unique_constraint("uq_leaders_id_district", "leaders", ["id", "district_id"])
    op.create_table(
        "leader_assignments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("leader_id", sa.UUID(), nullable=False),
        sa.Column("district_id", sa.UUID(), nullable=False),
        sa.Column(
            "congregation_id", sa.UUID(), sa.ForeignKey("congregations.id", ondelete="CASCADE")
        ),
        sa.Column("role", sa.String(50)),
        sa.Column("is_home", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["leader_id", "district_id"],
            ["leaders.id", "leaders.district_id"],
            ondelete="CASCADE",
            name="fk_leader_assignments_leader_district",
        ),
    )
    op.create_index("ix_leader_assignments_leader_id", "leader_assignments", ["leader_id"])
    op.create_index(
        "ix_leader_assignments_congregation_id", "leader_assignments", ["congregation_id"]
    )
    op.create_index(
        "uq_leader_assignments_leader_congregation",
        "leader_assignments",
        ["leader_id", "congregation_id"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "uq_leader_assignments_home",
        "leader_assignments",
        ["leader_id"],
        unique=True,
        postgresql_where=sa.text("is_home"),
    )
    op.execute(
        """INSERT INTO leader_assignments
             (id, leader_id, district_id, congregation_id, role, is_home, created_at, updated_at)
           SELECT gen_random_uuid(), id, district_id, congregation_id, special_role, true, now(), now()
           FROM leaders"""
    )
    op.execute("ALTER TABLE leader_assignments ENABLE ROW LEVEL SECURITY")
    op.execute(
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON leader_assignments TO "{_app_role()}"'
    )
    for name in rls.ASSIGNMENT_POLICIES:
        op.execute(rls.assignment_policy_sql()[name])
    for statement in rls.FUNCTIONS:
        op.execute(statement)
    for name in rls.LEADER_POLICIES:
        op.execute(f"DROP POLICY {name} ON leaders")
    op.drop_column("leaders", "congregation_id")
    op.drop_column("leaders", "special_role")
    for statement in rls.leader_policy_sql().values():
        op.execute(statement)


def downgrade() -> None:
    op.add_column(
        "leaders",
        sa.Column(
            "congregation_id", sa.UUID(), sa.ForeignKey("congregations.id", ondelete="SET NULL")
        ),
    )
    op.add_column("leaders", sa.Column("special_role", sa.String(50)))
    op.execute(
        """UPDATE leaders l SET congregation_id = la.congregation_id, special_role = la.role
           FROM leader_assignments la WHERE la.leader_id = l.id AND la.is_home"""
    )
    for name in rls.LEADER_POLICIES:
        op.execute(f"DROP POLICY {name} ON leaders")
    for statement in rls.legacy_policy_sql().values():
        op.execute(statement)
    for function in rls.FUNCTION_NAMES:
        op.execute(f"DROP FUNCTION {function}")
    op.drop_table("leader_assignments")
    op.drop_constraint("uq_leaders_id_district", "leaders", type_="unique")
