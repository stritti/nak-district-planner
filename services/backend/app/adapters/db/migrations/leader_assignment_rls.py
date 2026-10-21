# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Row-level security for ``leader_assignments`` and the leader policies built on it.

A leader used to carry ``leaders.congregation_id``. With several assignments per leader
(step 4 of ``person-identity-and-conflicts``) visibility and write rights follow the
assignments:

* a leader is visible to the district and to the members of **every** assigned congregation
  (a leader without any assignment is visible to the district level only; a congregation
  planner may insert the leader row, because the assignment follows in the same transaction,
  and the ORM insert does not read the row back);
* district planners manage all assignments, a congregation planner only the assignment of
  their own congregation (the write policy checks ``leader_assignments.congregation_id``).

``leader_assignments`` carries ``district_id`` itself so that its policies never read
``leaders`` (no policy recursion). The legacy policies are kept verbatim for the downgrade
(taken from ``pg_policies`` before this revision; ``test_leader_assignment_migration``
compares them after a round trip).
"""

from app.adapters.db.migrations.rls_policies import (
    SUPERADMIN_SQL,
    congregation_membership_sql,
    congregation_write_membership_sql,
    district_membership_sql,
    district_write_membership_sql,
)
from app.domain.models.role import Role, roles_at_least_sql

TABLE = "leader_assignments"
LEADER_POLICIES = (
    "leaders_tenant_isolation_policy",
    "leaders_insert_policy",
    "leaders_update_policy",
    "leaders_delete_policy",
)
ASSIGNMENT_POLICIES = (
    "leader_assignments_select",
    "leader_assignments_insert",
    "leader_assignments_update",
    "leader_assignments_delete",
)

_TOKEN = "et.token_hash = encode(sha256(current_setting('app.current_export_token', true)::bytea), 'hex')"
_USER = "current_setting('app.current_user_sub', true)"

# Legacy definitions of the four leader policies (pg_policies text, verbatim).
LEGACY_LEADER_POLICIES = {
    'leaders_delete_policy': (
        'DELETE',
        "((EXISTS ( SELECT 1    FROM users   WHERE (((users.sub)::text = current_setting('app.current_user_sub'::text, true)) AND (users.is_superadmin = true)))) OR (current_setting('app.is_system_worker'::text, true) = 'true'::text) OR (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'DISTRICT'::text) AND (m.scope_id = leaders.district_id) AND ((m.role)::text = ANY ((ARRAY['DISTRICT_ADMIN'::character varying, 'CONGREGATION_ADMIN'::character varying, 'PLANNER'::character varying])::text[]))))) OR ((congregation_id IS NOT NULL) AND (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'CONGREGATION'::text) AND (m.scope_id = leaders.congregation_id) AND ((m.role)::text = ANY ((ARRAY['DISTRICT_ADMIN'::character varying, 'CONGREGATION_ADMIN'::character varying, 'PLANNER'::character varying])::text[])))))))",
        '',
    ),
    'leaders_insert_policy': (
        'INSERT',
        '',
        "((EXISTS ( SELECT 1    FROM users   WHERE (((users.sub)::text = current_setting('app.current_user_sub'::text, true)) AND (users.is_superadmin = true)))) OR (current_setting('app.is_system_worker'::text, true) = 'true'::text) OR (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'DISTRICT'::text) AND (m.scope_id = leaders.district_id) AND ((m.role)::text = ANY ((ARRAY['DISTRICT_ADMIN'::character varying, 'CONGREGATION_ADMIN'::character varying, 'PLANNER'::character varying])::text[]))))) OR ((congregation_id IS NOT NULL) AND (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'CONGREGATION'::text) AND (m.scope_id = leaders.congregation_id) AND ((m.role)::text = ANY ((ARRAY['DISTRICT_ADMIN'::character varying, 'CONGREGATION_ADMIN'::character varying, 'PLANNER'::character varying])::text[])))))))",
    ),
    'leaders_tenant_isolation_policy': (
        'SELECT',
        "((EXISTS ( SELECT 1    FROM users   WHERE (((users.sub)::text = current_setting('app.current_user_sub'::text, true)) AND (users.is_superadmin = true)))) OR (current_setting('app.is_system_worker'::text, true) = 'true'::text) OR (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'DISTRICT'::text) AND (m.scope_id = leaders.district_id)))) OR ((congregation_id IS NOT NULL) AND (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'CONGREGATION'::text) AND (m.scope_id = leaders.congregation_id))))) OR (EXISTS ( SELECT 1    FROM export_tokens et   WHERE (((et.token_hash)::text = encode(sha256((current_setting('app.current_export_token'::text, true))::bytea), 'hex'::text)) AND (et.district_id = leaders.district_id) AND (((et.subject_sub IS NULL) AND ((et.leader_id = leaders.id) OR ((et.leader_id IS NULL) AND (et.token_type = 'INTERNAL'::tokentype)))) OR (((et.subject_sub)::text = (leaders.user_sub)::text) AND duty_subject_scope((et.subject_sub)::text, leaders.district_id, leaders.congregation_id)))))))",
        '',
    ),
    'leaders_update_policy': (
        'UPDATE',
        "((EXISTS ( SELECT 1    FROM users   WHERE (((users.sub)::text = current_setting('app.current_user_sub'::text, true)) AND (users.is_superadmin = true)))) OR (current_setting('app.is_system_worker'::text, true) = 'true'::text) OR (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'DISTRICT'::text) AND (m.scope_id = leaders.district_id)))) OR ((congregation_id IS NOT NULL) AND (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'CONGREGATION'::text) AND (m.scope_id = leaders.congregation_id))))) OR (EXISTS ( SELECT 1    FROM export_tokens et   WHERE (((et.token_hash)::text = encode(sha256((current_setting('app.current_export_token'::text, true))::bytea), 'hex'::text)) AND (et.district_id = leaders.district_id) AND ((et.congregation_id IS NULL) OR (et.congregation_id = leaders.congregation_id))))))",
        "((EXISTS ( SELECT 1    FROM users   WHERE (((users.sub)::text = current_setting('app.current_user_sub'::text, true)) AND (users.is_superadmin = true)))) OR (current_setting('app.is_system_worker'::text, true) = 'true'::text) OR (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'DISTRICT'::text) AND (m.scope_id = leaders.district_id) AND ((m.role)::text = ANY ((ARRAY['DISTRICT_ADMIN'::character varying, 'CONGREGATION_ADMIN'::character varying, 'PLANNER'::character varying])::text[]))))) OR ((congregation_id IS NOT NULL) AND (EXISTS ( SELECT 1    FROM memberships m   WHERE (((m.user_sub)::text = current_setting('app.current_user_sub'::text, true)) AND ((m.scope_type)::text = 'CONGREGATION'::text) AND (m.scope_id = leaders.congregation_id) AND ((m.role)::text = ANY ((ARRAY['DISTRICT_ADMIN'::character varying, 'CONGREGATION_ADMIN'::character varying, 'PLANNER'::character varying])::text[])))))))",
    ),
}


def _assigned_congregation_membership(roles: str | None = None) -> str:
    """The caller is a member of a congregation the leader (``leaders``) is assigned to."""
    role_filter = f"AND m.role IN ({roles})" if roles else ""
    return f"""EXISTS (
        SELECT 1 FROM leader_assignments la
        JOIN memberships m ON m.scope_type = 'CONGREGATION' AND m.scope_id = la.congregation_id
        WHERE la.leader_id = leaders.id AND m.user_sub = {_USER} {role_filter})"""


def _leader_export_token_read() -> str:
    """Export tokens read the leaders their feed names (unchanged semantics, per assignment)."""
    return f"""EXISTS (
        SELECT 1 FROM export_tokens et
        WHERE {_TOKEN} AND et.district_id = leaders.district_id
          AND (
            (et.subject_sub IS NULL AND (et.leader_id = leaders.id
              OR (et.leader_id IS NULL AND et.token_type = 'INTERNAL')))
            OR (et.subject_sub = leaders.user_sub AND EXISTS (
              SELECT 1 FROM leader_assignments la WHERE la.leader_id = leaders.id
                AND duty_subject_scope(et.subject_sub, leaders.district_id, la.congregation_id)))))"""


def _leader_export_token_update() -> str:
    return f"""EXISTS (
        SELECT 1 FROM export_tokens et
        WHERE {_TOKEN} AND et.district_id = leaders.district_id
          AND (et.congregation_id IS NULL OR EXISTS (
            SELECT 1 FROM leader_assignments la
            WHERE la.leader_id = leaders.id AND la.congregation_id = et.congregation_id)))"""


def _leader_write_scope() -> str:
    return f"""({SUPERADMIN_SQL} OR {district_write_membership_sql("leaders")}
        OR {_assigned_congregation_membership(roles_at_least_sql(Role.PLANNER))})"""


def leader_policy_sql() -> dict[str, str]:
    """``CREATE POLICY`` statements of the four leader policies on ``leader_assignments``."""
    read = f"""({SUPERADMIN_SQL} OR {district_membership_sql("leaders")}
        OR {_assigned_congregation_membership()}
        OR {_leader_export_token_read()})"""
    insert_check = f"""({SUPERADMIN_SQL} OR {district_write_membership_sql("leaders")}
        OR EXISTS (
          SELECT 1 FROM memberships m JOIN congregations c ON c.id = m.scope_id
          WHERE m.user_sub = {_USER} AND m.scope_type = 'CONGREGATION'
            AND c.district_id = leaders.district_id
            AND m.role IN ({roles_at_least_sql(Role.PLANNER)})))"""
    update_using = f"""({SUPERADMIN_SQL} OR {district_membership_sql("leaders")}
        OR {_assigned_congregation_membership()}
        OR {_leader_export_token_update()})"""
    return {
        "leaders_tenant_isolation_policy": (
            f"CREATE POLICY leaders_tenant_isolation_policy ON leaders FOR SELECT USING {read}"
        ),
        "leaders_insert_policy": (
            f"CREATE POLICY leaders_insert_policy ON leaders FOR INSERT WITH CHECK {insert_check}"
        ),
        "leaders_update_policy": (
            f"CREATE POLICY leaders_update_policy ON leaders FOR UPDATE "
            f"USING {update_using} WITH CHECK {_leader_write_scope()}"
        ),
        "leaders_delete_policy": (
            f"CREATE POLICY leaders_delete_policy ON leaders FOR DELETE USING {_leader_write_scope()}"
        ),
    }


def assignment_policy_sql() -> dict[str, str]:
    """``CREATE POLICY`` statements for ``leader_assignments`` (never reads ``leaders``)."""
    alias = TABLE
    token_read = f"""EXISTS (
        SELECT 1 FROM export_tokens et
        WHERE {_TOKEN} AND et.district_id = {alias}.district_id)"""
    read = f"""({SUPERADMIN_SQL} OR {district_membership_sql(alias)}
        OR ({alias}.congregation_id IS NOT NULL AND {congregation_membership_sql(alias)})
        OR {token_read})"""
    write = f"""({SUPERADMIN_SQL} OR {district_write_membership_sql(alias)}
        OR ({alias}.congregation_id IS NOT NULL AND {congregation_write_membership_sql(alias)}))"""
    return {
        "leader_assignments_select": f"CREATE POLICY leader_assignments_select ON {TABLE} FOR SELECT USING {read}",
        "leader_assignments_insert": f"CREATE POLICY leader_assignments_insert ON {TABLE} FOR INSERT WITH CHECK {write}",
        "leader_assignments_update": (
            f"CREATE POLICY leader_assignments_update ON {TABLE} FOR UPDATE USING {write} WITH CHECK {write}"
        ),
        "leader_assignments_delete": f"CREATE POLICY leader_assignments_delete ON {TABLE} FOR DELETE USING {write}",
    }


def legacy_policy_sql() -> dict[str, str]:
    """The pre-assignment leader policies, for the downgrade."""
    statements = {}
    for name, (command, using, check) in LEGACY_LEADER_POLICIES.items():
        clauses = (f" USING ({using})" if using else "") + (f" WITH CHECK ({check})" if check else "")
        statements[name] = f"CREATE POLICY {name} ON leaders FOR {command}{clauses}"
    return statements
