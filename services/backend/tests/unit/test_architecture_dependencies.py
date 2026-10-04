"""Architecture dependency tests.

The application layer still contains legacy infrastructure coupling. RC-2 does
not attempt a risky big-bang refactor; instead this test freezes the known debt
so every new application module must depend on domain/application ports rather
than concrete adapters. Entries should be removed from the allowlist whenever a
legacy module is refactored.
"""

from __future__ import annotations

import ast
from pathlib import Path

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "app" / "application"

LEGACY_APPLICATION_ADAPTER_DEPENDENCIES = {
    "audit_service.py",
    "event_mail_hook_tasks.py",
    "external_candidate_ingestion.py",
    "external_candidate_sync_adapter.py",
    "feiertage_service.py",
    "invitation_service.py",
    "reminder_service.py",
    "reminder_tasks.py",
    "service_assignment_conflict.py",
    "slot_gap_tasks.py",
    "sync_service.py",
    "tasks.py",
    "tenant_validation.py",
    "services/calendar_integration_service.py",
}


def _imports_adapters(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("app.adapters"):
            return True
        if isinstance(node, ast.Import) and any(
            alias.name.startswith("app.adapters") for alias in node.names
        ):
            return True
    return False


def test_application_layer_adds_no_new_adapter_dependencies() -> None:
    violations = {
        str(path.relative_to(APPLICATION_ROOT))
        for path in APPLICATION_ROOT.rglob("*.py")
        if _imports_adapters(path)
    }

    unexpected = violations - LEGACY_APPLICATION_ADAPTER_DEPENDENCIES
    assert not unexpected, (
        "New application->adapter dependencies are forbidden. Introduce a domain/application "
        f"port instead. Unexpected dependencies: {sorted(unexpected)}"
    )


def test_legacy_dependency_allowlist_contains_only_existing_modules() -> None:
    existing = {
        str(path.relative_to(APPLICATION_ROOT)) for path in APPLICATION_ROOT.rglob("*.py")
    }
    missing = LEGACY_APPLICATION_ADAPTER_DEPENDENCIES - existing
    assert not missing, f"Remove stale architecture allowlist entries: {sorted(missing)}"
