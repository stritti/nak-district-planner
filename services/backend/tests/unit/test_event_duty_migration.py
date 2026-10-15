# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Contract checks for the additive duties migration and its privacy policies."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch


def migration():
    path = Path(__file__).parents[2] / "alembic/versions/20261013_event_duties.py"
    spec = importlib.util.spec_from_file_location("duty_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_is_additive_and_keeps_leader_active_state():
    module = migration()
    with patch.object(module, "op", Mock()) as op:
        module.upgrade()
    sql = "\n".join(str(call.args[0]) for call in op.execute.call_args_list)
    assert "UPDATE leaders" not in sql
    assert "CREATE TABLE event_duty_assignments" in sql
    assert "uq_duty_assignment_subject" in sql
    assert "uq_duty_assignment_name" in sql
    assert "NULLS NOT DISTINCT" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "DROP POLICY IF EXISTS service_assignments_tenant_isolation_policy" in sql
    assert "duty_export_slot_allowed(ps.id)" in sql
    assert "CREATE FUNCTION eligible_duty_users" in sql
    assert "candidate.scope_id=p_congregation AND EXISTS" in sql
    assert "m.scope_id::text = ANY(planning_slots.applicability)" in sql
    assert "linked_user_sub=current_setting('app.current_user_sub',true)" in sql
    assert "m.scope_id::text = ANY(ps.applicability)" in sql
    assert "memberships_duty_read" not in sql
    assert "AS RESTRICTIVE" not in sql
    assert "service_assignments" not in "\n".join(
        str(call) for call in op.drop_table.call_args_list
    )


def test_downgrade_only_removes_new_fields_and_tables():
    module = migration()
    with patch.object(module, "op", Mock()) as op:
        module.downgrade()
    columns = [call.args for call in op.drop_column.call_args_list]
    assert ("leaders", "hidden_from_lists") in columns
    assert ("leaders", "service_end_date") in columns
    assert ("leaders", "is_active") not in columns
    assert ("export_tokens", "subject_sub") in columns
