"""Focused safety checks for generated RLS policy SQL."""

from __future__ import annotations

from app.adapters.db.migrations.rls_policies import get_all_rls_sql, get_rls_sql


def test_rls_sql_does_not_reference_missing_invitation_overwrite_columns() -> None:
    sql = "\n".join(get_all_rls_sql())

    assert "invitation_overwrite_requests.source_congregation_id" not in sql
    assert "invitation_overwrite_requests.target_congregation_id" not in sql
    assert "invitation_overwrite_requests.source_planning_slot_id" not in sql
    assert "ci.source_congregation_id" in sql


def test_membership_write_policies_do_not_query_memberships_recursively() -> None:
    sql = "\n".join(get_rls_sql("memberships"))

    for policy_name in (
        "memberships_insert_policy",
        "memberships_update_policy",
        "memberships_delete_policy",
    ):
        policy_sql = sql[sql.index(policy_name) :]
        next_create = policy_sql.find("CREATE POLICY", 1)
        if next_create != -1:
            policy_sql = policy_sql[:next_create]
        assert "FROM memberships m" not in policy_sql
        assert "can_admin_membership(" in policy_sql


def test_export_token_and_registration_policy_branches_exist() -> None:
    sql = "\n".join(get_all_rls_sql())

    assert "CREATE POLICY export_tokens_select_policy" in sql
    assert "app.current_export_token" in sql
    assert "CREATE POLICY export_tokens_insert_policy" in sql
    assert "CREATE POLICY export_tokens_update_policy" in sql
    assert "CREATE POLICY export_tokens_delete_policy" in sql
    assert "leader_registrations.user_sub = current_setting('app.current_user_sub', true)" in sql
