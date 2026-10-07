"""Regression tests for the directed backend architecture.

The application layer must not grow new dependencies on concrete adapters
(``app.adapters...``) or on the ORM (``sqlalchemy...``). Existing violations are
explicit technical debt and are frozen here *per imported module*, so that new
use cases - and new imports in legacy files - have to depend on domain ports.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "app" / "application"
FORBIDDEN_PREFIXES = ("app.adapters", "sqlalchemy")


class LegacyDebt(NamedTuple):
    rationale: str
    allowed_imports: frozenset[str]


def _debt(rationale: str, *imports: str) -> LegacyDebt:
    return LegacyDebt(rationale, frozenset(imports))


# RC-2 debt baseline. Do not add files or imports here for new code: introduce
# or extend a port under app.domain.ports and inject the concrete adapter at a
# composition boundary instead. Entries may only shrink as legacy code is
# refactored; an entry whose imports are gone must be removed (see tests below).
LEGACY_APPLICATION_ADAPTER_IMPORTS: dict[str, LegacyDebt] = {
    "audit_service.py": _debt(
        "legacy audit writer still constructs SQL repository and session adapters",
        "app.adapters.db.repositories.audit_log",
        "app.adapters.db.session",
        "sqlalchemy",
    ),
    "event_mail_hook_tasks.py": _debt(
        "Celery composition still constructs persistence adapters",
        "app.adapters.db.repositories.event_mail_hook",
        "app.adapters.db.session",
        "app.adapters.mail",
    ),
    "external_candidate_ingestion.py": _debt(
        "legacy ingestion orchestration still uses DB adapters",
        "app.adapters.db.locks",
        "app.adapters.db.repositories.planning_slot",
        "app.adapters.db.transactional_events",
        "sqlalchemy.ext.asyncio",
    ),
    "external_candidate_sync_adapter.py": _debt(
        "legacy sync bridge still reaches adapter implementations",
        "app.adapters.db.repositories.external_event_candidate",
        "app.adapters.db.repositories.notification",
    ),
    "feiertage_service.py": _debt(
        "legacy holiday import still works with persistence adapters",
        "app.adapters.db.repositories.event_instance",
        "app.adapters.db.repositories.planning_slot",
        "sqlalchemy.ext.asyncio",
    ),
    "init.py": _debt(
        "legacy role seeding still receives a SQLAlchemy session directly",
        "sqlalchemy.ext.asyncio",
    ),
    "invitation_service.py": _debt(
        "legacy invitation orchestration still reaches persistence adapters and API schemas",
        "app.adapters.api.schemas.invitation",
        "app.adapters.db.repositories.congregation",
        "app.adapters.db.repositories.event_instance",
        "app.adapters.db.repositories.invitation",
        "app.adapters.db.repositories.invitation_overwrite_request",
        "app.adapters.db.repositories.planning_slot",
        "sqlalchemy.ext.asyncio",
    ),
    "reminder_service.py": _debt(
        "legacy reminder orchestration still uses ORM/repository adapters",
        "app.adapters.db.orm_models.district",
        "app.adapters.db.orm_models.district_reminder_config",
        "app.adapters.db.orm_models.membership",
        "app.adapters.db.orm_models.user",
        "app.adapters.db.repositories.district_reminder_config",
        "sqlalchemy",
        "sqlalchemy.dialects.postgresql",
        "sqlalchemy.ext.asyncio",
    ),
    "reminder_tasks.py": _debt(
        "Celery composition currently lives in the application package",
        "app.adapters.db.session",
        "app.adapters.mail",
    ),
    "service_assignment_conflict.py": _debt(
        "legacy conflict orchestration still uses persistence adapters",
        "app.adapters.db.repositories.event_instance",
        "app.adapters.db.repositories.leader",
        "app.adapters.db.repositories.leader_unavailability",
        "app.adapters.db.repositories.planning_slot",
        "app.adapters.db.repositories.service_assignment",
        "sqlalchemy.ext.asyncio",
    ),
    "services/calendar_integration_service.py": _debt(
        "legacy application service consumes API request schemas directly",
        "app.adapters.api.schemas.calendar_integration",
    ),
    "slot_gap_tasks.py": _debt(
        "Celery composition currently lives in the application package",
        "app.adapters.db.repositories.slot_gap",
        "app.adapters.db.session",
        "app.adapters.db.transactional_events",
    ),
    "sync_service.py": _debt(
        "legacy sync orchestration still reaches calendar and persistence adapters",
        "app.adapters.calendar.caldav_connector",
        "app.adapters.calendar.google_connector",
        "app.adapters.calendar.ical_connector",
        "app.adapters.calendar.microsoft_connector",
        "app.adapters.db.repositories.calendar_integration",
        "app.adapters.db.repositories.event_instance",
        "app.adapters.db.repositories.external_event_link",
        "app.adapters.db.repositories.planning_slot",
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
    ),
    "tasks.py": _debt(
        "legacy Celery composition currently lives in the application package",
        "app.adapters.db.domain_audit",
        "app.adapters.db.orm_models.audit_log",
        "app.adapters.db.orm_models.planning_slot",
        "app.adapters.db.repositories.calendar_integration",
        "app.adapters.db.repositories.congregation",
        "app.adapters.db.repositories.district",
        "app.adapters.db.repositories.event_instance",
        "app.adapters.db.repositories.notification",
        "app.adapters.db.repositories.planning_series",
        "app.adapters.db.repositories.planning_slot",
        "app.adapters.db.session",
        "app.adapters.db.transactional_events",
        "app.adapters.version_check.cache",
        "app.adapters.version_check.ghcr",
        "sqlalchemy",
    ),
    "tenant_validation.py": _debt(
        "legacy tenant validation still queries persistence adapters",
        "app.adapters.db.orm_models.congregation",
        "app.adapters.db.orm_models.district",
        "app.adapters.db.orm_models.membership",
        "app.adapters.db.orm_models.user",
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
    ),
}


def _forbidden_imports(path: Path) -> set[str]:
    """Return the adapter/ORM modules imported anywhere in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return {m for m in modules if m == "sqlalchemy" or m.startswith(FORBIDDEN_PREFIXES)}


