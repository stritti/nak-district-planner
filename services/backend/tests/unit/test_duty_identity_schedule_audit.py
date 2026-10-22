# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Audit snapshot of the SECURITY DEFINER lookup behind the duty overlap check (step 2.2c).

The function reads duties across congregations on behalf of planners who cannot read
them directly. Every property that keeps that safe is pinned here; change the function
deliberately together with this file.
"""

import re

from app.adapters.db.migrations.duty_identity_schedule_v4 import FUNCTION_NAME, FUNCTION_SQL


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
    # Both branches (duties and the leader's service assignments) carry the same check.
    assert FUNCTION_SQL.count("current_setting('app.is_system_worker',true)='true'") == 2
    assert FUNCTION_SQL.count("u.is_superadmin") == 2
    assert FUNCTION_SQL.count("m.role IN ('DISTRICT_ADMIN','CONGREGATION_ADMIN','PLANNER')") == 2
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


def test_name_matches_are_weak_and_reach_every_identity_kind():
    """A typed name also hits account and leader duties, but never makes the match strong."""
    assert "da.normalized_name=p_name" in FUNCTION_SQL
    assert "da.linked_user_sub IS NOT NULL AND lower(regexp_replace(btrim(da.display_name)" in FUNCTION_SQL
    assert "l.id=da.leader_id AND lower(regexp_replace(btrim(l.name)" in FUNCTION_SQL
    strong = FUNCTION_SQL[FUNCTION_SQL.index("ei.actual_end_at,\n        (") : FUNCTION_SQL.index("FROM event_duty_assignments")]
    assert "p_name" not in strong
    assert "da.linked_user_sub IS NOT NULL OR" not in strong


def test_events_with_an_instance_match_by_their_actual_interval():
    window = FUNCTION_SQL[FUNCTION_SQL.index("ei.id IS NOT NULL AND"):FUNCTION_SQL.index("ei.id IS NULL AND")]
    assert "ei.actual_start_at<p_to AND ei.actual_end_at>p_from" in window
    # Only events without an instance fall back to the (coarser) planning date.
    assert FUNCTION_SQL.count("ei.id IS NULL AND ps.planning_date") == 2
    assert FUNCTION_SQL.count("ei.actual_start_at<p_to AND ei.actual_end_at>p_from") == 2
    assert "p_from timestamptz, p_to timestamptz" in FUNCTION_SQL


def test_the_service_assignment_branch_is_restricted_to_the_district_and_the_leader():
    branch = FUNCTION_SQL[FUNCTION_SQL.index("UNION ALL"):]
    assert "p_leader IS NOT NULL AND sa.leader_id=p_leader" in branch
    assert "ps.district_id=p_district" in branch
    assert "ps.status='ACTIVE'" in branch
    assert "ps.id<>p_exclude_slot" in branch


def test_version_3_stays_frozen_for_the_migration_history():
    from app.adapters.db.migrations import duty_identity_schedule_v3 as v3

    assert "p_from date, p_to date" in v3.FUNCTION_SQL
    assert "(da.linked_user_sub IS NOT NULL OR da.leader_id IS NOT NULL)" in v3.FUNCTION_SQL


def test_version_1_stays_frozen_for_the_migration_history():
    from app.adapters.db.migrations import duty_identity_schedule as v1

    assert "p_exclude_slot uuid, p_from date, p_to date)" in v1.FUNCTION_SQL
    assert "p_leader" not in v1.FUNCTION_SQL


def test_an_account_reaches_only_leaders_of_the_requested_district():
    assert FUNCTION_SQL.count(
        "(SELECT l.id FROM leaders l WHERE l.district_id=p_district AND l.user_sub=p_sub)"
    ) == 3  # strength flag, duty match, service branch
    assert FUNCTION_SQL.count("p_sub IS NOT NULL AND") == 4
