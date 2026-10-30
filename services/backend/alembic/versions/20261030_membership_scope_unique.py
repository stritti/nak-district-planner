# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""One membership per user and unit; administrators see the assignments they manage.

A user may hold memberships in several districts and congregations, but only
one role per unit. The old unique constraint included ``role`` and allowed a
VIEWER and a PLANNER row for the same user and unit. Steps, under a table lock:

1. Resolve duplicates per ``(user_sub, scope_type, scope_id)``: the row with
   the highest role (``PRIVILEGE_ORDER``) is kept, then the newest
   (``updated_at DESC``) and the lowest id. Effective access never shrinks,
   because RBAC and RLS already used the highest role. All other rows are
   copied to ``ARCHIVE_TABLE`` (owner-only) and deleted; the downgrade puts
   them back.
2. Replace ``uq_memberships_user_role_scope`` by ``uq_memberships_user_scope``,
   so upserts can rely on ``ON CONFLICT`` and concurrent assignments of the
   same unit cannot create a second row.
3. Extend the memberships SELECT policy by ``can_admin_membership``: an
   administrator sees the memberships of the units they may manage. This is
   needed for user administration and for ``INSERT ... ON CONFLICT DO UPDATE``,
   which PostgreSQL checks against the SELECT policy.
4. Move the INSERT policy's self-approval check into the SECURITY DEFINER
   helper ``is_self_approved_membership``. The inline subquery on
   ``leader_registrations`` (whose policies read ``memberships``) made every
   application-role INSERT into memberships fail with "infinite recursion
   detected in policy", including the approval of an already linked
   registration.

Revision ID: 20261030_membership_scope_unique
Revises: 20261022_leader_assignments
"""

from __future__ import annotations

import os

from alembic import op
from app.adapters.db.migrations.rls_policies import (
    SUPERADMIN_SQL,
    membership_row_read_sql,
    scoped_membership_admin_sql,
    self_approved_membership_insert_sql,
    self_approved_registration_insert_sql,
)
from app.domain.models.role import PRIVILEGE_ORDER

revision = "20261030_membership_scope_unique"
down_revision = "20261022_leader_assignments"
branch_labels = None
depends_on = None

OLD_CONSTRAINT = "uq_memberships_user_role_scope"
NEW_CONSTRAINT = "uq_memberships_user_scope"
ARCHIVE_TABLE = "membership_scope_duplicates"
POLICY = "memberships_tenant_isolation_policy"
INSERT_POLICY = "memberships_insert_policy"
HELPER_SIGNATURE = "is_self_approved_membership(TEXT, TEXT, UUID, TEXT)"

SELF_APPROVED_HELPER_SQL = """
CREATE OR REPLACE FUNCTION is_self_approved_membership(
    p_user_sub TEXT, p_scope_type TEXT, p_scope_id UUID, p_role TEXT
)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT p_user_sub = current_setting('app.current_user_sub', true)
       AND EXISTS (
           SELECT 1
           FROM leader_registrations lr
           WHERE lr.status = 'APPROVED'
             AND lr.user_sub = p_user_sub
             AND lr.assigned_scope_type = p_scope_type
             AND lr.assigned_scope_id = p_scope_id
             AND lr.assigned_role = p_role
       )
$$
"""

_ROLE_RANK = "\n".join(
    f"                       WHEN '{role.value}' THEN {rank}"
    for rank, role in enumerate(PRIVILEGE_ORDER)
)

RANKED_DUPLICATES_SQL = f"""
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY user_sub, scope_type, scope_id
               ORDER BY
                   CASE role
{_ROLE_RANK}
                       ELSE {len(PRIVILEGE_ORDER)}
                   END,
                   updated_at DESC,
                   id::text ASC
           ) AS rank
    FROM memberships
"""

ARCHIVE_DUPLICATES_SQL = f"""
CREATE TABLE IF NOT EXISTS {ARCHIVE_TABLE} AS
SELECT m.*, now() AS archived_at
FROM memberships m
JOIN ({RANKED_DUPLICATES_SQL}) ranked ON ranked.id = m.id
WHERE ranked.rank > 1;
"""

DELETE_DUPLICATES_SQL = f"""
DELETE FROM memberships m
USING ({RANKED_DUPLICATES_SQL}) ranked
WHERE m.id = ranked.id
  AND ranked.rank > 1;
