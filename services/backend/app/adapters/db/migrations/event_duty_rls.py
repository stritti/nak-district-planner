# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Versioned policy installation for the 20261013 additive duties migration.

Definer helpers return bounded booleans or the subject of the presented opaque
export token. They never return arbitrary account data and fix their search path.
"""

from __future__ import annotations

from app.adapters.db.migrations.rls_policies import SUPERADMIN_SQL

_TABLES = (
    "event_duty_categories",
    "event_type_duty_configurations",
    "duty_name_suggestions",
    "event_duty_assignments",
)


def _scope(alias: str, *, roles: str | None = None, inherited: bool = False) -> str:
    role_filter = (
        f"AND m.role IN ({roles})"
        if roles
        else "AND m.role IN ('VIEWER','PLANNER','CONGREGATION_ADMIN','DISTRICT_ADMIN')"
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
      AND ((m.scope_type='DISTRICT' AND m.scope_id={alias}.district_id AND m.role='DISTRICT_ADMIN')
        OR (m.scope_type='CONGREGATION' AND m.scope_id={alias}.congregation_id
            AND m.role IN ('CONGREGATION_ADMIN','DISTRICT_ADMIN')))))"""


_FUNCTIONS = (
    """CREATE FUNCTION duty_subject_scope(p_sub text, p_district uuid, p_congregation uuid)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT EXISTS (SELECT 1 FROM users u WHERE u.sub=p_sub AND (u.is_superadmin OR EXISTS (
        SELECT 1 FROM memberships m WHERE m.user_sub=u.sub
        AND m.role IN ('VIEWER','PLANNER','CONGREGATION_ADMIN','DISTRICT_ADMIN')
        AND ((m.scope_type='DISTRICT' AND m.scope_id=p_district)
          OR (p_congregation IS NOT NULL AND m.scope_type='CONGREGATION'
              AND m.scope_id=p_congregation AND EXISTS (
                SELECT 1 FROM congregations c WHERE c.id=p_congregation AND c.district_id=p_district)))
      )))
    $$""",
    """CREATE FUNCTION current_duty_export_subject() RETURNS text
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT COALESCE(et.subject_sub,l.user_sub) FROM export_tokens et
      LEFT JOIN leaders l ON l.id=et.leader_id AND l.district_id=et.district_id
      WHERE et.token=current_setting('app.current_export_token',true)
      AND et.token_type='INTERNAL' AND (et.subject_sub IS NOT NULL OR l.user_sub IS NOT NULL)
      AND (duty_subject_scope(COALESCE(et.subject_sub,l.user_sub),et.district_id,NULL)
        OR EXISTS (SELECT 1 FROM congregations c WHERE c.district_id=et.district_id
          AND duty_subject_scope(COALESCE(et.subject_sub,l.user_sub),et.district_id,c.id)))
    $$""",
    """CREATE FUNCTION duty_export_is_subject_bound() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT EXISTS (SELECT 1 FROM export_tokens et
        WHERE et.token=current_setting('app.current_export_token',true) AND et.subject_sub IS NOT NULL)
    $$""",
    """CREATE FUNCTION duty_export_slot_allowed(p_slot uuid) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT EXISTS (SELECT 1 FROM planning_slots ps JOIN export_tokens et ON et.district_id=ps.district_id
        WHERE ps.id=p_slot AND et.token=current_setting('app.current_export_token',true)
        AND current_duty_export_subject() IS NOT NULL
        AND duty_subject_scope(current_duty_export_subject(),ps.district_id,ps.congregation_id)
        AND (EXISTS (SELECT 1 FROM event_duty_assignments da WHERE da.planning_slot_id=ps.id
          AND da.district_id=ps.district_id AND da.congregation_id IS NOT DISTINCT FROM ps.congregation_id
          AND da.linked_user_sub=current_duty_export_subject())
        OR EXISTS (SELECT 1 FROM service_assignments sa JOIN leaders l ON l.id=sa.leader_id
          WHERE sa.planning_slot_id=ps.id AND l.district_id=ps.district_id
          AND l.user_sub=current_duty_export_subject())))
    $$""",
    """CREATE FUNCTION can_read_duty_membership(p_type text,p_scope uuid) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT EXISTS (SELECT 1 FROM memberships m
        WHERE m.user_sub=current_setting('app.current_user_sub',true)
        AND m.role IN ('PLANNER','CONGREGATION_ADMIN','DISTRICT_ADMIN')
        AND ((m.scope_type=p_type AND m.scope_id=p_scope)
          OR (m.scope_type='DISTRICT' AND p_type='CONGREGATION' AND EXISTS (
            SELECT 1 FROM congregations c WHERE c.id=p_scope AND c.district_id=m.scope_id))
          OR (m.scope_type='CONGREGATION' AND p_type='DISTRICT' AND EXISTS (
            SELECT 1 FROM congregations c WHERE c.id=m.scope_id AND c.district_id=p_scope))))
    $$""",
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
              AND m.role IN ('PLANNER','CONGREGATION_ADMIN','DISTRICT_ADMIN')
              AND ((m.scope_type='DISTRICT' AND m.scope_id=ps.district_id)
                OR (m.scope_type='CONGREGATION' AND m.scope_id=ps.congregation_id)))))
      $$""")
    for sql in _FUNCTIONS:
        op.execute(sql)
    for table in _TABLES:
        read = _scope(table, inherited=table == "event_duty_categories")
        write = (
            _admin(table)
            if table in _TABLES[:2]
            else _scope(table, roles="'PLANNER','CONGREGATION_ADMIN','DISTRICT_ADMIN'")
        )
        if table == "event_duty_assignments":
            read = f"""({read} OR (linked_user_sub=current_duty_export_subject()
              AND duty_export_slot_allowed(planning_slot_id)
              AND EXISTS (SELECT 1 FROM planning_slots ps WHERE ps.id=planning_slot_id
                AND ps.district_id=event_duty_assignments.district_id
                AND ps.congregation_id IS NOT DISTINCT FROM event_duty_assignments.congregation_id)))"""
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING {read}")
        op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK {write}")
        op.execute(
            f"CREATE POLICY {table}_update ON {table} FOR UPDATE USING {write} WITH CHECK {write}"
        )
        op.execute(f"CREATE POLICY {table}_delete ON {table} FOR DELETE USING {write}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Token possession grants only the bound subject's current scope and records.
    # RESTRICTIVE policies also constrain the pre-existing broad INTERNAL policies.
    restrictions = {
        "planning_slots": "duty_export_slot_allowed(id)",
        "event_instances": "duty_export_slot_allowed(planning_slot_id)",
        "service_assignments": "duty_export_slot_allowed(planning_slot_id) AND EXISTS (SELECT 1 FROM leaders l WHERE l.id=leader_id AND l.user_sub=current_duty_export_subject())",
        "leaders": "user_sub=current_duty_export_subject() AND duty_subject_scope(user_sub,district_id,congregation_id)",
    }
    for table, condition in restrictions.items():
        op.execute(
            f"CREATE POLICY {table}_subject_feed ON {table} AS RESTRICTIVE FOR SELECT USING ("
            "NULLIF(current_setting('app.current_export_token',true),'') IS NULL "
            f"OR NOT duty_export_is_subject_bound() OR ({condition}))"
        )
    op.execute("""CREATE POLICY memberships_duty_read ON memberships FOR SELECT USING (
      can_read_duty_membership(scope_type,scope_id)
      OR user_sub=current_duty_export_subject())""")
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
    op.execute("""CREATE FUNCTION seed_event_duty_defaults() RETURNS trigger
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
      BEGIN
        INSERT INTO event_duty_categories
          (id,district_id,congregation_id,code,label,event_categories,enabled,capacity)
        VALUES
          (gen_random_uuid(),NEW.id,NULL,'closing','Schließdienst','{}',true,1),
          (gen_random_uuid(),NEW.id,NULL,'organist','Organist',ARRAY['Gottesdienst'],true,1),
          (gen_random_uuid(),NEW.id,NULL,'conductor','Dirigent',ARRAY['Gottesdienst'],true,1)
        ON CONFLICT DO NOTHING;
        RETURN NEW;
      END $$""")
    op.execute(
        "CREATE TRIGGER district_duty_defaults AFTER INSERT ON districts FOR EACH ROW EXECUTE FUNCTION seed_event_duty_defaults()"
    )
    op.execute("""INSERT INTO event_duty_categories
      (id,district_id,congregation_id,code,label,event_categories,enabled,capacity)
      SELECT gen_random_uuid(),d.id,NULL,v.code,v.label,v.categories,true,1
      FROM districts d CROSS JOIN (VALUES
        ('closing','Schließdienst',ARRAY[]::varchar(255)[]),
        ('organist','Organist',ARRAY['Gottesdienst']::varchar(255)[]),
        ('conductor','Dirigent',ARRAY['Gottesdienst']::varchar(255)[])) v(code,label,categories)
      ON CONFLICT DO NOTHING""")


def remove_duty_policies(op) -> None:
    """Remove only policy/function additions from this revision."""
    op.execute("DROP TRIGGER district_duty_defaults ON districts")
    op.execute("DROP FUNCTION seed_event_duty_defaults()")
    for table in _TABLES:
        for action in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY {table}_{action} ON {table}")
    for table in ("planning_slots", "event_instances", "service_assignments", "leaders"):
        op.execute(f"DROP POLICY {table}_subject_feed ON {table}")
    op.execute("DROP POLICY memberships_duty_read ON memberships")
    for action in ("read", "insert", "delete"):
        op.execute(f"DROP POLICY export_tokens_subject_{action} ON export_tokens")
    for fn in (
        "duty_assignment_count(uuid,uuid)",
        "can_read_duty_membership(text,uuid)",
        "duty_export_slot_allowed(uuid)",
        "duty_export_is_subject_bound()",
        "current_duty_export_subject()",
        "duty_subject_scope(text,uuid,uuid)",
    ):
        op.execute(f"DROP FUNCTION {fn}")
