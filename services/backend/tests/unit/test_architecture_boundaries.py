"""Architecture boundaries for the backend application layer.

The current RC still contains a small number of legacy infrastructure imports.
They are listed explicitly so that existing debt is visible while new
application code cannot deepen it. Removing an entry is always allowed once
that module has been migrated behind a domain port.
"""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
APPLICATION_ROOT = BACKEND_ROOT / "app" / "application"

# Legacy application modules that still reach into concrete adapters. Do not
# add new entries: migrate dependencies behind app.domain.ports instead.
LEGACY_ADAPTER_IMPORTS = frozenset(
    {
        "audit_service.py",
        "feiertage_service.py",
        "invitation_service.py",
        "reminder_service.py",
        "reminder_tasks.py",
        "slot_gap_tasks.py",
        "sync_service.py",
        "tasks.py",
        "tenant_validation.py",
    }
)

# Direct SQLAlchemy types are infrastructure concerns as well. These two
# existing modules are frozen until their DB concerns move behind ports.
LEGACY_SQLALCHEMY_IMPORTS = frozenset({"init.py", "reminder_service.py"})


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _files_importing(prefix: str) -> dict[str, set[str]]:
    imports: dict[str, set[str]] = {}
    for path in sorted(APPLICATION_ROOT.glob("*.py")):
        matching = {module for module in _imported_modules(path) if module.startswith(prefix)}
        if matching:
            imports[path.name] = matching
    return imports


def _assert_only_legacy_imports(prefix: str, allowlist: frozenset[str]) -> None:
    imports = _files_importing(prefix)
    unexpected = {name: modules for name, modules in imports.items() if name not in allowlist}
    stale = sorted(allowlist - imports.keys())

    assert not unexpected, (
        f"New application -> {prefix} dependency detected: {unexpected}. "
        "Depend on app.domain.ports instead of expanding the legacy allowlist."
    )
    assert not stale, f"Remove migrated modules from the legacy allowlist: {stale}"


def test_application_does_not_add_adapter_dependencies() -> None:
    _assert_only_legacy_imports("app.adapters", LEGACY_ADAPTER_IMPORTS)


def test_application_does_not_add_sqlalchemy_dependencies() -> None:
    _assert_only_legacy_imports("sqlalchemy", LEGACY_SQLALCHEMY_IMPORTS)
