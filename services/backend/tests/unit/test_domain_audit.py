# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Domain audit hook: which changes are recorded and what an entry contains."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm.attributes import set_committed_value

from app.adapters.db import domain_audit
from app.adapters.db.domain_audit import (
    AUDIT_SOURCE,
    bulk_delete_audit_row,
    collect_entries,
    entry_for,
    record_domain_audit,
)
from app.adapters.db.orm_models.audit_log import AuditAction, AuditStatus
from app.adapters.db.orm_models.calendar_integration import CalendarIntegrationORM
from app.adapters.db.orm_models.export_token import ExportTokenORM
from app.adapters.db.orm_models.notification import NotificationORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.domain.models.planning_slot import EventApprovalStatus
from app.domain.models.service_assignment import AssignmentStatus
from app.tenant import TenantContext

DISTRICT = uuid.uuid4()
CONGREGATION = uuid.uuid4()


def _slot(**overrides) -> PlanningSlotORM:
    values = {
        "id": uuid.uuid4(),
        "district_id": DISTRICT,
        "congregation_id": CONGREGATION,
        "title": "Gottesdienst",
        "category": "Gottesdienst",
        "planning_date": date(2026, 10, 4),
        "planning_time": time(9, 30),
        "approval_status": EventApprovalStatus.PLANNED,
        "applicability": [],
    }
    values.update(overrides)
    return PlanningSlotORM(**values)


def _loaded(row, **committed):
    """Simulate a row loaded from the database; ``committed`` overrides column values."""
    for column in inspect(row).mapper.column_attrs:
        set_committed_value(row, column.key, committed.get(column.key, getattr(row, column.key)))
    return row


def _assignment(slot_id: uuid.UUID | None, **overrides) -> ServiceAssignmentORM:
    values = {
        "id": uuid.uuid4(),
        "planning_slot_id": slot_id,
        "leader_name": "Anna Beispiel",
        "status": AssignmentStatus.ASSIGNED,
    }
    values.update(overrides)
    return ServiceAssignmentORM(**values)


def _session(new=(), dirty=(), deleted=(), identity=None, db_tenant=None) -> MagicMock:
    session = MagicMock()
    session.new, session.dirty, session.deleted = list(new), list(dirty), list(deleted)
    identity = identity or {}
    session.identity_map.get.side_effect = lambda key: identity.get(key[1][0])
    session.connection.return_value.execute.return_value.first.return_value = db_tenant
    return session


@pytest.fixture(autouse=True)
def _actor():
    TenantContext.set_context(user_sub="user-1", user_roles=["PLANNER"])
    yield
    TenantContext.clear_context()


class TestEntryFor:
    def test_create_snapshots_whitelisted_fields_as_json(self) -> None:
        slot = _slot()
        entry = entry_for(AuditAction.CREATE, slot)

        assert entry.old_values is None
        assert entry.new_values == {
            "title": "Gottesdienst",
            "category": "Gottesdienst",
            "planning_date": "2026-10-04",
            "planning_time": "09:30:00",
            "status": None,
            "approval_status": "PLANNED",
            "applicability": [],
            "congregation_id": str(CONGREGATION),
        }

    def test_delete_keeps_the_last_state(self) -> None:
        entry = entry_for(AuditAction.DELETE, _assignment(uuid.uuid4()))
        assert entry.new_values is None
        assert entry.old_values["leader_name"] == "Anna Beispiel"
        assert entry.old_values["status"] == "ASSIGNED"

    def test_update_records_only_changed_fields(self) -> None:
        slot = _loaded(_slot(), title="Alt", category="Gottesdienst")
        slot.title = "Neu"
        slot.category = "Gottesdienst"  # assigned but unchanged

        entry = entry_for(AuditAction.UPDATE, slot)

        assert entry.old_values == {"title": "Alt"}
        assert entry.new_values == {"title": "Neu"}

    def test_update_of_unaudited_fields_only_is_ignored(self) -> None:
        integration = _loaded(CalendarIntegrationORM(id=uuid.uuid4()), last_sync_error=None)
        integration.last_sync_error = "timeout"
        integration.last_synced_at = datetime.now(UTC)
        assert entry_for(AuditAction.UPDATE, integration) is None

    def test_changed_credentials_are_reported_by_name_only(self) -> None:
        integration = _loaded(
            CalendarIntegrationORM(id=uuid.uuid4()), credentials_enc="old-cipher", name="ICS"
        )
        integration.credentials_enc = "new-cipher"

        entry = entry_for(AuditAction.UPDATE, integration)

        assert entry.redacted_fields == ("credentials_enc",)
        assert entry.old_values == {} and entry.new_values == {}
        assert "cipher" not in repr((entry.old_values, entry.new_values))

    def test_export_token_value_is_never_snapshotted(self) -> None:
        token = ExportTokenORM(
            id=uuid.uuid4(), token="secret-token", label="Gemeinde", district_id=DISTRICT
        )
        entry = entry_for(AuditAction.CREATE, token)
        assert "token" not in entry.new_values
        assert "secret-token" not in repr(entry.new_values)

    def test_unaudited_resources_are_ignored(self) -> None:
        assert entry_for(AuditAction.CREATE, NotificationORM()) is None


