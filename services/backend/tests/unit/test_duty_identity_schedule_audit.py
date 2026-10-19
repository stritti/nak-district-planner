# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Audit snapshot of the SECURITY DEFINER lookup behind the duty overlap check (step 2.2c).

The function reads duties across congregations on behalf of planners who cannot read
them directly. Every property that keeps that safe is pinned here; change the function
deliberately together with this file.
"""

import re

from app.adapters.db.migrations.duty_identity_schedule import FUNCTION_NAME, FUNCTION_SQL


def test_is_a_stable_definer_function_with_a_fixed_search_path():
    assert f"CREATE FUNCTION {FUNCTION_NAME}(" in FUNCTION_SQL
    assert "SECURITY DEFINER" in FUNCTION_SQL
    assert "SET search_path=public,pg_temp" in FUNCTION_SQL
    assert " STABLE " in FUNCTION_SQL
    for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "EXECUTE ", "DROP ", "ALTER "):
        assert forbidden not in FUNCTION_SQL


def test_returns_schedule_facts_only_never_names_or_assignment_details():
    returns = FUNCTION_SQL[FUNCTION_SQL.index("RETURNS TABLE") : FUNCTION_SQL.index("LANGUAGE")]
    columns = re.findall(r"(\w+) (?:uuid|date|time|timestamptz|boolean)", returns)
    assert columns == [
        "slot_id", "congregation_id", "planning_date", "planning_time",
        "actual_start_at", "actual_end_at", "strong",
    ]
    for leaked in ("display_name", "normalized_name", "duty_label", "linked_user_sub,"):
        assert leaked not in returns


def test_only_planners_superadmins_and_workers_of_the_district_may_ask():
    caller = FUNCTION_SQL[FUNCTION_SQL.index("AND (\n          current_setting"):]
    assert "app.is_system_worker" in caller
    assert "u.is_superadmin" in caller
    assert "m.role IN ('DISTRICT_ADMIN','CONGREGATION_ADMIN','PLANNER')" in caller
    assert "'VIEWER'" not in caller
    assert "m.scope_type='DISTRICT' AND m.scope_id=p_district" in caller
    assert "c.id=m.scope_id AND c.district_id=p_district" in caller
    assert "current_setting('app.current_user_sub',true)" in caller


def test_results_stay_inside_the_requested_district_and_active_events():
    assert "da.district_id=p_district" in FUNCTION_SQL
    assert "ps.status='ACTIVE'" in FUNCTION_SQL
    assert "da.planning_slot_id<>p_exclude_slot" in FUNCTION_SQL


def test_name_matches_never_catch_linked_accounts():
    assert "da.linked_user_sub IS NULL AND da.normalized_name=p_name" in FUNCTION_SQL
