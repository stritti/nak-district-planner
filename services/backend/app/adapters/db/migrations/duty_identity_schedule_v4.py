# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Version 4 of the duty identity lookup: exact intervals and symmetric name matching.

Changes against version 3 (``duty_identity_schedule_v3.py``, frozen for the migration
history), prompted by the review of the duty overlap check:

* The window is a timestamp range. An event with an instance matches when its actual
  interval overlaps the window, so a moved or long-running event is found whatever its
  planning date; only events without an instance fall back to their planning date.
* ``strong`` reports how the match was made (account or leader), not what kind of row
  matched, so a typed name that hits an account-linked duty is a weak match.
* A typed name also matches the display names of account-linked and leader duties, so
  the namesake warning no longer depends on which duty was entered first.

Caller authorisation, the fixed search_path and the "schedule facts only" result are
unchanged. Pinned by ``tests/unit/test_duty_identity_schedule_audit.py``.
"""

from app.adapters.db.migrations.duty_identity_schedule_v2 import _CALLER_ALLOWED, FUNCTION_NAME
from app.adapters.db.migrations.duty_identity_schedule_v3 import _ACCOUNT_LEADERS

SIGNATURE = "uuid, text, text, uuid, uuid, timestamptz, timestamptz"

_WINDOW = """(
          (ei.id IS NOT NULL AND ei.actual_start_at<p_to AND ei.actual_end_at>p_from)
          OR (ei.id IS NULL AND ps.planning_date
            BETWEEN (p_from AT TIME ZONE 'UTC')::date AND (p_to AT TIME ZONE 'UTC')::date))"""

_NAME = "lower(regexp_replace(btrim({column}),'\\s+',' ','g'))=p_name"

FUNCTION_SQL = f"""CREATE FUNCTION {FUNCTION_NAME}(
      p_district uuid, p_sub text, p_name text, p_leader uuid, p_exclude_slot uuid,
      p_from timestamptz, p_to timestamptz)
    RETURNS TABLE(slot_id uuid, congregation_id uuid, planning_date date, planning_time time,
      actual_start_at timestamptz, actual_end_at timestamptz, strong boolean)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT ps.id, ps.congregation_id, ps.planning_date, ps.planning_time,
        ei.actual_start_at, ei.actual_end_at,
        ((p_sub IS NOT NULL AND (da.linked_user_sub=p_sub OR da.leader_id IN {_ACCOUNT_LEADERS}))
          OR (p_leader IS NOT NULL AND da.leader_id=p_leader))
      FROM event_duty_assignments da
      JOIN planning_slots ps ON ps.id=da.planning_slot_id
      LEFT JOIN event_instances ei ON ei.planning_slot_id=ps.id
      WHERE da.district_id=p_district
        AND da.planning_slot_id<>p_exclude_slot
        AND ps.status='ACTIVE'
        AND {_WINDOW}
        AND ((p_sub IS NOT NULL AND da.linked_user_sub=p_sub)
          OR (p_sub IS NOT NULL AND da.leader_id IN {_ACCOUNT_LEADERS})
          OR (p_leader IS NOT NULL AND da.leader_id=p_leader)
          OR (p_name IS NOT NULL AND (da.normalized_name=p_name
            OR (da.linked_user_sub IS NOT NULL AND {_NAME.format(column="da.display_name")})
            OR (da.leader_id IS NOT NULL AND EXISTS (SELECT 1 FROM leaders l
              WHERE l.id=da.leader_id AND {_NAME.format(column="l.name")})))))
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
        AND {_WINDOW}
        AND {_CALLER_ALLOWED}
    $$"""
