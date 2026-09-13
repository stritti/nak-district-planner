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
    assert "UPDATE planning_slots duplicate" in cleanup_sql
    assert "SET status = 'CANCELLED'" in cleanup_sql
    assert "congregation_id" in cleanup_sql
    assert "planning_date" in cleanup_sql
    assert "planning_time" in cleanup_sql
    assert "status = 'ACTIVE'" in cleanup_sql
    assert calls[1][0] == "create_index"
