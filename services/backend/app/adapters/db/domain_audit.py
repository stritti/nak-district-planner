# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Domain audit hooks: record governance-relevant changes in the same transaction.

The HTTP ``AuditMiddleware`` only knows that a request hit a route. This hook
records *what* changed on the audited aggregates (planning slots, service
assignments, calendar integrations, export tokens), including changes made by
Celery tasks, with old and new values of whitelisted fields.

It runs in ``after_flush`` and inserts into ``audit_logs`` on the flushing
connection, so an entry exists exactly when the change commits. Every actor
allowed to write an audited row passes the ``audit_logs`` insert policy,
because the entry carries the row's district and congregation.

Secrets never reach the log: credential and token columns are only reported by
name under ``changes.redacted_fields``.
"""

from __future__ import annotations

import enum
import logging
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import insert, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.util import identity_key

from app.adapters.db.orm_models.audit_log import AuditAction, AuditLogORM, AuditStatus
from app.adapters.db.orm_models.calendar_integration import CalendarIntegrationORM
from app.adapters.db.orm_models.export_token import ExportTokenORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.tenant import TenantContext

logger = logging.getLogger(__name__)

AUDIT_SOURCE = "domain"

Tenant = tuple[uuid.UUID | None, uuid.UUID | None]


def _own_tenant(_: Session, row: Any) -> Tenant:
    return row.district_id, row.congregation_id


def _planning_slot_tenant(session: Session, row: ServiceAssignmentORM) -> Tenant:
    """Assignments inherit their tenant from the planning slot they belong to."""
    slot_id = row.planning_slot_id or row.event_id
    if slot_id is None:
        return None, None
    slot = session.identity_map.get(identity_key(PlanningSlotORM, slot_id))
    if slot is not None:
        return slot.district_id, slot.congregation_id
    found = session.connection().execute(
        select(PlanningSlotORM.district_id, PlanningSlotORM.congregation_id).where(
            PlanningSlotORM.id == slot_id
        )
    )
    tenant = found.first()
    return (tenant.district_id, tenant.congregation_id) if tenant else (None, None)


@dataclass(frozen=True)
class AuditedResource:
    resource_type: str
    fields: tuple[str, ...]
    tenant: Callable[[Session, Any], Tenant]
    redacted: tuple[str, ...] = ()


AUDITED_RESOURCES: dict[type, AuditedResource] = {
    PlanningSlotORM: AuditedResource(
        "planning_slot",
        (
            "title",
            "category",
            "planning_date",
            "planning_time",
            "status",
            "approval_status",
            "applicability",
            "congregation_id",
        ),
        _own_tenant,
    ),
    ServiceAssignmentORM: AuditedResource(
        "service_assignment",
        ("planning_slot_id", "leader_id", "leader_name", "status"),
        _planning_slot_tenant,
    ),
    # Sync bookkeeping (last_synced_at, last_sync_error) is deliberately not
    # audited: it changes on every run and is not a governance decision.
    CalendarIntegrationORM: AuditedResource(
        "calendar_integration",
        (
            "name",
            "type",
            "sync_interval",
            "capabilities",
            "is_active",
            "default_category",
            "delete_behavior",
            "congregation_id",
        ),
        _own_tenant,
        redacted=("credentials_enc",),
    ),
    ExportTokenORM: AuditedResource(
        "export_token",
        ("label", "token_type", "congregation_id", "leader_id"),
        _own_tenant,
        redacted=("token",),
    ),
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value


def _snapshot(row: Any, fields: Iterable[str]) -> dict[str, Any]:
    return {name: _jsonable(getattr(row, name)) for name in fields}


def _changed(row: Any, names: Iterable[str]) -> dict[str, tuple[Any, Any]]:
    """Old and new value of every attribute modified since the row was loaded."""
    attrs = inspect(row).attrs
    changed: dict[str, tuple[Any, Any]] = {}
    for name in names:
        history = attrs[name].history
        if not history.has_changes():
            continue
        old = history.deleted[0] if history.deleted else None
        new = history.added[0] if history.added else None
        if old != new:
            changed[name] = (_jsonable(old), _jsonable(new))
    return changed


@dataclass(frozen=True)
class AuditEntry:
    action: AuditAction
    resource: AuditedResource
    row: Any
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    redacted_fields: tuple[str, ...] = ()


def entry_for(action: AuditAction, row: Any) -> AuditEntry | None:
    """Audit entry for one flushed row, or None if nothing audit-relevant changed."""
    resource = AUDITED_RESOURCES.get(type(row))
    if resource is None:
        return None
    if action is AuditAction.CREATE:
        return AuditEntry(action, resource, row, new_values=_snapshot(row, resource.fields))
    if action is AuditAction.DELETE:
        return AuditEntry(action, resource, row, old_values=_snapshot(row, resource.fields))
    changed = _changed(row, resource.fields)
    redacted = tuple(_changed(row, resource.redacted))
    if not changed and not redacted:
        return None
    return AuditEntry(
        action,
        resource,
        row,
        old_values={name: old for name, (old, _) in changed.items()},
        new_values={name: new for name, (_, new) in changed.items()},
        redacted_fields=redacted,
    )


def collect_entries(session: Session) -> list[AuditEntry]:
    pending = (
        (AuditAction.CREATE, session.new),
        (AuditAction.UPDATE, session.dirty),
        (AuditAction.DELETE, session.deleted),
    )
    entries = (entry_for(action, row) for action, rows in pending for row in rows)
    return [entry for entry in entries if entry is not None]


def _audit_row(session: Session, entry: AuditEntry, now: datetime) -> dict[str, Any] | None:
    district_id, congregation_id = entry.resource.tenant(session, entry.row)
    if district_id is None and congregation_id is None:
        # Without a tenant the entry would be invisible and, for non-superadmins,
        # rejected by RLS, which would abort the business transaction.
        logger.warning(
            "Domain audit skipped, tenant unknown: resource_type=%s resource_id=%s",
            entry.resource.resource_type,
            entry.row.id,
        )
        return None
    changes = {"redacted_fields": list(entry.redacted_fields)} if entry.redacted_fields else None
    return {
        "id": uuid.uuid4(),
        "timestamp": now,
        "created_at": now,
        "user_sub": TenantContext.get_user_sub(),
        "user_roles": TenantContext.get_user_roles(),
        "action": entry.action,
        "resource_type": entry.resource.resource_type,
        "resource_id": entry.row.id,
        "district_id": district_id,
        "congregation_id": congregation_id,
        "changes": changes,
        "old_values": entry.old_values,
        "new_values": entry.new_values,
        "status": AuditStatus.SUCCESS,
        "extra_metadata": {"source": AUDIT_SOURCE},
    }


def record_domain_audit(session: Session, _flush_context: Any) -> None:
    """``after_flush`` hook: write audit rows on the flushing connection."""
    entries = collect_entries(session)
    if not entries:
        return
    now = datetime.now(UTC)
    rows = [row for entry in entries if (row := _audit_row(session, entry, now)) is not None]
    if rows:
        session.connection().execute(insert(AuditLogORM.__table__), rows)


def bulk_delete_audit_row(
    resource_type: str,
    *,
    deleted: int,
    reason: str,
    criteria: dict[str, Any],
) -> dict[str, Any]:
    """Values for one ``audit_logs`` row summarising a bulk DELETE statement.

    Bulk statements bypass the ORM unit of work and therefore ``after_flush``;
    callers insert this row in the same transaction instead.
    """
    now = datetime.now(UTC)
    return {
        "id": uuid.uuid4(),
        "timestamp": now,
        "created_at": now,
        "user_sub": TenantContext.get_user_sub(),
        "user_roles": TenantContext.get_user_roles(),
        "action": AuditAction.BULK_OPERATION,
        "resource_type": resource_type,
        "status": AuditStatus.SUCCESS,
        "changes": {"operation": "DELETE", "deleted": deleted, "reason": reason},
        "extra_metadata": {"source": AUDIT_SOURCE, "criteria": _jsonable_dict(criteria)},
    }


def _jsonable_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: _jsonable(value) for key, value in values.items()}
