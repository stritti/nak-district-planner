# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SECURITY DEFINER lookup of a person's other duties for the overlap check (step 2.2c).

Row-level security hides duties of other congregations from a congregation planner,
so a plain query cannot see that the same organist is already booked elsewhere. This
function answers only that question: it returns the schedule facts (event, congregation,
time window, match strength) of the other duties of one account or normalised name,
never names or assignment details, and only to callers who may plan duties in the
district. The text is frozen by ``tests/unit/test_duty_identity_schedule_audit.py``.
"""

from app.domain.models.role import Role, roles_at_least_sql

FUNCTION_NAME = "duty_identity_schedule"

FUNCTION_SQL = f"""CREATE FUNCTION {FUNCTION_NAME}(
      p_district uuid, p_sub text, p_name text, p_exclude_slot uuid, p_from date, p_to date)
    RETURNS TABLE(slot_id uuid, congregation_id uuid, planning_date date, planning_time time,
      actual_start_at timestamptz, actual_end_at timestamptz, strong boolean)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT ps.id, ps.congregation_id, ps.planning_date, ps.planning_time,
        ei.actual_start_at, ei.actual_end_at, (da.linked_user_sub IS NOT NULL)
      FROM event_duty_assignments da
      JOIN planning_slots ps ON ps.id=da.planning_slot_id
      LEFT JOIN event_instances ei ON ei.planning_slot_id=ps.id
      WHERE da.district_id=p_district
        AND da.planning_slot_id<>p_exclude_slot
        AND ps.status='ACTIVE'
        AND ps.planning_date BETWEEN p_from AND p_to
        AND ((p_sub IS NOT NULL AND da.linked_user_sub=p_sub)
          OR (p_name IS NOT NULL AND da.linked_user_sub IS NULL AND da.normalized_name=p_name))
        AND (
          current_setting('app.is_system_worker',true)='true'
          OR EXISTS (SELECT 1 FROM users u
            WHERE u.sub=current_setting('app.current_user_sub',true) AND u.is_superadmin)
          OR EXISTS (SELECT 1 FROM memberships m
            WHERE m.user_sub=current_setting('app.current_user_sub',true)
              AND m.role IN ({roles_at_least_sql(Role.PLANNER)})
              AND ((m.scope_type='DISTRICT' AND m.scope_id=p_district)
                OR (m.scope_type='CONGREGATION' AND EXISTS (SELECT 1 FROM congregations c
                  WHERE c.id=m.scope_id AND c.district_id=p_district)))))
    $$"""
