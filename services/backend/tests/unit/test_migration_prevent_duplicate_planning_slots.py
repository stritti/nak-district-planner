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

    setattr(migration, "op", FakeOp())

    migration.upgrade()

    assert calls[0][0] == "execute"
    cleanup_sql = str(calls[0][1])
    # Loser slots are deleted, not just cancelled
    assert "DELETE FROM planning_slots duplicate" in cleanup_sql
    assert "USING ranked" in cleanup_sql
    assert "WHERE duplicate.id = ranked.id" in cleanup_sql
    assert "ranked.id <> ranked.keep_id" in cleanup_sql
    # Service assignments: both event_id and planning_slot_id rewired
    assert "SET event_id = ranked.keep_id" in cleanup_sql
    assert "planning_slot_id = ranked.keep_id" in cleanup_sql
    assert "COALESCE(sa.planning_slot_id, sa.event_id) = ranked.id" in cleanup_sql
    # Congregation invitations: all three fields in single update
    assert "SET source_event_id = ranked.keep_id" in cleanup_sql
    assert "source_planning_slot_id = ranked.keep_id" in cleanup_sql
    assert "linked_event_id = ranked.keep_id" in cleanup_sql
    assert "COALESCE(ci.source_planning_slot_id, ci.source_event_id) = ranked.id" in cleanup_sql
    assert "ci.linked_event_id = ranked.id" in cleanup_sql
    # Invitation copies: invitation_source_event_id rewired
    assert "UPDATE planning_slots ps" in cleanup_sql
    assert "SET invitation_source_event_id = ranked.keep_id" in cleanup_sql
    assert "ps.invitation_source_event_id = ranked.id" in cleanup_sql
    assert calls[1][0] == "create_index"
