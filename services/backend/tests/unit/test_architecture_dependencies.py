"""Regression tests for the directed backend architecture.

The application layer must not grow new dependencies on concrete adapters.
Existing violations are explicit technical debt and are frozen here so that
new use cases have to depend on domain ports/interfaces instead.
"""

from __future__ import annotations

import ast
from pathlib import Path

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "app" / "application"

# RC-2 debt baseline. Do not add files here for new code: introduce or extend a
# port under app.domain.ports and inject the concrete adapter at a composition
# boundary instead. Entries may only disappear as legacy code is refactored.
LEGACY_APPLICATION_ADAPTER_FILES: dict[str, str] = {
    "audit_service.py": "legacy audit writer still constructs SQL repository and session adapters",
    "event_mail_hook_tasks.py": "Celery composition still constructs persistence adapters",
    "external_candidate_ingestion.py": "legacy ingestion orchestration still uses DB adapters",
    "external_candidate_sync_adapter.py": "legacy sync bridge still reaches adapter implementations",
    "feiertage_service.py": "legacy holiday import still works with persistence adapters",
    "invitation_service.py": "legacy invitation orchestration still reaches persistence adapters",
    "reminder_service.py": "legacy reminder orchestration still uses ORM/repository adapters",
    "reminder_tasks.py": "Celery composition currently lives in the application package",
    "service_assignment_conflict.py": "legacy conflict orchestration still uses persistence adapters",
    "services/calendar_integration_service.py": "legacy application service consumes API request schemas directly",
    "slot_gap_tasks.py": "Celery composition currently lives in the application package",
    "sync_service.py": "legacy sync orchestration still reaches persistence adapters",
    "tasks.py": "legacy Celery composition currently lives in the application package",
    "tenant_validation.py": "legacy tenant validation still queries persistence adapters",
}


def _adapter_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.adapters"):
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names if alias.name.startswith("app.adapters"))
    return imports


def _application_adapter_dependencies() -> dict[str, set[str]]:
    return {
        path.relative_to(APPLICATION_ROOT).as_posix(): imports
        for path in APPLICATION_ROOT.rglob("*.py")
        if (imports := _adapter_imports(path))
    }


def test_application_layer_does_not_gain_new_adapter_dependencies() -> None:
    """Only the documented RC-2 legacy files may import concrete adapters."""
    actual = _application_adapter_dependencies()
    unexpected = sorted(set(actual) - set(LEGACY_APPLICATION_ADAPTER_FILES))

    assert not unexpected, (
        "New app.application -> app.adapters dependency detected. "
        "Define a domain port/interface and inject the adapter at the composition boundary instead: "
        f"{unexpected}"
    )


def test_legacy_adapter_allowlist_only_references_existing_files() -> None:
    """Keep the debt register explicit and typo-free while it is reduced."""
    missing = sorted(
        path for path in LEGACY_APPLICATION_ADAPTER_FILES if not (APPLICATION_ROOT / path).is_file()
    )
    assert not missing, f"Remove stale architecture debt entries: {missing}"


def test_legacy_adapter_allowlist_has_actionable_rationales() -> None:
    """Every exception must explain why it is debt rather than silently normalising it."""
    invalid = sorted(
        path
        for path, rationale in LEGACY_APPLICATION_ADAPTER_FILES.items()
        if len(rationale.strip()) < 20
    )
    assert not invalid, f"Architecture debt entries need an actionable rationale: {invalid}"
