# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Versioned policy installation for the 20261013 additive duties migration.

Definer helpers return bounded booleans or the subject of the presented opaque
export token. They never return arbitrary account data and fix their search path.
"""

from __future__ import annotations

from app.adapters.db.migrations.rls_policies import (
    SUPERADMIN_SQL,
    congregation_membership_sql,
    distributed_slot_membership_sql,
    district_membership_sql,
    leader_read_sql,
    leader_row_read_sql,
    planning_slot_row_read_sql,
    related_planning_slot_sql,
)
from app.domain.models.event_duty import DEFAULT_DUTY_CATEGORIES
from app.domain.models.role import Role, roles_at_least_sql

_TABLES = (
    "event_duty_categories",
    "event_type_duty_configurations",
    "duty_name_suggestions",
    "event_duty_assignments",
)
_ADMIN_TABLES = {"event_duty_categories", "event_type_duty_configurations"}


def _scope(alias: str, *, roles: str | None = None, inherited: bool = False) -> str:
    role_filter = (
        f"AND m.role IN ({roles})" if roles else f"AND m.role IN ({roles_at_least_sql(Role.VIEWER)})"
    )
    inherited_sql = (
        f"OR ({alias}.congregation_id IS NULL AND EXISTS (SELECT 1 FROM congregations c WHERE c.id=m.scope_id AND c.district_id={alias}.district_id))"
        if inherited
        else ""
    )
    return f"""({SUPERADMIN_SQL} OR EXISTS (
      SELECT 1 FROM memberships m WHERE m.user_sub=current_setting('app.current_user_sub',true)
      {role_filter} AND (
        (m.scope_type='DISTRICT' AND m.scope_id={alias}.district_id)
        OR (m.scope_type='CONGREGATION' AND (m.scope_id={alias}.congregation_id {inherited_sql}))
      )))"""


def _admin(alias: str) -> str:
    return f"""({SUPERADMIN_SQL} OR EXISTS (
      SELECT 1 FROM memberships m WHERE m.user_sub=current_setting('app.current_user_sub',true)
      AND ((m.scope_type='DISTRICT' AND m.scope_id={alias}.district_id AND m.role IN ({roles_at_least_sql(Role.DISTRICT_ADMIN)}))
        OR (m.scope_type='CONGREGATION' AND m.scope_id={alias}.congregation_id
            AND m.role IN ({roles_at_least_sql(Role.CONGREGATION_ADMIN)})))))"""


_FUNCTIONS = (
    f"""CREATE FUNCTION duty_subject_scope(p_sub text, p_district uuid, p_congregation uuid)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT EXISTS (SELECT 1 FROM users u WHERE u.sub=p_sub AND (u.is_superadmin OR EXISTS (
        SELECT 1 FROM memberships m WHERE m.user_sub=u.sub
        AND m.role IN ({roles_at_least_sql(Role.VIEWER)})
        AND ((m.scope_type='DISTRICT' AND m.scope_id=p_district)
          OR (p_congregation IS NOT NULL AND m.scope_type='CONGREGATION'
              AND m.scope_id=p_congregation AND EXISTS (
                SELECT 1 FROM congregations c WHERE c.id=p_congregation AND c.district_id=p_district)))
      )))
    $$""",
    f"""CREATE FUNCTION current_duty_export_subject() RETURNS text
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT COALESCE(et.subject_sub,l.user_sub) FROM export_tokens et
      LEFT JOIN leaders l ON l.id=et.leader_id AND l.district_id=et.district_id
      WHERE et.token=current_setting('app.current_export_token',true)
      AND et.token_type='INTERNAL' AND (et.subject_sub IS NOT NULL OR l.user_sub IS NOT NULL)
      AND (duty_subject_scope(COALESCE(et.subject_sub,l.user_sub),et.district_id,NULL)
        OR EXISTS (SELECT 1 FROM congregations c WHERE c.district_id=et.district_id
          AND duty_subject_scope(COALESCE(et.subject_sub,l.user_sub),et.district_id,c.id)))
    $$""",
    f"""CREATE FUNCTION duty_export_is_subject_bound() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT EXISTS (SELECT 1 FROM export_tokens et
        WHERE et.token=current_setting('app.current_export_token',true) AND et.subject_sub IS NOT NULL)
    $$""",
    f"""CREATE FUNCTION duty_export_slot_allowed(p_slot uuid) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT EXISTS (SELECT 1 FROM planning_slots ps JOIN export_tokens et ON et.district_id=ps.district_id
        WHERE ps.id=p_slot AND et.token=current_setting('app.current_export_token',true)
        AND current_duty_export_subject() IS NOT NULL
        AND (
          duty_subject_scope(current_duty_export_subject(),ps.district_id,ps.congregation_id)
          OR (ps.congregation_id IS NULL AND EXISTS (
            SELECT 1 FROM congregations c WHERE c.district_id=ps.district_id
            AND ('all'=ANY(ps.applicability) OR c.id::text=ANY(ps.applicability))
            AND duty_subject_scope(current_duty_export_subject(),ps.district_id,c.id)
          ))
        )
        AND (EXISTS (SELECT 1 FROM event_duty_assignments da WHERE da.planning_slot_id=ps.id
          AND da.district_id=ps.district_id AND da.congregation_id IS NOT DISTINCT FROM ps.congregation_id
          AND da.linked_user_sub=current_duty_export_subject())
        OR EXISTS (SELECT 1 FROM service_assignments sa JOIN leaders l ON l.id=sa.leader_id
          WHERE sa.planning_slot_id=ps.id AND l.district_id=ps.district_id
          AND l.user_sub=current_duty_export_subject())))
    $$""",
    f"""CREATE FUNCTION eligible_duty_users(p_district uuid,p_congregation uuid)
    RETURNS TABLE(sub text,display_name text)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT DISTINCT u.sub::text,COALESCE(NULLIF(u.name,''),u.username)::text
      FROM users u JOIN memberships candidate ON candidate.user_sub=u.sub
      WHERE (
        (candidate.scope_type='DISTRICT' AND candidate.scope_id=p_district)
        OR (p_congregation IS NOT NULL AND candidate.scope_type='CONGREGATION'
          AND candidate.scope_id=p_congregation AND EXISTS (
            SELECT 1 FROM congregations candidate_congregation
            WHERE candidate_congregation.id=p_congregation
              AND candidate_congregation.district_id=p_district))
      ) AND (
        current_setting('app.is_system_worker',true)='true'
        OR EXISTS (SELECT 1 FROM users actor
          WHERE actor.sub=current_setting('app.current_user_sub',true) AND actor.is_superadmin)
        OR EXISTS (SELECT 1 FROM memberships actor_membership
          WHERE actor_membership.user_sub=current_setting('app.current_user_sub',true)
          AND actor_membership.role IN ({roles_at_least_sql(Role.PLANNER)})
          AND (
            (actor_membership.scope_type='DISTRICT' AND actor_membership.scope_id=p_district)
            OR (p_congregation IS NOT NULL
              AND actor_membership.scope_type='CONGREGATION'
              AND actor_membership.scope_id=p_congregation
              AND EXISTS (SELECT 1 FROM congregations c
                WHERE c.id=p_congregation AND c.district_id=p_district))
          ))
      )
      ORDER BY 1
    $$""",
    f"""CREATE FUNCTION personal_calendar_scopes(p_subject text,p_district uuid)
    RETURNS TABLE(role text,scope_type text,scope_id uuid)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT m.role::text,m.scope_type::text,m.scope_id
      FROM memberships m
      WHERE m.user_sub=p_subject
      AND (
        (m.scope_type='DISTRICT' AND m.scope_id=p_district)
        OR (m.scope_type='CONGREGATION' AND EXISTS (
          SELECT 1 FROM congregations c
          WHERE c.id=m.scope_id AND c.district_id=p_district))
      )
      AND (
        current_setting('app.is_system_worker',true)='true'
        OR p_subject=current_setting('app.current_user_sub',true)
        OR EXISTS (SELECT 1 FROM users actor
          WHERE actor.sub=current_setting('app.current_user_sub',true) AND actor.is_superadmin)
        OR EXISTS (SELECT 1 FROM memberships actor_membership
          WHERE actor_membership.user_sub=current_setting('app.current_user_sub',true)
          AND actor_membership.role IN ({roles_at_least_sql(Role.DISTRICT_ADMIN)})
          AND actor_membership.scope_type='DISTRICT'
          AND actor_membership.scope_id=p_district)
        OR EXISTS (SELECT 1 FROM export_tokens et
          WHERE et.token=current_setting('app.current_export_token',true)
          AND et.token_type='INTERNAL'
          AND et.subject_sub=p_subject
          AND et.district_id=p_district)
      )
      ORDER BY m.scope_type,m.scope_id,m.role
    $$""",
)


def _subject_slot_read(alias: str, assignment_alias: str | None = None) -> str:
    """Keep membership reads fast and constrain only subject-bound token reads."""
    subject_assignment = ""
    if assignment_alias is not None:
        subject_assignment = f"""AND EXISTS (SELECT 1 FROM leaders l
          WHERE l.id={assignment_alias}.leader_id AND l.user_sub=et.subject_sub)"""
    return f"""(
      {SUPERADMIN_SQL}
      OR {district_membership_sql(alias)}
      OR ({alias}.congregation_id IS NOT NULL AND {congregation_membership_sql(alias)})
      OR {distributed_slot_membership_sql(alias)}
      OR EXISTS (SELECT 1 FROM export_tokens et
        WHERE et.token=current_setting('app.current_export_token',true)
        AND et.district_id={alias}.district_id
        AND (et.congregation_id IS NULL OR et.congregation_id={alias}.congregation_id
          OR (et.congregation_id IS NOT NULL AND {alias}.congregation_id IS NULL
            AND ('all'=ANY({alias}.applicability)
              OR et.congregation_id::text=ANY({alias}.applicability))))
        AND (et.subject_sub IS NULL OR (
          duty_export_slot_allowed({alias}.id) {subject_assignment}
        )))
    )"""


def _subject_leader_read(alias: str = "leaders") -> str:
    return f"""(
      {leader_read_sql(alias)}
      OR EXISTS (SELECT 1 FROM export_tokens et
        WHERE et.token=current_setting('app.current_export_token',true)
        AND et.district_id={alias}.district_id
        AND ((et.subject_sub IS NULL AND
          (et.leader_id={alias}.id OR (et.leader_id IS NULL AND et.token_type='INTERNAL')))
          OR (et.subject_sub={alias}.user_sub
            AND duty_subject_scope(et.subject_sub,{alias}.district_id,{alias}.congregation_id))))
    )"""


def _replace_select_policy(op, table: str, policy: str, using: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute(f"CREATE POLICY {policy} ON {table} FOR SELECT USING {using}")


def _install_subject_feed_policies(op) -> None:
    """Integrate personal-token checks into export branches, not every row read."""
    _replace_select_policy(
        op,
        "planning_slots",
        "planning_slots_tenant_isolation_policy",
        _subject_slot_read("planning_slots"),
    )
    _replace_select_policy(
        op,
        "event_instances",
        "event_instances_tenant_isolation_policy",
        related_planning_slot_sql("event_instances", _subject_slot_read),
    )
    _replace_select_policy(
        op,
        "service_assignments",
        "service_assignments_tenant_isolation_policy",
        related_planning_slot_sql(
            "service_assignments",
            lambda alias: _subject_slot_read(alias, "service_assignments"),
        ),
    )
    _replace_select_policy(
        op,
        "leaders",
        "leaders_tenant_isolation_policy",
        _subject_leader_read(),
    )


def _restore_select_policies(op) -> None:
    """Restore the SELECT policies that preceded subject-bound duty feeds."""
    _replace_select_policy(
        op,
        "planning_slots",
        "planning_slots_tenant_isolation_policy",
        planning_slot_row_read_sql(),
    )
    for table in ("event_instances", "service_assignments"):
        _replace_select_policy(
            op,
            table,
            f"{table}_tenant_isolation_policy",
            related_planning_slot_sql(table, planning_slot_row_read_sql),
        )
    _replace_select_policy(
        op,
        "leaders",
        "leaders_tenant_isolation_policy",
        leader_row_read_sql(),
    )


def install_duty_policies(op) -> None:
    """Install independently scoped duties policies and personal feed restrictions."""
    op.execute("""CREATE FUNCTION duty_assignment_count(p_slot uuid,p_category uuid) RETURNS bigint
      LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT count(*) FROM event_duty_assignments da WHERE da.planning_slot_id=p_slot
        AND da.duty_category_id=p_category AND EXISTS (SELECT 1 FROM planning_slots ps
          WHERE ps.id=p_slot AND (
            current_setting('app.is_system_worker',true)='true'
            OR EXISTS (SELECT 1 FROM users u WHERE u.sub=current_setting('app.current_user_sub',true) AND u.is_superadmin)
            OR EXISTS (SELECT 1 FROM memberships m WHERE m.user_sub=current_setting('app.current_user_sub',true)
              AND m.role IN ({roles_at_least_sql(Role.VIEWER)})
              AND ((m.scope_type='DISTRICT' AND m.scope_id=ps.district_id)
                OR (m.scope_type='CONGREGATION' AND m.scope_id=ps.congregation_id)))))
      $$""")
    for sql in _FUNCTIONS:
        op.execute(sql)
    for table in _TABLES:
        read = _scope(table, inherited=table == "event_duty_categories")
        write = (
            _admin(table)
            if table in _ADMIN_TABLES
            else _scope(table, roles=roles_at_least_sql(Role.PLANNER))
        )
        if table == "event_duty_assignments":
            read = f"""({read}
              OR (linked_user_sub=current_duty_export_subject()
                AND duty_export_slot_allowed(planning_slot_id)
                AND EXISTS (SELECT 1 FROM planning_slots ps WHERE ps.id=planning_slot_id
                  AND ps.district_id=event_duty_assignments.district_id
                  AND ps.congregation_id IS NOT DISTINCT FROM event_duty_assignments.congregation_id))
              OR (linked_user_sub=current_setting('app.current_user_sub',true)
                AND EXISTS (SELECT 1 FROM planning_slots ps WHERE ps.id=planning_slot_id
                  AND ps.district_id=event_duty_assignments.district_id
                  AND ps.congregation_id IS NOT DISTINCT FROM event_duty_assignments.congregation_id
                  AND {distributed_slot_membership_sql("ps")})))"""
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING {read}")
        op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK {write}")
        op.execute(
            f"CREATE POLICY {table}_update ON {table} FOR UPDATE USING {write} WITH CHECK {write}"
        )
        op.execute(f"CREATE POLICY {table}_delete ON {table} FOR DELETE USING {write}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Subject checks live only in export-token branches of the established
    # SELECT policies. This avoids adding per-row restrictive-policy overhead
    # to normal authenticated planner and matrix queries.
    _install_subject_feed_policies(op)
    owner = """(subject_sub=current_setting('app.current_user_sub',true) AND token_type='INTERNAL'
      AND (duty_subject_scope(subject_sub,district_id,NULL) OR EXISTS (
        SELECT 1 FROM congregations c WHERE c.district_id=export_tokens.district_id
        AND duty_subject_scope(subject_sub,district_id,c.id))))"""
    op.execute(
        "CREATE POLICY export_tokens_subject_read ON export_tokens FOR SELECT USING (subject_sub=current_setting('app.current_user_sub',true))"
    )
    op.execute(
        f"CREATE POLICY export_tokens_subject_insert ON export_tokens FOR INSERT WITH CHECK {owner}"
    )
    # Ownership is sufficient for revocation even after loss of membership.
    op.execute(
        "CREATE POLICY export_tokens_subject_delete ON export_tokens FOR DELETE USING (subject_sub=current_setting('app.current_user_sub',true))"
    )
    _seed_defaults(op)


def _seed_defaults(op) -> None:
    # A trigger also covers future districts. Conflict handling preserves explicit
    # administrator settings and lets an upgrade/seed retry safely reuse records.
    trigger_values = ",\n          ".join(
        f"(gen_random_uuid(),NEW.id,NULL,{_sql_literal(code)},{_sql_literal(label)},"
        f"{_sql_array(categories)},true,1)"
        for code, label, categories in DEFAULT_DUTY_CATEGORIES
    )
    backfill_values = ",\n        ".join(
        f"({_sql_literal(code)},{_sql_literal(label)},{_sql_array(categories)})"
        for code, label, categories in DEFAULT_DUTY_CATEGORIES
    )
    op.execute(f"""CREATE FUNCTION seed_event_duty_defaults() RETURNS trigger
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
      BEGIN
        INSERT INTO event_duty_categories
          (id,district_id,congregation_id,code,label,event_categories,enabled,capacity)
        VALUES
          {trigger_values}
        ON CONFLICT DO NOTHING;
        RETURN NEW;
      END $$""")
    op.execute(
        "CREATE TRIGGER district_duty_defaults AFTER INSERT ON districts FOR EACH ROW EXECUTE FUNCTION seed_event_duty_defaults()"
    )
    op.execute(f"""INSERT INTO event_duty_categories
      (id,district_id,congregation_id,code,label,event_categories,enabled,capacity)
      SELECT gen_random_uuid(),d.id,NULL,v.code,v.label,v.categories,true,1
      FROM districts d CROSS JOIN (VALUES
        {backfill_values}) v(code,label,categories)
      ON CONFLICT DO NOTHING""")


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_array(values: tuple[str, ...]) -> str:
    entries = ",".join(_sql_literal(value) for value in values)
    return f"ARRAY[{entries}]::varchar(255)[]"


def remove_duty_policies(op) -> None:
    """Remove only policy/function additions from this revision."""
    op.execute("DROP TRIGGER district_duty_defaults ON districts")
    op.execute("DROP FUNCTION seed_event_duty_defaults()")
    for table in _TABLES:
        for action in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY {table}_{action} ON {table}")
    _restore_select_policies(op)
    for action in ("read", "insert", "delete"):
        op.execute(f"DROP POLICY export_tokens_subject_{action} ON export_tokens")
    for fn in (
        "duty_assignment_count(uuid,uuid)",
        "eligible_duty_users(uuid,uuid)",
        "personal_calendar_scopes(text,uuid)",
        "duty_export_slot_allowed(uuid)",
        "duty_export_is_subject_bound()",
        "current_duty_export_subject()",
        "duty_subject_scope(text,uuid,uuid)",
    ):
        op.execute(f"DROP FUNCTION {fn}")

