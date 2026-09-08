"""PostgreSQL Row-Level Security (RLS) Policies for Tenant Isolation.

This module contains SQL statements for creating RLS policies on tenant-specific tables.
These policies should be applied as part of the database migration process.

RLS policies provide an additional layer of security by enforcing tenant isolation
at the database level, even if application-level checks are bypassed.
"""

from __future__ import annotations

# RLS Policies for each tenant-specific table
# These policies assume that the current user's tenant context is set via:
# - current_setting('app.current_user_sub', true) for user subject
#
# The legacy ``events`` table was dropped by Alembic revision 0125. Current
# tenant ownership is anchored on ``planning_slots``. Derived tables join
# through ``planning_slots`` rather than referencing the removed table.

SUPERADMIN_SQL = """
EXISTS (
    SELECT 1
    FROM users
    WHERE sub = current_setting('app.current_user_sub', true)
      AND is_superadmin = true
)
"""


def district_membership_sql(table_alias: str) -> str:
    return f"""
EXISTS (
    SELECT 1
    FROM memberships m
    WHERE m.user_sub = current_setting('app.current_user_sub', true)
      AND m.scope_type = 'DISTRICT'
      AND m.scope_id = {table_alias}.district_id
)
"""


def congregation_membership_sql(table_alias: str) -> str:
    return f"""
EXISTS (
    SELECT 1
    FROM memberships m
    WHERE m.user_sub = current_setting('app.current_user_sub', true)
      AND m.scope_type = 'CONGREGATION'
      AND m.scope_id = {table_alias}.congregation_id
)
"""


def district_write_membership_sql(table_alias: str) -> str:
    return f"""
EXISTS (
    SELECT 1
    FROM memberships m
    WHERE m.user_sub = current_setting('app.current_user_sub', true)
      AND m.scope_type = 'DISTRICT'
      AND m.scope_id = {table_alias}.district_id
      AND m.role IN ('PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
)
"""


def congregation_write_membership_sql(table_alias: str) -> str:
    return f"""
EXISTS (
    SELECT 1
    FROM memberships m
    WHERE m.user_sub = current_setting('app.current_user_sub', true)
      AND m.scope_type = 'CONGREGATION'
      AND m.scope_id = {table_alias}.congregation_id
      AND m.role IN ('PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
)
"""


def district_admin_membership_sql(table_alias: str) -> str:
    return f"""
EXISTS (
    SELECT 1
    FROM memberships m
    WHERE m.user_sub = current_setting('app.current_user_sub', true)
      AND m.scope_type = 'DISTRICT'
      AND m.scope_id = {table_alias}.district_id
      AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
)
"""


def congregation_admin_membership_sql(table_alias: str) -> str:
    return f"""
EXISTS (
    SELECT 1
    FROM memberships m
    WHERE m.user_sub = current_setting('app.current_user_sub', true)
      AND m.scope_type = 'CONGREGATION'
      AND m.scope_id = {table_alias}.congregation_id
      AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
)
"""


def planning_slot_read_sql(alias: str = 'planning_slots') -> str:
    return f"""(
        {SUPERADMIN_SQL}
        OR {district_membership_sql(alias)}
        OR ({alias}.congregation_id IS NOT NULL AND {congregation_membership_sql(alias)})
    )"""


def planning_slot_write_sql(alias: str = 'planning_slots') -> str:
    return f"""(
        {SUPERADMIN_SQL}
        OR {district_write_membership_sql(alias)}
        OR ({alias}.congregation_id IS NOT NULL AND {congregation_write_membership_sql(alias)})
    )"""


def planning_slot_admin_sql(alias: str = 'planning_slots') -> str:
    return f"""(
        {SUPERADMIN_SQL}
        OR {district_admin_membership_sql(alias)}
        OR ({alias}.congregation_id IS NOT NULL AND {congregation_admin_membership_sql(alias)})
    )"""


