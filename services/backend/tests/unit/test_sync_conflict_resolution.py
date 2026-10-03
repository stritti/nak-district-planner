"""Regression tests for explicit sync conflict resolution."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.application.sync_service as sync_service
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.ports.calendar import CalendarConnectorError

_NOW = datetime(2026, 3, 6, 12, tzinfo=UTC)
_START = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
_END = datetime(2026, 4, 10, 10, 0, tzinfo=UTC)
_DISTRICT_ID = uuid.uuid4()
_CONG_ID = uuid.uuid4()
_INT_ID = uuid.uuid4()


def _integration(*, writable: bool = True) -> CalendarIntegration:
    capabilities = [CalendarCapability.READ]
    if writable:
        capabilities.append(CalendarCapability.WRITE)
    return CalendarIntegration(
        id=_INT_ID,
        district_id=_DISTRICT_ID,
        congregation_id=_CONG_ID,
        name="Test Kalender",
        type=CalendarType.GOOGLE,
        credentials_enc="encrypted",
        sync_interval=60,
        capabilities=capabilities,
        is_active=True,
        last_synced_at=None,
        created_at=_NOW,
        updated_at=_NOW,
        last_sync_error=None,
    )


def _instance(*, title: str = "Gottesdienst", shifted: bool = False) -> EventInstance:
    instance = EventInstance.create(
        planning_slot_id=uuid.uuid4(),
        title=title,
        actual_start_at=_START + (timedelta(hours=1) if shifted else timedelta()),
        actual_end_at=_END + (timedelta(hours=1) if shifted else timedelta()),
        source=EventSource.EXTERNAL,
        visibility=EventVisibility.PUBLIC,
    )
    instance.description = "Beschreibung"
    instance.sync_state = SyncState.DIRTY_INTERNAL
    return instance


def _baseline() -> dict[str, str | None]:
    return {
        "title": "Gottesdienst",
        "description": "Beschreibung",
        "actual_start_at": _START.isoformat(),
        "actual_end_at": _END.isoformat(),
    }


def _link(
    instance: EventInstance,
    *,
    baseline: dict[str, str | None] | None = None,
) -> ExternalEventLink:
    return ExternalEventLink.create(
        event_instance_id=instance.id,
        provider=CalendarType.GOOGLE.value,
        external_event_id="uid@test",
        calendar_integration_id=_INT_ID,
        last_synced_hash="old-hash",
        revision_marker="stale-revision",
        last_synced_payload=baseline,
        provider_resource_id="provider-resource",
    )


def _install_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    link: ExternalEventLink,
    integration: CalendarIntegration,
):
    link_repo = AsyncMock()
    integration_repo = AsyncMock()
    instance_repo = AsyncMock()
    connector = MagicMock()
    connector.update_event_times = AsyncMock(return_value="ack-revision")
    session = AsyncMock(spec=AsyncSession)

    link_repo.list_by_event_instance.return_value = [link]
    integration_repo.get.return_value = integration

    monkeypatch.setattr(sync_service, "SqlExternalEventLinkRepository", lambda _: link_repo)
    monkeypatch.setattr(sync_service, "SqlCalendarIntegrationRepository", lambda _: integration_repo)
    monkeypatch.setattr(sync_service, "SqlEventInstanceRepository", lambda _: instance_repo)
    monkeypatch.setattr(sync_service, "_get_connector", lambda _: connector)
    monkeypatch.setattr(sync_service, "decrypt_credentials", lambda _: {"token": "test"})

    return link_repo, instance_repo, connector, session


async def test_time_conflict_pushes_without_stale_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = _instance(shifted=True)
    link = _link(instance, baseline=_baseline())
    link_repo, instance_repo, connector, session = _install_runtime(
        monkeypatch, link=link, integration=_integration()
    )

    assert await sync_service.push_conflict_resolution(instance, session) is True

    raw = connector.update_event_times.await_args.args[1]
    assert raw.revision_marker is None
    assert raw.resource_id == "provider-resource"
    assert link.revision_marker == "ack-revision"
    assert link.last_synced_payload == {
        "title": "Gottesdienst",
        "description": "Beschreibung",
        "actual_start_at": (_START + timedelta(hours=1)).isoformat(),
        "actual_end_at": (_END + timedelta(hours=1)).isoformat(),
    }
    assert instance.sync_state == SyncState.CLEAN
    link_repo.save.assert_awaited_once_with(link)
    instance_repo.save.assert_awaited_once_with(instance)


async def test_text_conflict_is_not_falsely_acknowledged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = _instance(title="Interner Titel")
    link = _link(instance, baseline=_baseline())
    link_repo, instance_repo, connector, session = _install_runtime(
        monkeypatch, link=link, integration=_integration()
    )

    with pytest.raises(CalendarConnectorError, match="title"):
        await sync_service.push_conflict_resolution(instance, session)

    connector.update_event_times.assert_not_awaited()
    link_repo.save.assert_not_awaited()
    instance_repo.save.assert_not_awaited()
    assert link.last_synced_hash == "old-hash"
    assert link.revision_marker == "stale-revision"
    assert instance.sync_state == SyncState.DIRTY_INTERNAL


async def test_missing_baseline_is_not_acknowledged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = _instance()
    link = _link(instance)
    link_repo, instance_repo, connector, session = _install_runtime(
        monkeypatch, link=link, integration=_integration()
    )

    with pytest.raises(CalendarConnectorError):
        await sync_service.push_conflict_resolution(instance, session)

    connector.update_event_times.assert_not_awaited()
    link_repo.save.assert_not_awaited()
    instance_repo.save.assert_not_awaited()


async def test_no_writable_link_leaves_instance_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = _instance()
    link = _link(instance, baseline=_baseline())
    _, instance_repo, connector, session = _install_runtime(
        monkeypatch, link=link, integration=_integration(writable=False)
    )

    assert await sync_service.push_conflict_resolution(instance, session) is False
    assert instance.sync_state == SyncState.DIRTY_INTERNAL
    connector.update_event_times.assert_not_awaited()
    instance_repo.save.assert_not_awaited()


async def test_provider_failure_does_not_advance_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = _instance(shifted=True)
    baseline = _baseline()
    link = _link(instance, baseline=baseline)
    link_repo, instance_repo, connector, session = _install_runtime(
        monkeypatch, link=link, integration=_integration()
    )
    connector.update_event_times.side_effect = CalendarConnectorError("provider down")

    with pytest.raises(CalendarConnectorError, match="provider down"):
        await sync_service.push_conflict_resolution(instance, session)

    assert link.last_synced_payload == baseline
    assert link.last_synced_hash == "old-hash"
    assert link.revision_marker == "stale-revision"
    link_repo.save.assert_not_awaited()
    instance_repo.save.assert_not_awaited()
