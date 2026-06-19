"""PostgreSQL Row-Level Security (RLS) Policies for Tenant Isolation.

This module contains SQL statements for creating RLS policies on tenant-specific tables.
These policies should be applied as part of the database migration process.

RLS policies provide an additional layer of security by enforcing tenant isolation
at the database level, even if application-level checks are bypassed.
"""

from __future__ import annotations

# RLS Policies for each tenant-specific table
# These policies assume that the current user's tenant context is set via:
# - current_setting('app.current_tenant_id') for tenant ID
# - current_setting('app.current_user_sub') for user subject
# - current_setting('app.current_district_id') for district ID

RLS_POLICIES = {
    # Events table
    "events": {
        "enable": "ALTER TABLE events ENABLE ROW LEVEL SECURITY;",
        "policies": [
            # Allow read access to events in user's districts/congregations
            """
            CREATE POLICY events_tenant_isolation_policy ON events
                USING (
                    -- User is superadmin
                    (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
                    OR
                    -- Event belongs to a congregation user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        JOIN congregations c ON c.id = m.scope_id
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'congregation'
                        AND m.scope_id = events.congregation_id
                    ))
                    OR
                    -- Event belongs to a district user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'district'
                        AND m.scope_id = events.district_id
                    ))
                );
            """,
            # Allow insert/update for users with write access
            """
            CREATE POLICY events_write_policy ON events
                FOR INSERT OR UPDATE
                USING (
                    -- User is superadmin
                    (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
                    OR
                    -- User has write role in the event's congregation
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'congregation'
                        AND m.scope_id = NEW.congregation_id
                        AND m.role IN ('PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
                    ))
                    OR
                    -- User has write role in the event's district
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'district'
                        AND m.scope_id = NEW.district_id
                        AND m.role IN ('PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
                    ))
                );
            """,
            # Allow delete for users with admin access
            """
            CREATE POLICY events_delete_policy ON events
                FOR DELETE
                USING (
                    -- User is superadmin
                    (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
                    OR
                    -- User has admin role in the event's congregation
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'congregation'
                        AND m.scope_id = OLD.congregation_id
                        AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
                    ))
                    OR
                    -- User has admin role in the event's district
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'district'
                        AND m.scope_id = OLD.district_id
                        AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
                    ))
                );
            """,
        ],
    },
    
    # Service Assignments table
    "service_assignments": {
        "enable": "ALTER TABLE service_assignments ENABLE ROW LEVEL SECURITY;",
        "policies": [
            # Read access
            """
            CREATE POLICY service_assignments_tenant_isolation_policy ON service_assignments
                USING (
                    -- User is superadmin
                    (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
                    OR
                    -- Assignment belongs to a congregation user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'congregation'
                        AND m.scope_id = service_assignments.congregation_id
                    ))
                    OR
                    -- Assignment belongs to a district user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        JOIN congregations c ON c.id = service_assignments.congregation_id
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'district'
                        AND m.scope_id = c.district_id
                    ))
                );
            """,
        ],
    },
    
    # Leaders table
    "leaders": {
        "enable": "ALTER TABLE leaders ENABLE ROW LEVEL SECURITY;",
        "policies": [
            # Read access
            """
            CREATE POLICY leaders_tenant_isolation_policy ON leaders
                USING (
                    -- User is superadmin
                    (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
                    OR
                    -- Leader belongs to a congregation user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'congregation'
                        AND m.scope_id = leaders.congregation_id
                    ))
                    OR
                    -- Leader belongs to a district user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        JOIN congregations c ON c.id = leaders.congregation_id
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'district'
                        AND m.scope_id = c.district_id
                    ))
                );
            """,
        ],
    },
    
    # Invitations table
    "invitations": {
        "enable": "ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;",
        "policies": [
            # Read access
            """
            CREATE POLICY invitations_tenant_isolation_policy ON invitations
                USING (
                    -- User is superadmin
                    (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
                    OR
                    -- Invitation belongs to a congregation user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'congregation'
                        AND m.scope_id = invitations.congregation_id
                    ))
                    OR
                    -- Invitation belongs to a district user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        JOIN congregations c ON c.id = invitations.congregation_id
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'district'
                        AND m.scope_id = c.district_id
                    ))
                );
            """,
        ],
    },
    
    # Calendar Integrations table
    "calendar_integrations": {
        "enable": "ALTER TABLE calendar_integrations ENABLE ROW LEVEL SECURITY;",
        "policies": [
            # Read access
            """
            CREATE POLICY calendar_integrations_tenant_isolation_policy ON calendar_integrations
                USING (
                    -- User is superadmin
                    (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
                    OR
                    -- Integration belongs to a congregation user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'congregation'
                        AND m.scope_id = calendar_integrations.congregation_id
                    ))
                    OR
                    -- Integration belongs to a district user has access to
                    (EXISTS (
                        SELECT 1 FROM memberships m
                        JOIN congregations c ON c.id = calendar_integrations.congregation_id
                        WHERE m.user_sub = current_setting('app.current_user_sub')
                        AND m.scope_type = 'district'
                        AND m.scope_id = c.district_id
                    ))
                );
            """,
        ],
    },
    
    # Memberships table (sensitive - only admins can see)
    "memberships": {
        "enable": "ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;",
        "policies": [
            # Read access - only admins can see memberships
            """
            CREATE POLICY memberships_tenant_isolation_policy ON memberships
                USING (
                    -- User is superadmin
                    (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
                    OR
                    -- User is district admin and membership is in their district
                    (EXISTS (
                        SELECT 1 FROM memberships m2
                        WHERE m2.user_sub = current_setting('app.current_user_sub')
                        AND m2.scope_type = 'district'
                        AND m2.role IN ('DISTRICT_ADMIN')
                        AND (
                            (memberships.scope_type = 'district' AND memberships.scope_id = m2.scope_id)
                            OR
                            (memberships.scope_type = 'congregation' AND 
                             EXISTS (
                                 SELECT 1 FROM congregations c
                                 WHERE c.id = memberships.scope_id
                                 AND c.district_id = m2.scope_id
                             ))
                        )
                    ))
                    OR
                    -- User is congregation admin and membership is in their congregation
                    (EXISTS (
                        SELECT 1 FROM memberships m2
                        WHERE m2.user_sub = current_setting('app.current_user_sub')
                        AND m2.scope_type = 'congregation'
                        AND m2.role IN ('CONGREGATION_ADMIN')
                        AND memberships.scope_type = 'congregation'
                        AND memberships.scope_id = m2.scope_id
                    ))
                    OR
                    -- User can see their own memberships
                    (memberships.user_sub = current_setting('app.current_user_sub'))
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