def related_planning_slot_sql(table_name: str, permission_sql_factory) -> str:
    return f"""(
        {SUPERADMIN_SQL}
        OR EXISTS (
            SELECT 1
            FROM planning_slots ps
            WHERE ps.id = {table_name}.planning_slot_id
              AND {permission_sql_factory('ps')}
        )
    )"""


def invitation_visibility_sql(
    congregation_permission_sql_factory,
    planning_slot_permission_sql_factory,
) -> str:
    return f"""(
        {SUPERADMIN_SQL}
        OR EXISTS (
            SELECT 1
            FROM congregations c
            WHERE c.id IN (
                congregation_invitations.source_congregation_id,
                congregation_invitations.target_congregation_id
            )
              AND {congregation_permission_sql_factory('c')}
        )
        OR EXISTS (
            SELECT 1
            FROM planning_slots ps
            WHERE ps.id = congregation_invitations.source_planning_slot_id
              AND {planning_slot_permission_sql_factory('ps')}
        )
    )"""


def congregation_row_read_sql(alias: str = "congregations") -> str:
    return f"""(
        {SUPERADMIN_SQL}
        OR EXISTS (
            SELECT 1
            FROM memberships m
            WHERE m.user_sub = current_setting('app.current_user_sub', true)
              AND m.scope_type = 'DISTRICT'
              AND m.scope_id = {alias}.district_id
        )
        OR EXISTS (
            SELECT 1
            FROM memberships m
            WHERE m.user_sub = current_setting('app.current_user_sub', true)
              AND m.scope_type = 'CONGREGATION'
              AND m.scope_id = {alias}.id
        )
    )"""


