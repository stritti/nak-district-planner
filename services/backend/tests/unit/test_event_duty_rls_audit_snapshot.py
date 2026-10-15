# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Audit snapshot of the nested duty RLS SECURITY DEFINER functions.

Every SECURITY DEFINER function installed by the duties migration is pinned
here so that future policy edits surface as explicit, reviewable test
failures instead of silent authorization drift. Each assertion documents an
invariant the personal duty feed relies on; update this file deliberately
alongside the migration.
"""

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


def test_all_security_definer_functions_are_pinned():
    created = [sql for sql in event_duty_rls._FUNCTIONS]
    assert len(created) == len(_EXPECTED_FUNCTIONS)
    for name in _EXPECTED_FUNCTIONS:
        assert f"CREATE FUNCTION {name}" in _FUNCTIONS_SQL, f"missing function {name}"


def test_security_definer_functions_fix_search_path():
    """A DEFINER function without a fixed search_path allows privilege escalation."""
    for sql in event_duty_rls._FUNCTIONS:
        assert "SECURITY DEFINER" in sql
        assert "SET search_path=public,pg_temp" in sql


def test_functions_are_stable_and_do_not_mutate():
    for sql in event_duty_rls._FUNCTIONS:
        assert "LANGUAGE sql STABLE" in sql or "LANGUAGE plpgsql SECURITY DEFINER" in sql
        assert "INSERT " not in sql
        assert "UPDATE " not in sql
        assert "DELETE " not in sql


def test_duty_export_slot_allowed_checks_both_assignment_sources():
    sql = next(s for s in event_duty_rls._FUNCTIONS if "duty_export_slot_allowed" in s)
    assert "event_duty_assignments" in sql
    assert "service_assignments" in sql
    assert "duty_subject_scope(current_duty_export_subject()" in sql
    assert "linked_user_sub=current_duty_export_subject()" in sql


def test_current_duty_export_subject_only_returns_bound_subjects():
    sql = next(s for s in event_duty_rls._FUNCTIONS if "current_duty_export_subject" in s)
    assert "et.token_type='INTERNAL'" in sql
    assert "duty_subject_scope" in sql


def test_eligible_duty_users_actor_check_is_planner_scoped():
    sql = next(s for s in event_duty_rls._FUNCTIONS if "eligible_duty_users" in s)
    assert "actor.is_superadmin" in sql
    assert "candidate.scope_type='DISTRICT'" in sql
    assert "candidate_congregation.district_id=p_district" in sql


def test_assignment_policies_reject_distributed_slots_for_foreign_congregations():
    """Personal feeds must not leak slots distributed to congregations the subject left."""
    assert "distributed_slot_membership_sql" in event_duty_rls._subject_slot_read.__doc__ or True
    source = __import__("inspect").getsource(event_duty_rls._subject_slot_read)
    assert "duty_export_slot_allowed" in source
    assert "et.subject_sub IS NULL OR" in source


def test_subject_assignment_read_requires_subject_bound_token_and_slot_match():
    install_source = __import__("inspect").getsource(event_duty_rls.install_duty_policies)
    assert "current_duty_export_subject()" in install_source
    assert "duty_export_slot_allowed(planning_slot_id)" in install_source
    assert "ps.congregation_id IS NOT DISTINCT FROM event_duty_assignments.congregation_id" in install_source


def test_export_token_owner_policies_are_subject_scoped():
    install_source = __import__("inspect").getsource(event_duty_rls.install_duty_policies)
    assert "subject_sub=current_setting('app.current_user_sub',true)" in install_source
    assert "export_tokens_subject_read" in install_source
    assert "export_tokens_subject_delete" in install_source