"""

# No duplicates: no archive. Otherwise default privileges grant the app role
# access to the new table; take it away, so only the owner can read it.
LOCK_DOWN_ARCHIVE_SQL = f"""
DO $$
BEGIN
    IF to_regclass('{ARCHIVE_TABLE}') IS NULL THEN
        RETURN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM {ARCHIVE_TABLE}) THEN
        DROP TABLE {ARCHIVE_TABLE};
        RETURN;
    END IF;
    REVOKE ALL ON {ARCHIVE_TABLE} FROM PUBLIC;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :app_role) THEN
        EXECUTE format('REVOKE ALL ON {ARCHIVE_TABLE} FROM %I', :app_role);
    END IF;
    ALTER TABLE {ARCHIVE_TABLE} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {ARCHIVE_TABLE} FORCE ROW LEVEL SECURITY;
END
$$;
"""

RESTORE_DUPLICATES_SQL = f"""
DO $$
DECLARE
    cols text;
BEGIN
    IF to_regclass('{ARCHIVE_TABLE}') IS NULL THEN
        RETURN;
    END IF;
    SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position) INTO cols
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'memberships';
    EXECUTE format(
        'INSERT INTO memberships (%s) SELECT %s FROM {ARCHIVE_TABLE} ON CONFLICT (id) DO NOTHING',
        cols, cols
    );
    DROP TABLE {ARCHIVE_TABLE};
END
$$;
"""


def _app_role() -> str:
    return os.getenv("APP_DB_USER", "nak_app")


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _recreate_select_policy(using: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLICY} ON memberships")
    op.execute(f"CREATE POLICY {POLICY} ON memberships FOR SELECT USING {using}")  # nosec B608


def _recreate_insert_policy(self_insert: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS {INSERT_POLICY} ON memberships")
    op.execute(
        f"CREATE POLICY {INSERT_POLICY} ON memberships FOR INSERT "  # nosec B608
        f"WITH CHECK ({scoped_membership_admin_sql('memberships')} OR {self_insert})"
    )


def upgrade() -> None:
    op.execute("LOCK TABLE memberships IN SHARE ROW EXCLUSIVE MODE")
    op.execute(ARCHIVE_DUPLICATES_SQL)
    op.execute(LOCK_DOWN_ARCHIVE_SQL.replace(":app_role", _quote_literal(_app_role())))
    op.execute(DELETE_DUPLICATES_SQL)
    op.drop_constraint(OLD_CONSTRAINT, "memberships", type_="unique")
    op.create_unique_constraint(
        NEW_CONSTRAINT, "memberships", ["user_sub", "scope_type", "scope_id"]
    )
    _recreate_select_policy(membership_row_read_sql())
    op.execute(SELF_APPROVED_HELPER_SQL)
    op.execute(f"REVOKE ALL ON FUNCTION {HELPER_SIGNATURE} FROM PUBLIC")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {_quote_literal(_app_role())}) THEN
                EXECUTE format('GRANT EXECUTE ON FUNCTION {HELPER_SIGNATURE} TO %I', {_quote_literal(_app_role())});
            END IF;
        END $$;
        """
    )
    _recreate_insert_policy(self_approved_membership_insert_sql("memberships"))


def downgrade() -> None:
    _recreate_insert_policy(self_approved_registration_insert_sql("memberships"))
    op.execute(f"DROP FUNCTION IF EXISTS {HELPER_SIGNATURE}")
    _recreate_select_policy(
        f"({SUPERADMIN_SQL} OR memberships.user_sub = current_setting('app.current_user_sub', true))"
    )
    op.drop_constraint(NEW_CONSTRAINT, "memberships", type_="unique")
    op.create_unique_constraint(
        OLD_CONSTRAINT, "memberships", ["user_sub", "role", "scope_type", "scope_id"]
    )
    op.execute(RESTORE_DUPLICATES_SQL)