RLS_POLICIES = {
    "planning_slots": {
        "enable": "ALTER TABLE planning_slots ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""
            CREATE POLICY planning_slots_tenant_isolation_policy ON planning_slots
                FOR SELECT
                USING {planning_slot_read_sql()};
            """,
            f"""
            CREATE POLICY planning_slots_insert_policy ON planning_slots
                FOR INSERT
                WITH CHECK {planning_slot_write_sql()};
            """,
            f"""
            CREATE POLICY planning_slots_update_policy ON planning_slots
                FOR UPDATE
                USING {planning_slot_read_sql()}
                WITH CHECK {planning_slot_write_sql()};
            """,
            f"""
            CREATE POLICY planning_slots_delete_policy ON planning_slots
                FOR DELETE
                USING {planning_slot_admin_sql()};
            """,
        ],
    },
    "event_instances": {
        "enable": "ALTER TABLE event_instances ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""
            CREATE POLICY event_instances_tenant_isolation_policy ON event_instances
                FOR SELECT
                USING {related_planning_slot_sql('event_instances', planning_slot_read_sql)};
            """,
            f"""
            CREATE POLICY event_instances_insert_policy ON event_instances
                FOR INSERT
                WITH CHECK {related_planning_slot_sql('event_instances', planning_slot_write_sql)};
            """,
            f"""
            CREATE POLICY event_instances_update_policy ON event_instances
                FOR UPDATE
                USING {related_planning_slot_sql('event_instances', planning_slot_read_sql)}
                WITH CHECK {related_planning_slot_sql('event_instances', planning_slot_write_sql)};
            """,
            f"""
            CREATE POLICY event_instances_delete_policy ON event_instances
                FOR DELETE
                USING {related_planning_slot_sql('event_instances', planning_slot_admin_sql)};
            """,
        ],
    },
    "service_assignments": {
        "enable": "ALTER TABLE service_assignments ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""
            CREATE POLICY service_assignments_tenant_isolation_policy ON service_assignments
                FOR SELECT
                USING {related_planning_slot_sql('service_assignments', planning_slot_read_sql)};
            """,
            f"""
            CREATE POLICY service_assignments_insert_policy ON service_assignments
                FOR INSERT
                WITH CHECK {related_planning_slot_sql('service_assignments', planning_slot_write_sql)};
            """,
            f"""
            CREATE POLICY service_assignments_update_policy ON service_assignments
                FOR UPDATE
                USING {related_planning_slot_sql('service_assignments', planning_slot_read_sql)}
                WITH CHECK {related_planning_slot_sql('service_assignments', planning_slot_write_sql)};
            """,
            f"""
            CREATE POLICY service_assignments_delete_policy ON service_assignments
                FOR DELETE
                USING {related_planning_slot_sql('service_assignments', planning_slot_admin_sql)};
            """,
        ],
    },
    "leaders": {
        "enable": "ALTER TABLE leaders ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""
            CREATE POLICY leaders_tenant_isolation_policy ON leaders
                FOR SELECT
                USING (
                    {SUPERADMIN_SQL}
                    OR {congregation_membership_sql('leaders')}
                    OR EXISTS (
                        SELECT 1
                        FROM memberships m
                        JOIN congregations c ON c.id = leaders.congregation_id
                        WHERE m.user_sub = current_setting('app.current_user_sub', true)
                          AND m.scope_type = 'DISTRICT'
                          AND m.scope_id = c.district_id
                    )
                );
            """,
        ],
    },
    "congregation_invitations": {
        "enable": "ALTER TABLE congregation_invitations ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""
            CREATE POLICY invitations_tenant_isolation_policy ON congregation_invitations
                FOR SELECT
                USING {invitation_visibility_sql(congregation_row_read_sql, planning_slot_read_sql)};
            """,
        ],
    },
    "calendar_integrations": {
        "enable": "ALTER TABLE calendar_integrations ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""
            CREATE POLICY calendar_integrations_tenant_isolation_policy ON calendar_integrations
                FOR SELECT
                USING {planning_slot_read_sql('calendar_integrations')};
            """,
        ],
    },
    "memberships": {
        "enable": "ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""
            CREATE POLICY memberships_tenant_isolation_policy ON memberships
                FOR SELECT
                USING (
                    {SUPERADMIN_SQL}
                    OR memberships.user_sub = current_setting('app.current_user_sub', true)
                );
            """,
        ],
    },
}

def get_rls_sql(table_name: str) -> list[str]:
    """Get RLS SQL statements for a specific table.

    Args:
        table_name: Name of the table.

    Returns:
        List of SQL statements to execute.
    """
    if table_name not in RLS_POLICIES:
        return []

    policies = RLS_POLICIES[table_name]
    sql_statements = [policies["enable"]]

    for policy in policies["policies"]:
        # Clean up the policy SQL (remove leading/trailing whitespace and newlines)
        cleaned_policy = policy.strip()
        if cleaned_policy:
            sql_statements.append(cleaned_policy)

    return sql_statements


def get_all_rls_sql() -> list[str]:
    """Get all RLS SQL statements for all tables.

    Returns:
        List of all SQL statements to execute.
    """
    all_sql = []

    for table_name in RLS_POLICIES:
        all_sql.extend(get_rls_sql(table_name))

    return all_sql


# Function to drop all RLS policies (for rollback)
def get_drop_rls_sql() -> list[str]:
    """Get SQL statements to drop all RLS policies.

    Returns:
        List of SQL statements to drop policies.
    """
    drop_sql = []

    for table_name in RLS_POLICIES:
        # Drop all policies on the table
        drop_sql.append(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")

        # Drop each policy
        for policy_info in RLS_POLICIES[table_name].get("policies", []):
            # Extract policy name from the CREATE POLICY statement
            if "CREATE POLICY" in policy_info:
                parts = policy_info.split()
                policy_name_index = parts.index("POLICY") + 1
                if policy_name_index < len(parts):
                    policy_name = parts[policy_name_index].split("(")[0]
                    drop_sql.append(f"DROP POLICY IF EXISTS {policy_name} ON {table_name};")

    return drop_sql
