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
# Worker/maintenance Celery tasks set ``app.is_system_worker=true`` through
# ``TenantContext`` so scheduled cross-tenant jobs can operate under RLS without
# requiring the database role to own or BYPASSRLS-protect tenant tables.
# The legacy ``events`` table was dropped by Alembic revision 0125. Current
# tenant ownership is anchored on ``planning_slots``. Derived tables join
# through ``planning_slots`` rather than referencing the removed table.

SYSTEM_WORKER_SQL = """current_setting('app.is_system_worker', true) = 'true'"""

# nosec B608 — interpolated aliases are internal code constants, never user input
SUPERADMIN_SQL = f"""
EXISTS (
    SELECT 1
    FROM users
    WHERE sub = current_setting('app.current_user_sub', true)
      AND is_superadmin = true
)
OR {SYSTEM_WORKER_SQL}
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
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


# nosec B608 — interpolated aliases are internal code constants, never user input
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


# nosec B608 — interpolated aliases are internal code constants, never user input
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


# nosec B608 — interpolated aliases are internal code constants, never user input
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


# nosec B608 — interpolated aliases are internal code constants, never user input
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


# nosec B608 — interpolated aliases are internal code constants, never user input
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


# nosec B608 — interpolated aliases are internal code constants, never user input
def planning_slot_read_sql(alias: str = "planning_slots") -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR {district_membership_sql(alias)}
    OR ({alias}.congregation_id IS NOT NULL AND {congregation_membership_sql(alias)})
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def planning_slot_write_sql(alias: str = "planning_slots") -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR {district_write_membership_sql(alias)}
    OR ({alias}.congregation_id IS NOT NULL AND {congregation_write_membership_sql(alias)})
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def notifications_update_sql(alias: str = "notifications") -> str:
    """Allow users with VIEWER role or higher to update notifications (e.g., mark as read)."""
    return f"""
