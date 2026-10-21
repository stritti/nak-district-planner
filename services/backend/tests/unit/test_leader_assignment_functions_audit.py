# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Audit snapshot of the SECURITY DEFINER predicates behind the leader policies (step 4).

They read ``leader_assignments`` for the policies without pulling that table's own policy
into every policy that reads ``leaders`` (which made the matrix query five times slower).
Each one answers a yes/no question; change them deliberately together with this file.
"""

from app.adapters.db.migrations import leader_assignment_rls as rls


def test_every_predicate_is_a_stable_definer_function_with_a_fixed_search_path():
    assert len(rls.FUNCTIONS) == len(rls.FUNCTION_NAMES) == 3
    for name, sql in zip(rls.FUNCTION_NAMES, rls.FUNCTIONS, strict=True):
        assert f"CREATE FUNCTION {name}(" in sql
        assert "RETURNS boolean" in sql
        assert "SECURITY DEFINER" in sql and "SET search_path=public,pg_temp" in sql
        assert " STABLE " in sql
        for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "EXECUTE ", "DROP ", "ALTER "):
            assert forbidden not in sql


def test_the_predicates_only_answer_about_the_caller_or_a_given_subject():
    member, assigned, scope = rls.FUNCTIONS
    assert "m.user_sub=current_setting('app.current_user_sub',true)" in member
    assert "m.scope_type='CONGREGATION'" in member
    assert "SELECT EXISTS" in member and "SELECT EXISTS" in assigned and "SELECT EXISTS" in scope
    assert "duty_subject_scope(p_sub,p_district,la.congregation_id)" in scope


def test_the_leader_policies_call_the_predicates_instead_of_reading_assignments_inline():
    for statement in rls.leader_policy_sql().values():
        assert "leader_assignments" not in statement
    read = rls.leader_policy_sql()["leaders_tenant_isolation_policy"]
    assert "leader_assignment_member(leaders.id, NULL::text[])" in read
    assert "leader_subject_scope(leaders.id, et.subject_sub, leaders.district_id)" in read
    update = rls.leader_policy_sql()["leaders_update_policy"]
    assert "leader_assigned_to(leaders.id, et.congregation_id)" in update
    assert "leader_assignment_member(leaders.id, ARRAY['DISTRICT_ADMIN','CONGREGATION_ADMIN','PLANNER']::text[])" in update