class TestRecordDomainAudit:
    def _inserted_rows(self, session: MagicMock) -> list[dict]:
        statement, rows = session.connection.return_value.execute.call_args.args
        assert statement.table.name == "audit_logs"
        return rows

    def test_writes_one_row_per_change_with_actor_and_tenant(self) -> None:
        slot = _slot()
        session = _session(new=[slot])

        record_domain_audit(session, None)

        [row] = self._inserted_rows(session)
        assert row["action"] is AuditAction.CREATE
        assert row["resource_type"] == "planning_slot"
        assert row["resource_id"] == slot.id
        assert (row["district_id"], row["congregation_id"]) == (DISTRICT, CONGREGATION)
        assert (row["user_sub"], row["user_roles"]) == ("user-1", ["PLANNER"])
        assert row["status"] is AuditStatus.SUCCESS
        assert row["extra_metadata"] == {"source": AUDIT_SOURCE}
        assert row["timestamp"] == row["created_at"]
        assert row["changes"] is None

    def test_redacted_fields_are_listed_under_changes(self) -> None:
        integration = _loaded(
            CalendarIntegrationORM(id=uuid.uuid4(), district_id=DISTRICT), credentials_enc="a"
        )
        integration.credentials_enc = "b"
        session = _session(dirty=[integration])

        record_domain_audit(session, None)

        [row] = self._inserted_rows(session)
        assert row["changes"] == {"redacted_fields": ["credentials_enc"]}

    def test_assignment_uses_tenant_of_slot_in_the_same_flush(self) -> None:
        slot = _slot()
        session = _session(deleted=[_assignment(slot.id)], identity={slot.id: slot})

        record_domain_audit(session, None)

        [row] = self._inserted_rows(session)
        assert row["action"] is AuditAction.DELETE
        assert (row["district_id"], row["congregation_id"]) == (DISTRICT, CONGREGATION)

    def test_assignment_tenant_falls_back_to_the_database(self) -> None:
        tenant = SimpleNamespace(district_id=DISTRICT, congregation_id=None)
        session = _session(new=[_assignment(uuid.uuid4())], db_tenant=tenant)

        record_domain_audit(session, None)

        insert_call = session.connection.return_value.execute.call_args_list[-1]
        [row] = insert_call.args[1]
        assert (row["district_id"], row["congregation_id"]) == (DISTRICT, None)

    def test_legacy_event_id_links_the_assignment_to_its_slot(self) -> None:
        slot = _slot()
        assignment = _assignment(None, event_id=slot.id)
        session = _session(new=[assignment], identity={slot.id: slot})

        record_domain_audit(session, None)

        [row] = self._inserted_rows(session)
        assert row["district_id"] == DISTRICT

    @pytest.mark.parametrize("slot_id", [None, uuid.uuid4()], ids=["unlinked", "slot-gone"])
    def test_entry_without_tenant_is_skipped_and_logged(self, slot_id, caplog) -> None:
        assignment = _assignment(slot_id)
        session = _session(deleted=[assignment], db_tenant=None)

        record_domain_audit(session, None)

        inserts = [
            call
            for call in session.connection.return_value.execute.call_args_list
            if len(call.args) == 2
        ]
        assert inserts == []
        assert f"resource_id={assignment.id}" in caplog.text
        assert "Anna" not in caplog.text

    def test_nothing_is_written_without_audited_changes(self) -> None:
        session = _session(new=[NotificationORM()])
        record_domain_audit(session, None)
        session.connection.assert_not_called()

    def test_collect_entries_covers_new_dirty_and_deleted(self) -> None:
        updated = _loaded(_slot(), title="Alt")
        updated.title = "Neu"
        session = _session(new=[_slot()], dirty=[updated], deleted=[_slot()])

        actions = [entry.action for entry in collect_entries(session)]

        assert actions == [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE]


def test_bulk_delete_row_summarises_the_statement() -> None:
    row = bulk_delete_audit_row(
        "planning_slot",
        deleted=7,
        reason="retention",
        criteria={"planning_date_before": date(2024, 9, 30)},
    )
    assert row["action"] is AuditAction.BULK_OPERATION
    assert row["changes"] == {"operation": "DELETE", "deleted": 7, "reason": "retention"}
    assert row["extra_metadata"] == {
        "source": AUDIT_SOURCE,
        "criteria": {"planning_date_before": "2024-09-30"},
    }
    assert row["user_sub"] == "user-1"


def test_audited_session_class_is_used_by_the_session_factory() -> None:
    from sqlalchemy import event

    from app.adapters.db.session import AsyncSessionLocal, AuditedSession

    assert AsyncSessionLocal.kw["sync_session_class"] is AuditedSession
    assert event.contains(AuditedSession, "after_flush", domain_audit.record_domain_audit)
