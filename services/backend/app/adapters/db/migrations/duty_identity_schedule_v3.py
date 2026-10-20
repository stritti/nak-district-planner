# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Version 3 of the duty identity lookup: an account also matches its linked leaders.

``p_sub`` now also finds duties and service assignments of every leader of the district
linked to that account. The lookup runs as definer, so leaders outside the caller's
leader RLS (another congregation of the district) count as well. Signature, caller
authorisation and the "schedule facts only" result are unchanged from version 2
(``duty_identity_schedule_v2.py``, which stays frozen for the migration history).
Pinned by ``tests/unit/test_duty_identity_schedule_audit.py``.
"""

from app.adapters.db.migrations.duty_identity_schedule_v2 import _CALLER_ALLOWED, FUNCTION_NAME

SIGNATURE = "uuid, text, text, uuid, uuid, date, date"

_ACCOUNT_LEADERS = (
    "(SELECT l.id FROM leaders l WHERE l.district_id=p_district AND l.user_sub=p_sub)"
)

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
          OR (p_sub IS NOT NULL AND da.leader_id IN {_ACCOUNT_LEADERS})
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
      WHERE ((p_leader IS NOT NULL AND sa.leader_id=p_leader)
          OR (p_sub IS NOT NULL AND sa.leader_id IN {_ACCOUNT_LEADERS}))
        AND ps.district_id=p_district
        AND ps.id<>p_exclude_slot
        AND ps.status='ACTIVE'
        AND ps.planning_date BETWEEN p_from AND p_to
        AND {_CALLER_ALLOWED}
    $$"""