(
    {SUPERADMIN_SQL}
    OR {district_membership_sql(alias)}
    OR ({alias}.congregation_id IS NOT NULL AND {congregation_membership_sql(alias)})
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def leaders_self_update_sql(alias: str = "leaders") -> str:
    """Allow users to update their own leader record (self-link/unlink via user_sub)."""
    return f"""
(
    {SUPERADMIN_SQL}
    OR {district_membership_sql(alias)}
    OR ({alias}.congregation_id IS NOT NULL AND {congregation_membership_sql(alias)})
    OR ({alias}.user_sub = current_setting('app.current_user_sub', true))
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def planning_slot_admin_sql(alias: str = "planning_slots") -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR {district_admin_membership_sql(alias)}
    OR ({alias}.congregation_id IS NOT NULL AND {congregation_admin_membership_sql(alias)})
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def related_planning_slot_sql(table_name: str, permission_sql_factory) -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR EXISTS (
        SELECT 1
        FROM planning_slots ps
        WHERE ps.id = {table_name}.planning_slot_id
          AND {permission_sql_factory("ps")}
    )
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def invitation_visibility_sql(
    congregation_permission_sql_factory,
    planning_slot_permission_sql_factory,
) -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR EXISTS (
        SELECT 1
        FROM congregations c
        WHERE c.id IN (
            congregation_invitations.source_congregation_id,
            congregation_invitations.target_congregation_id
        )
          AND {congregation_permission_sql_factory("c")}
    )
    OR EXISTS (
        SELECT 1
        FROM planning_slots ps
        WHERE ps.id = congregation_invitations.source_planning_slot_id
          AND {planning_slot_permission_sql_factory("ps")}
    )
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def congregation_row_read_sql(alias: str = "congregations") -> str:
    return f"""
(
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
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def congregation_row_write_sql(alias: str = "congregations") -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR EXISTS (
        SELECT 1 FROM memberships m
        WHERE m.user_sub = current_setting('app.current_user_sub', true)
          AND m.scope_type = 'DISTRICT'
          AND m.scope_id = {alias}.district_id
          AND m.role IN ('PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
    )
    OR EXISTS (
        SELECT 1 FROM memberships m
        WHERE m.user_sub = current_setting('app.current_user_sub', true)
          AND m.scope_type = 'CONGREGATION'
          AND m.scope_id = {alias}.id
          AND m.role IN ('PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
    )
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def congregation_row_admin_sql(alias: str = "congregations") -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR EXISTS (
        SELECT 1 FROM memberships m
        WHERE m.user_sub = current_setting('app.current_user_sub', true)
          AND m.scope_type = 'DISTRICT'
          AND m.scope_id = {alias}.district_id
          AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
    )
    OR EXISTS (
        SELECT 1 FROM memberships m
        WHERE m.user_sub = current_setting('app.current_user_sub', true)
          AND m.scope_type = 'CONGREGATION'
          AND m.scope_id = {alias}.id
          AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
    )
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def scoped_membership_admin_sql(alias: str = "memberships") -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR (
        -- Check if current user has admin role via GUC (avoids recursive memberships lookup)
        current_setting('app.current_user_roles', true) LIKE '%CONGREGATION_ADMIN%'
        OR current_setting('app.current_user_roles', true) LIKE '%DISTRICT_ADMIN%'
    )
    AND (
        -- For DISTRICT scope: user must have admin membership in that district
        ({alias}.scope_type = 'DISTRICT' AND EXISTS (
            SELECT 1 FROM memberships m
            WHERE m.user_sub = current_setting('app.current_user_sub', true)
              AND m.scope_type = 'DISTRICT'
              AND m.scope_id = {alias}.scope_id
              AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
        ))
        -- For CONGREGATION scope: user must have admin membership in that congregation or its district
        OR ({alias}.scope_type = 'CONGREGATION' AND EXISTS (
            SELECT 1 FROM memberships m
            WHERE m.user_sub = current_setting('app.current_user_sub', true)
              AND (
                  (m.scope_type = 'CONGREGATION' AND m.scope_id = {alias}.scope_id)
                  OR (m.scope_type = 'DISTRICT' AND m.scope_id = (
                      SELECT c.district_id FROM congregations c WHERE c.id = {alias}.scope_id
                  ))
              )
              AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
        ))
    )
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def self_approved_registration_insert_sql(alias: str = "memberships") -> str:
    return f"""
(
    {alias}.user_sub = current_setting('app.current_user_sub', true)
    AND EXISTS (
        SELECT 1
        FROM leader_registrations lr
        WHERE lr.status = 'APPROVED'
          AND lr.user_sub = {alias}.user_sub
          AND lr.assigned_scope_type = {alias}.scope_type
          AND lr.assigned_scope_id = {alias}.scope_id
          AND lr.assigned_role = {alias}.role
    )
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def external_event_link_sql(permission_sql_factory) -> str:
    return f"""
(
    {SUPERADMIN_SQL}
    OR EXISTS (
        SELECT 1 FROM event_instances ei
        JOIN planning_slots ps ON ps.id = ei.planning_slot_id
        WHERE ei.id = external_event_links.event_instance_id
          AND {permission_sql_factory("ps")}
    )
    OR EXISTS (
        SELECT 1 FROM calendar_integrations ci
        WHERE ci.id = external_event_links.calendar_integration_id
          AND {permission_sql_factory("ci")}
    )
)
"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def invitation_overwrite_request_sql(invitation_visibility_factory) -> str:
    return f"""(/* # nosec B608 — interpolated aliases are internal code constants, never user input */
        {SUPERADMIN_SQL}
        OR {invitation_visibility_factory("invitation_overwrite_requests")}
    )"""


# nosec B608 — interpolated aliases are internal code constants, never user input
def invitation_overwrite_request_visibility_factory(
    congregation_permission_sql_factory,
    planning_slot_permission_sql_factory,
):
    """Return a callable that generates invitation overwrite request visibility SQL.
    
    Derives tenant access through invitation_id -> congregation_invitations relationship.
    """
    def _factory(alias: str) -> str:
        return f"""(/* # nosec B608 — interpolated aliases are internal code constants, never user input */
            {SUPERADMIN_SQL}
            OR EXISTS (
                SELECT 1
                FROM congregation_invitations ci
                WHERE ci.id = {alias}.invitation_id
                  AND (
                      EXISTS (
                          SELECT 1
                          FROM congregations c
                          WHERE c.id IN (
                              ci.source_congregation_id,
                              ci.target_congregation_id
                          )
                            AND {congregation_permission_sql_factory("c")}
                      )
                      OR EXISTS (
                          SELECT 1
                          FROM planning_slots ps
                          WHERE ps.id = ci.source_planning_slot_id
                            AND {planning_slot_permission_sql_factory("ps")}
                      )
                  )
            )
        )"""
    return _factory


RLS_POLICIES = {
    "planning_slots": {
        "enable": "ALTER TABLE planning_slots ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY planning_slots_tenant_isolation_policy ON planning_slots
                FOR SELECT
                USING {planning_slot_read_sql()};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY planning_slots_insert_policy ON planning_slots
                FOR INSERT
                WITH CHECK {planning_slot_write_sql()};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY planning_slots_update_policy ON planning_slots
                FOR UPDATE
                USING {planning_slot_read_sql()}
                WITH CHECK {planning_slot_write_sql()};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY planning_slots_delete_policy ON planning_slots
                FOR DELETE
                USING {planning_slot_admin_sql()};
            """,
        ],
    },
    "event_instances": {
        "enable": "ALTER TABLE event_instances ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY event_instances_tenant_isolation_policy ON event_instances
                FOR SELECT
                USING {related_planning_slot_sql("event_instances", planning_slot_read_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY event_instances_insert_policy ON event_instances
                FOR INSERT
                WITH CHECK {related_planning_slot_sql("event_instances", planning_slot_write_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY event_instances_update_policy ON event_instances
                FOR UPDATE
                USING {related_planning_slot_sql("event_instances", planning_slot_read_sql)}
                WITH CHECK {related_planning_slot_sql("event_instances", planning_slot_write_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY event_instances_delete_policy ON event_instances
                FOR DELETE
                USING {related_planning_slot_sql("event_instances", planning_slot_admin_sql)};
            """,
        ],
    },
    "service_assignments": {
        "enable": "ALTER TABLE service_assignments ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY service_assignments_tenant_isolation_policy ON service_assignments
                FOR SELECT
                USING {related_planning_slot_sql("service_assignments", planning_slot_read_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY service_assignments_insert_policy ON service_assignments
                FOR INSERT
                WITH CHECK {related_planning_slot_sql("service_assignments", planning_slot_write_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY service_assignments_update_policy ON service_assignments
                FOR UPDATE
                USING {related_planning_slot_sql("service_assignments", planning_slot_read_sql)}
                WITH CHECK {related_planning_slot_sql("service_assignments", planning_slot_write_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY service_assignments_delete_policy ON service_assignments
                FOR DELETE
                USING {related_planning_slot_sql("service_assignments", planning_slot_write_sql)};
            """,
        ],
    },
    "leaders": {
        "enable": "ALTER TABLE leaders ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY leaders_tenant_isolation_policy ON leaders
                FOR SELECT
                USING (
                    {SUPERADMIN_SQL}
                    OR {district_membership_sql("leaders")}
                    OR (leaders.congregation_id IS NOT NULL AND {congregation_membership_sql("leaders")})
                );
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY leaders_insert_policy ON leaders
                FOR INSERT
                WITH CHECK {planning_slot_write_sql("leaders")};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY leaders_update_policy ON leaders
                FOR UPDATE
                USING {planning_slot_read_sql("leaders")}
                WITH CHECK {leaders_self_update_sql("leaders")};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY leaders_delete_policy ON leaders
                FOR DELETE
                USING {planning_slot_write_sql("leaders")};
            """,
        ],
    },
    "congregation_invitations": {
        "enable": "ALTER TABLE congregation_invitations ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY invitations_tenant_isolation_policy ON congregation_invitations
                FOR SELECT
                USING {invitation_visibility_sql(congregation_row_read_sql, planning_slot_read_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY invitations_insert_policy ON congregation_invitations
                FOR INSERT
                WITH CHECK {invitation_visibility_sql(congregation_row_write_sql, planning_slot_write_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY invitations_update_policy ON congregation_invitations
                FOR UPDATE
                USING {invitation_visibility_sql(congregation_row_read_sql, planning_slot_read_sql)}
                WITH CHECK {invitation_visibility_sql(congregation_row_write_sql, planning_slot_write_sql)};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY invitations_delete_policy ON congregation_invitations
                FOR DELETE
                USING {invitation_visibility_sql(congregation_row_write_sql, planning_slot_write_sql)};
            """,
        ],
    },
    "calendar_integrations": {
        "enable": "ALTER TABLE calendar_integrations ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY calendar_integrations_tenant_isolation_policy ON calendar_integrations
                FOR SELECT
                USING {planning_slot_read_sql("calendar_integrations")};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY calendar_integrations_insert_policy ON calendar_integrations
                FOR INSERT
                WITH CHECK {planning_slot_write_sql("calendar_integrations")};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY calendar_integrations_update_policy ON calendar_integrations
                FOR UPDATE
                USING {planning_slot_read_sql("calendar_integrations")}
                WITH CHECK {planning_slot_write_sql("calendar_integrations")};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY calendar_integrations_delete_policy ON calendar_integrations
                FOR DELETE
                USING {planning_slot_admin_sql("calendar_integrations")};
            """,
        ],
    },
    "memberships": {
        "enable": "ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY memberships_tenant_isolation_policy ON memberships
                FOR SELECT
                USING (
                    {SUPERADMIN_SQL}
                    OR memberships.user_sub = current_setting('app.current_user_sub', true)
                );
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY memberships_insert_policy ON memberships
                FOR INSERT
                WITH CHECK (
                    {scoped_membership_admin_sql("memberships")}
                    OR {self_approved_registration_insert_sql("memberships")}
                );
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY memberships_update_policy ON memberships
                FOR UPDATE
                USING {scoped_membership_admin_sql("memberships")}
                WITH CHECK {scoped_membership_admin_sql("memberships")};
            """,
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
            CREATE POLICY memberships_delete_policy ON memberships
                FOR DELETE
                USING {scoped_membership_admin_sql("memberships")};
            """,
        ],
    },
    "planning_series": {
        "enable": "ALTER TABLE planning_series ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY planning_series_select_policy ON planning_series FOR SELECT USING {planning_slot_read_sql("planning_series")};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY planning_series_insert_policy ON planning_series FOR INSERT WITH CHECK {planning_slot_write_sql("planning_series")};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY planning_series_update_policy ON planning_series FOR UPDATE USING {planning_slot_read_sql("planning_series")} WITH CHECK {planning_slot_write_sql("planning_series")};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY planning_series_delete_policy ON planning_series FOR DELETE USING {planning_slot_admin_sql("planning_series")};""",
        ],
    },
    "notifications": {
        "enable": "ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY notifications_select_policy ON notifications FOR SELECT USING {planning_slot_read_sql("notifications")};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY notifications_insert_policy ON notifications FOR INSERT WITH CHECK {planning_slot_write_sql("notifications")};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY notifications_update_policy ON notifications FOR UPDATE USING {notifications_update_sql("notifications")} WITH CHECK {notifications_update_sql("notifications")};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY notifications_delete_policy ON notifications FOR DELETE USING {planning_slot_admin_sql("notifications")};""",
        ],
    },
    "leader_registrations": {
        "enable": "ALTER TABLE leader_registrations ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY leader_registrations_select_policy ON leader_registrations FOR SELECT USING ({planning_slot_read_sql("leader_registrations")} OR leader_registrations.user_sub = current_setting('app.current_user_sub', true));""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY leader_registrations_insert_policy ON leader_registrations FOR INSERT WITH CHECK (
                {planning_slot_write_sql("leader_registrations")}
                OR (
                    -- Allow public registration: district_id must be valid and user_sub must be NULL
                    leader_registrations.user_sub IS NULL
                    AND EXISTS (
                        SELECT 1 FROM districts d WHERE d.id = leader_registrations.district_id
                    )
                )
            );""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY leader_registrations_update_policy ON leader_registrations FOR UPDATE USING {planning_slot_read_sql("leader_registrations")} WITH CHECK {planning_slot_write_sql("leader_registrations")};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY leader_registrations_delete_policy ON leader_registrations FOR DELETE USING {planning_slot_admin_sql("leader_registrations")};""",
        ],
    },
    "congregation_groups": {
        "enable": "ALTER TABLE congregation_groups ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY congregation_groups_select_policy ON congregation_groups FOR SELECT USING ({SUPERADMIN_SQL} OR {district_membership_sql("congregation_groups")});""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY congregation_groups_insert_policy ON congregation_groups FOR INSERT WITH CHECK ({SUPERADMIN_SQL} OR {district_write_membership_sql("congregation_groups")});""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY congregation_groups_update_policy ON congregation_groups FOR UPDATE USING ({SUPERADMIN_SQL} OR {district_membership_sql("congregation_groups")}) WITH CHECK ({SUPERADMIN_SQL} OR {district_write_membership_sql("congregation_groups")});""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY congregation_groups_delete_policy ON congregation_groups FOR DELETE USING ({SUPERADMIN_SQL} OR {district_admin_membership_sql("congregation_groups")});""",
        ],
    },
    "audit_logs": {
        "enable": "ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY audit_logs_select_policy ON audit_logs FOR SELECT USING ({SUPERADMIN_SQL} OR (audit_logs.district_id IS NOT NULL AND {district_membership_sql("audit_logs")}) OR (audit_logs.congregation_id IS NOT NULL AND {congregation_membership_sql("audit_logs")}));""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY audit_logs_insert_policy ON audit_logs FOR INSERT WITH CHECK ({SUPERADMIN_SQL} OR (audit_logs.district_id IS NOT NULL AND {district_membership_sql("audit_logs")}) OR (audit_logs.congregation_id IS NOT NULL AND {congregation_membership_sql("audit_logs")}));""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY audit_logs_update_policy ON audit_logs FOR UPDATE USING ({SUPERADMIN_SQL}) WITH CHECK ({SUPERADMIN_SQL});""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY audit_logs_delete_policy ON audit_logs FOR DELETE USING ({SUPERADMIN_SQL});""",
        ],
    },
    "external_event_links": {
        "enable": "ALTER TABLE external_event_links ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY external_event_links_select_policy ON external_event_links FOR SELECT USING {external_event_link_sql(planning_slot_read_sql)};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY external_event_links_insert_policy ON external_event_links FOR INSERT WITH CHECK {external_event_link_sql(planning_slot_write_sql)};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY external_event_links_update_policy ON external_event_links FOR UPDATE USING {external_event_link_sql(planning_slot_read_sql)} WITH CHECK {external_event_link_sql(planning_slot_write_sql)};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY external_event_links_delete_policy ON external_event_links FOR DELETE USING {external_event_link_sql(planning_slot_admin_sql)};""",
        ],
    },
    "invitation_overwrite_requests": {
        "enable": "ALTER TABLE invitation_overwrite_requests ENABLE ROW LEVEL SECURITY;",
        "policies": [
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY invitation_overwrite_requests_select_policy ON invitation_overwrite_requests FOR SELECT USING {invitation_overwrite_request_sql(invitation_overwrite_request_visibility_factory(congregation_row_read_sql, planning_slot_read_sql))};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY invitation_overwrite_requests_insert_policy ON invitation_overwrite_requests FOR INSERT WITH CHECK {invitation_overwrite_request_sql(invitation_overwrite_request_visibility_factory(congregation_row_write_sql, planning_slot_write_sql))};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY invitation_overwrite_requests_update_policy ON invitation_overwrite_requests FOR UPDATE USING {invitation_overwrite_request_sql(invitation_overwrite_request_visibility_factory(congregation_row_read_sql, planning_slot_read_sql))} WITH CHECK {invitation_overwrite_request_sql(invitation_overwrite_request_visibility_factory(congregation_row_write_sql, planning_slot_write_sql))};""",
            f"""/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ CREATE POLICY invitation_overwrite_requests_delete_policy ON invitation_overwrite_requests FOR DELETE USING {invitation_overwrite_request_sql(invitation_overwrite_request_visibility_factory(congregation_row_admin_sql, planning_slot_admin_sql))};""",
        ],
    },
}


def get_rls_sql(table_name: str) -> list[str]:
    """Get RLS SQL statements for a specific table.

    Args:
        table_name: Name of the table.

    Returns:
        List of SQL statements to execute. Policies are created before
        enabling RLS to avoid a window where RLS is active but no policies exist.
    """
    if table_name not in RLS_POLICIES:
        return []

    policies = RLS_POLICIES[table_name]
    sql_statements = []

    # Create policies first
    for policy in policies["policies"]:
        # Clean up the policy SQL (remove leading/trailing whitespace and newlines)
        cleaned_policy = policy.strip()
        if cleaned_policy:
            sql_statements.append(cleaned_policy)

    # Then enable RLS
    sql_statements.append(policies["enable"])

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
        drop_sql.append(
            f"/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;"
        )

        # Drop each policy
        for policy_info in RLS_POLICIES[table_name].get("policies", []):
            # Extract policy name from the CREATE POLICY statement
            if "CREATE POLICY" in policy_info:
                parts = policy_info.split()
                policy_name_index = parts.index("POLICY") + 1
                if policy_name_index < len(parts):
                    policy_name = parts[policy_name_index].split("(")[0]
                    drop_sql.append(
                        f"/* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */ DROP POLICY IF EXISTS {policy_name} ON {table_name};"
                    )

    return drop_sql
