# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Version 2 of the duty identity lookup: also matches a leader (step 2.2b).

Adds ``p_leader``: duties that reference the leader and the leader's service
assignments count as strong matches, so duties and service leadership are checked
against each other. Everything else, including the authorisation of the caller and
the "schedule facts only" result, is unchanged from version 1
(``duty_identity_schedule.py``, which stays frozen for the migration history).
Pinned by ``tests/unit/test_duty_identity_schedule_audit.py``.
"""

from app.domain.models.role import Role, roles_at_least_sql

FUNCTION_NAME = "duty_identity_schedule"
V1_SIGNATURE = "uuid, text, text, uuid, date, date"

_CALLER_ALLOWED = f"""(
          current_setting('app.is_system_worker',true)='true'
          OR EXISTS (SELECT 1 FROM users u
            WHERE u.sub=current_setting('app.current_user_sub',true) AND u.is_superadmin)
          OR EXISTS (SELECT 1 FROM memberships m
            WHERE m.user_sub=current_setting('app.current_user_sub',true)
              AND m.role IN ({roles_at_least_sql(Role.PLANNER)})
              AND ((m.scope_type='DISTRICT' AND m.scope_id=p_district)
                OR (m.scope_type='CONGREGATION' AND EXISTS (SELECT 1 FROM congregations c
                  WHERE c.id=m.scope_id AND c.district_id=p_district)))))"""

FUNCTION_SQL = f"""CREATE FUNCTION {FUNCTION_NAME}(
      p_district uuid, p_sub text, p_name text, p_leader uuid, p_exclude_slot uuid,
      p_from date, p_to date)
    RETURNS TABLE(slot_id uuid, congregation_id uuid, planning_date date, planning_time time,
      actual_start_at timestamptz, actual_end_at timestamptz, strong boolean)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT ps.id, ps.congregation_id, ps.planning_date, ps.planning_time,
        ei.actual_start_at, ei.actual_end_at,
        (da.linked_user_sub IS NOT NULL OR da.leader_id IS NOT NULL)
      FROM event_duty_assignments da
      JOIN planning_slots ps ON ps.id=da.planning_slot_id
      LEFT JOIN event_instances ei ON ei.planning_slot_id=ps.id
      WHERE da.district_id=p_district
        AND da.planning_slot_id<>p_exclude_slot
        AND ps.status='ACTIVE'
        AND ps.planning_date BETWEEN p_from AND p_to
        AND ((p_sub IS NOT NULL AND da.linked_user_sub=p_sub)
          OR (p_leader IS NOT NULL AND da.leader_id=p_leader)
          OR (p_name IS NOT NULL AND da.linked_user_sub IS NULL AND da.leader_id IS NULL
            AND da.normalized_name=p_name))
        AND {_CALLER_ALLOWED}
      UNION ALL
      SELECT ps.id, ps.congregation_id, ps.planning_date, ps.planning_time,
        ei.actual_start_at, ei.actual_end_at, true
      FROM service_assignments sa
      JOIN planning_slots ps ON ps.id=COALESCE(sa.planning_slot_id,sa.event_id)
      LEFT JOIN event_instances ei ON ei.planning_slot_id=ps.id
      WHERE p_leader IS NOT NULL AND sa.leader_id=p_leader
        AND ps.district_id=p_district
        AND ps.id<>p_exclude_slot
        AND ps.status='ACTIVE'
        AND ps.planning_date BETWEEN p_from AND p_to
        AND {_CALLER_ALLOWED}
    $$"""
