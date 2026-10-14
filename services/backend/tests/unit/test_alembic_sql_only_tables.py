# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Tables created by migrations without an ORM model must be excluded from autogenerate."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
_ENV = _BACKEND / "alembic" / "env.py"
_ASSIGNMENT_UNIQUE = _BACKEND / "alembic" / "versions" / "20261007_assignment_unique.py"


def _sql_only_tables() -> set[str]:
    """Read ``_SQL_ONLY_TABLES`` from env.py without executing it (it needs an Alembic context)."""
    tree = ast.parse(_ENV.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_SQL_ONLY_TABLES" for t in node.targets
        ):
            return {elt.value for elt in node.value.args[0].elts}
    raise AssertionError("_SQL_ONLY_TABLES not found in alembic/env.py")


def test_duplicate_archive_is_not_dropped_by_autogenerate() -> None:
    """Without the exclusion `alembic check` reports drift and autogenerate would drop the archive."""
    spec = importlib.util.spec_from_file_location("assignment_unique", _ASSIGNMENT_UNIQUE)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.ARCHIVE_TABLE in _sql_only_tables()
