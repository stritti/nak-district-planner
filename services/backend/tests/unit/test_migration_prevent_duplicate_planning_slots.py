from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_migration() -> ModuleType:
    migration_path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "0ea121ae36ad_prevent_duplicate_active_planning_slots_.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0ea121ae36ad", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_reconciles_duplicate_active_slots_before_creating_unique_index() -> None:
    migration = _load_migration()
    calls: list[tuple[str, object]] = []

    class FakeOp:
        def execute(self, statement: object) -> None:
            calls.append(("execute", statement))

        def create_index(self, *args: object, **kwargs: object) -> None:
            calls.append(("create_index", {"args": args, "kwargs": kwargs}))

    migration.op = FakeOp()

    migration.upgrade()

    assert [call[0] for call in calls] == [
        "execute",
        "execute",
        "execute",
        "execute",
        "execute",
        "execute",
        "create_index",
    ]

    ambiguous_duplicates_sql = str(calls[0][1])
    service_assignments_sql = str(calls[1][1])
    invitations_sql = str(calls[2][1])
    invitation_copies_sql = str(calls[3][1])
    overwrite_requests_sql = str(calls[4][1])
    delete_losers_sql = str(calls[5][1])

    assert "COUNT(ei.id) > 1" in ambiguous_duplicates_sql
    assert "RAISE EXCEPTION" in ambiguous_duplicates_sql

    assert "SET event_id = ranked.keep_id" in service_assignments_sql
    assert "planning_slot_id = ranked.keep_id" in service_assignments_sql
    assert "COALESCE(sa.planning_slot_id, sa.event_id) = ranked.id" in service_assignments_sql

    assert "SELECT ranked.keep_id FROM ranked WHERE ranked.id = ci.source_event_id" in invitations_sql
    assert (
        "SELECT ranked.keep_id FROM ranked WHERE ranked.id = ci.source_planning_slot_id"
        in invitations_sql
    )
    assert "SELECT ranked.keep_id FROM ranked WHERE ranked.id = ci.linked_event_id" in invitations_sql
    assert "FROM ranked\nWHERE ranked.id <> ranked.keep_id" not in invitations_sql

    assert "UPDATE planning_slots ps" in invitation_copies_sql
    assert "SET invitation_source_event_id = ranked.keep_id" in invitation_copies_sql
    assert "ps.invitation_source_event_id = ranked.id" in invitation_copies_sql

    assert "UPDATE invitation_overwrite_requests ior" in overwrite_requests_sql
    assert (
        "SELECT ranked.keep_id FROM ranked WHERE ranked.id = ior.source_event_id"
        in overwrite_requests_sql
    )
    assert (
        "SELECT ranked.keep_id FROM ranked WHERE ranked.id = ior.target_event_id"
        in overwrite_requests_sql
    )
    assert "FROM ranked\nWHERE ranked.id <> ranked.keep_id" not in overwrite_requests_sql

    assert "DELETE FROM planning_slots duplicate" in delete_losers_sql
    assert "NOT EXISTS" in delete_losers_sql
    assert "event_instances ei" in delete_losers_sql
    assert calls[6][0] == "create_index"