def scan(root: Path) -> dict[str, set[str]]:
    """Map each module below ``root`` (posix relative path) to its forbidden imports."""
    return {
        path.relative_to(root).as_posix(): imports
        for path in root.rglob("*.py")
        if (imports := _forbidden_imports(path))
    }


def new_violations(
    actual: dict[str, set[str]], allowlist: dict[str, LegacyDebt]
) -> dict[str, list[str]]:
    """Imports not covered by the allowlist. Unlisted files may import nothing forbidden."""
    violations = {}
    for path, imports in actual.items():
        allowed = allowlist[path].allowed_imports if path in allowlist else frozenset()
        if extra := sorted(imports - allowed):
            violations[path] = extra
    return violations


def test_application_layer_does_not_gain_new_adapter_dependencies() -> None:
    """No new file and no legacy file may add an app.adapters/sqlalchemy import."""
    violations = new_violations(scan(APPLICATION_ROOT), LEGACY_APPLICATION_ADAPTER_IMPORTS)

    assert not violations, (
        "New app.application -> app.adapters/sqlalchemy dependency detected. "
        "Define a domain port/interface and inject the adapter at the composition boundary instead: "
        f"{violations}"
    )


def test_legacy_allowlist_has_no_stale_entries() -> None:
    """Removed debt must be removed from the allowlist in the same change (spec: architecture-governance)."""
    actual = scan(APPLICATION_ROOT)
    stale = {
        path: sorted(debt.allowed_imports - actual.get(path, set()))
        for path, debt in LEGACY_APPLICATION_ADAPTER_IMPORTS.items()
        if debt.allowed_imports - actual.get(path, set())
    }
    assert not stale, f"Remove repaid architecture debt from the allowlist: {stale}"


def test_legacy_allowlist_has_actionable_rationales() -> None:
    """Every exception must explain why it is debt rather than silently normalising it."""
    invalid = sorted(
        path
        for path, debt in LEGACY_APPLICATION_ADAPTER_IMPORTS.items()
        if len(debt.rationale.strip()) < 20
    )
    assert not invalid, f"Architecture debt entries need an actionable rationale: {invalid}"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from app.adapters.db.session import get_session\n", ["app.adapters.db.session"]),
        (
            "from app.adapters.api.schemas.event import EventCreate\n",
            ["app.adapters.api.schemas.event"],
        ),
        ("import sqlalchemy\n", ["sqlalchemy"]),
    ],
)
def test_scanner_rejects_new_violations(tmp_path: Path, source: str, expected: list[str]) -> None:
    """Negative test: a new module, or a new import in a legacy module, is reported."""
    (tmp_path / "new_service.py").write_text(source, encoding="utf-8")
    (tmp_path / "legacy.py").write_text("import sqlalchemy\n" + source, encoding="utf-8")
    allowlist = {"legacy.py": _debt("legacy example rationale for this test", "sqlalchemy")}

    violations = new_violations(scan(tmp_path), allowlist)

    assert violations["new_service.py"] == expected
    assert violations.get("legacy.py", []) == [m for m in expected if m != "sqlalchemy"]


def test_scanner_accepts_port_based_module(tmp_path: Path) -> None:
    (tmp_path / "clean_service.py").write_text(
        "from app.domain.ports.repositories import EventRepository\n", encoding="utf-8"
    )
    assert new_violations(scan(tmp_path), {}) == {}
