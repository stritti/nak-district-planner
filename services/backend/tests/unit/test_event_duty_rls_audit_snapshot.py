# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Audit snapshot of the nested duty RLS SECURITY DEFINER functions.

Every SECURITY DEFINER function installed by the duties migration is pinned
here so that future policy edits surface as explicit, reviewable test
failures instead of silent authorization drift. Each assertion documents an
invariant the personal duty feed relies on; update this file deliberately
alongside the migration.
"""

from inspect import getsource
from unittest.mock import Mock

from app.adapters.db.migrations import event_duty_rls

_FUNCTIONS_SQL = "\n".join(event_duty_rls._FUNCTIONS)

_EXPECTED_FUNCTIONS = (
    "duty_subject_scope",
    "current_duty_export_subject",
    "duty_export_is_subject_bound",
    "duty_export_slot_allowed",
    "eligible_duty_users",
    "personal_calendar_scopes",
)


def _install_sql() -> str:
    op = Mock()
    event_duty_rls.install_duty_policies(op)
    return "\n".join(str(call.args[0]) for call in op.execute.call_args_list)


def test_all_security_definer_functions_are_pinned():
    """Every DEFINER function, including duty_assignment_count, is audited."""
    sql = _install_sql()
    for name in (*_EXPECTED_FUNCTIONS, "duty_assignment_count"):
        assert f"CREATE FUNCTION {name}" in sql, f"missing function {name}"
    assert (
        len(event_duty_rls._FUNCTIONS) == len(_EXPECTED_FUNCTIONS)
    ), "update _EXPECTED_FUNCTIONS when adding a _FUNCTIONS entry"


def test_security_definer_functions_fix_search_path():
    """A DEFINER function without a fixed search_path allows privilege escalation."""
    sql = _install_sql()
    for name in (*_EXPECTED_FUNCTIONS, "duty_assignment_count", "seed_event_duty_defaults"):
        start = sql.index(f"CREATE FUNCTION {name}")
        end = sql.index("$$", start)
        definition = sql[start:end]
        assert "SECURITY DEFINER" in definition, name
        assert "SET search_path=public,pg_temp" in definition, name


def test_functions_are_stable_and_do_not_mutate():
    """STABLE must hold for every helper language, including plpgsql defaults."""
    sql = _install_sql()
    for name in (*_EXPECTED_FUNCTIONS, "duty_assignment_count"):
        start = sql.index(f"CREATE FUNCTION {name}")
        end = sql.index("$$", start)
        definition = sql[start:end]
        assert " STABLE " in definition, f"{name} must be STABLE"
        assert "INSERT " not in definition, name
        assert "UPDATE " not in definition, name
        assert "DELETE " not in definition, name


def test_duty_export_slot_allowed_checks_both_assignment_sources():
    sql = next(s for s in event_duty_rls._FUNCTIONS if "duty_export_slot_allowed" in s)
    assert "event_duty_assignments" in sql
    assert "service_assignments" in sql
    assert "duty_subject_scope(current_duty_export_subject()" in sql
    assert "linked_user_sub=current_duty_export_subject()" in sql
    assert "l.user_sub=current_duty_export_subject()" in sql


def test_current_duty_export_subject_only_returns_bound_subjects():
    sql = next(s for s in event_duty_rls._FUNCTIONS if "current_duty_export_subject" in s)
    assert "et.token_type='INTERNAL'" in sql
    assert "duty_subject_scope" in sql


def test_eligible_duty_users_actor_check_is_planner_scoped():
    """The actor (not the candidate) must be planner-or-higher in the requested scope."""
    sql = next(s for s in event_duty_rls._FUNCTIONS if "eligible_duty_users" in s)
    assert "actor.is_superadmin" in sql
    assert "actor_membership.role" in sql
    assert "actor_membership.scope_type='DISTRICT'" in sql
    assert "actor_membership.scope_type='CONGREGATION'" in sql
    assert "actor_membership.scope_id=p_district" in sql
    assert "actor_membership.scope_id=p_congregation" in sql
    assert "candidate_congregation.district_id=p_district" in sql


def test_assignment_read_restricts_subject_bound_tokens_to_matching_slots():
    sql = _install_sql()
    read_policy = sql[
        sql.index("CREATE POLICY event_duty_assignments_select") : sql.index(
            "CREATE POLICY event_duty_assignments_insert"
        )
    ]
    assert "current_duty_export_subject()" in read_policy
    assert "duty_export_slot_allowed(planning_slot_id)" in read_policy
    assert (
        "ps.congregation_id IS NOT DISTINCT FROM event_duty_assignments.congregation_id"
        in read_policy
    )


def test_export_token_owner_policies_are_subject_scoped_individually():
    """Each owner policy must contain the subject predicate on its own."""
    sql = _install_sql()

    read_policy = sql[
        sql.index("CREATE POLICY export_tokens_subject_read") : sql.index(
            "CREATE POLICY export_tokens_subject_insert"
        )
    ]
    delete_policy = sql[sql.index("CREATE POLICY export_tokens_subject_delete") :]
    insert_policy = sql[
        sql.index("CREATE POLICY export_tokens_subject_insert") : sql.index(
            "CREATE POLICY export_tokens_subject_delete"
        )
    ]

    subject_predicate = "subject_sub=current_setting('app.current_user_sub',true)"
    assert subject_predicate in read_policy
    assert subject_predicate in delete_policy
    assert "duty_subject_scope(subject_sub,district_id,NULL)" in insert_policy


def test_subject_slot_read_keeps_distributed_slot_membership_constraint():
    """Personal feeds must not leak slots distributed to congregations the subject left."""
    source = getsource(event_duty_rls._subject_slot_read)
    assert "duty_export_slot_allowed" in source
    assert "et.subject_sub IS NULL OR" in source
    assert "distributed_slot_membership_sql" in getsource(
        event_duty_rls.install_duty_policies
    ) or "distributed_slot_membership_sql" in source
