"""Unit tests for run_sync() — UC-02 calendar sync.

Repositories, crypto, and the calendar connector are all mocked.
No database or network access is required.
"""

from __future__ import annotations

import uuid
from contextlib import ExitStack
from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.sync_service import run_sync
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.models.event import Event, EventSource, EventStatus, EventVisibility
from app.domain.models.raw_calendar_event import RawCalendarEvent

# ── factories ─────────────────────────────────────────────────────────────────

_NOW = datetime(2026, 3, 6, 12, tzinfo=UTC)
_DISTRICT_ID = uuid.uuid4()
_CONG_ID = uuid.uuid4()
_INT_ID = uuid.uuid4()


def _integration(**kw) -> CalendarIntegration:
    return CalendarIntegration(
        id=kw.get("id", _INT_ID),
        district_id=kw.get("district_id", _DISTRICT_ID),
        congregation_id=kw.get("congregation_id", _CONG_ID),
        name="Test Kalender",
        type=CalendarType.ICS,
        credentials_enc="encrypted",
        sync_interval=60,
        capabilities=[CalendarCapability.READ],
        is_active=True,
        last_synced_at=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _raw(
    uid: str = "uid@test",
    title: str = "Gottesdienst",
    content_hash: str = "hash-v1",
    is_cancelled: bool = False,
) -> RawCalendarEvent:
    return RawCalendarEvent(
        uid=uid,
        title=title,
        start_at=datetime(2026, 3, 10, 10, tzinfo=UTC),
        end_at=datetime(2026, 3, 10, 12, tzinfo=UTC),
        description="Beschreibung",
        content_hash=content_hash,
        is_cancelled=is_cancelled,
    )


def _existing_event(
    integration: CalendarIntegration,
    raw: RawCalendarEvent,
    status: EventStatus = EventStatus.DRAFT,
) -> Event:
    return Event(
        id=uuid.uuid4(),
        title=raw.title,
        start_at=raw.start_at,
        end_at=raw.end_at,
        district_id=integration.district_id,
        congregation_id=integration.congregation_id,
        source=EventSource.EXTERNAL,
        status=status,
        visibility=EventVisibility.INTERNAL,
        external_uid=raw.uid,
        calendar_integration_id=integration.id,
        content_hash=raw.content_hash,
        created_at=_NOW,
        updated_at=_NOW,
    )


# ── patch fixture ─────────────────────────────────────────────────────────────


class _SyncMocks:
    def __init__(self):
        self.session = MagicMock()
        self.integration_repo = MagicMock()
        self.integration_repo.get = AsyncMock()
        self.integration_repo.save = AsyncMock()
        self.event_repo = MagicMock()
        self.event_repo.get_by_external_uid = AsyncMock()
        self.event_repo.save = AsyncMock()
        self.connector = MagicMock()
        self.connector.fetch_events = AsyncMock()

    def _patchers(self):
        return [
            patch(
                "app.application.sync_service.SqlCalendarIntegrationRepository",
                return_value=self.integration_repo,
            ),
            patch(
                "app.application.sync_service.SqlEventRepository",
                return_value=self.event_repo,
            ),
            patch(
                "app.application.sync_service.decrypt_credentials",
                return_value={"url": "https://example.com/cal.ics"},
            ),
            patch(
                "app.application.sync_service._get_connector",
                return_value=self.connector,
            ),
        ]

    def __enter__(self):
        self._stack = ExitStack()
        for p in self._patchers():
            self._stack.enter_context(p)
        return self

    def __exit__(self, *args):
        self._stack.__exit__(*args)


@pytest.fixture
def m():
    with _SyncMocks() as mocks:
        yield mocks


# ── tests ─────────────────────────────────────────────────────────────────────


class TestRunSync:
    async def test_integration_not_found_raises(self, m):
        m.integration_repo.get.return_value = None
        with pytest.raises(ValueError, match=str(_INT_ID)):
            await run_sync(_INT_ID, m.session)

    async def test_new_event_is_created(self, m):
        integration = _integration()
        raw = _raw()
        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = [raw]
        m.event_repo.get_by_external_uid.return_value = None  # new

        result = await run_sync(_INT_ID, m.session)

        assert result == {"created": 1, "updated": 0, "cancelled": 0}
        m.event_repo.save.assert_called_once()
        saved_event: Event = m.event_repo.save.call_args[0][0]
        assert saved_event.external_uid == raw.uid
        assert saved_event.district_id == integration.district_id
        assert saved_event.congregation_id == integration.congregation_id
        assert saved_event.source == EventSource.EXTERNAL
        assert saved_event.status == EventStatus.DRAFT

    async def test_new_cancelled_event_is_skipped(self, m):
        m.integration_repo.get.return_value = _integration()
        m.connector.fetch_events.return_value = [_raw(is_cancelled=True)]
        m.event_repo.get_by_external_uid.return_value = None

        result = await run_sync(_INT_ID, m.session)

        assert result == {"created": 0, "updated": 0, "cancelled": 0}
        m.event_repo.save.assert_not_called()

    async def test_changed_event_is_updated(self, m):
        integration = _integration()
        raw_old = _raw(content_hash="hash-v1", title="Alter Titel")
        existing = _existing_event(integration, raw_old)
        raw_new = _raw(content_hash="hash-v2", title="Neuer Titel")  # hash changed

        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = [raw_new]
        m.event_repo.get_by_external_uid.return_value = existing

        result = await run_sync(_INT_ID, m.session)

        assert result == {"created": 0, "updated": 1, "cancelled": 0}
        assert existing.title == "Neuer Titel"
        assert existing.content_hash == "hash-v2"
        m.event_repo.save.assert_called_once_with(existing)

    async def test_unchanged_event_is_skipped(self, m):
        integration = _integration()
        raw = _raw(content_hash="hash-v1")
        existing = _existing_event(integration, raw)  # same hash

        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = [raw]
        m.event_repo.get_by_external_uid.return_value = existing

        result = await run_sync(_INT_ID, m.session)

        assert result == {"created": 0, "updated": 0, "cancelled": 0}
        m.event_repo.save.assert_not_called()

    async def test_existing_event_cancelled(self, m):
        integration = _integration()
        raw = _raw(is_cancelled=True)
        existing = _existing_event(integration, raw, status=EventStatus.DRAFT)

        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = [raw]
        m.event_repo.get_by_external_uid.return_value = existing

        result = await run_sync(_INT_ID, m.session)

        assert result == {"created": 0, "updated": 0, "cancelled": 1}
        assert existing.status == EventStatus.CANCELLED
        m.event_repo.save.assert_called_once_with(existing)

    async def test_already_cancelled_event_not_saved_again(self, m):
        integration = _integration()
        raw = _raw(is_cancelled=True)
        existing = _existing_event(integration, raw, status=EventStatus.CANCELLED)

        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = [raw]
        m.event_repo.get_by_external_uid.return_value = existing

        result = await run_sync(_INT_ID, m.session)

        assert result == {"created": 0, "updated": 0, "cancelled": 0}
        m.event_repo.save.assert_not_called()

    async def test_integration_last_synced_at_updated(self, m):
        integration = _integration()
        assert integration.last_synced_at is None

        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = []

        await run_sync(_INT_ID, m.session)

        assert integration.last_synced_at is not None
        m.integration_repo.save.assert_called_once_with(integration)

    async def test_mixed_events_counted_correctly(self, m):
        integration = _integration()
        raw_new = _raw(uid="new@test", content_hash="new-hash")
        raw_changed = _raw(uid="changed@test", content_hash="new-hash-2")
        raw_cancelled = _raw(uid="cancelled@test", is_cancelled=True)
        raw_unchanged = _raw(uid="same@test", content_hash="same-hash")

        existing_changed = _existing_event(
            integration, _raw(uid="changed@test", content_hash="old-hash-2")
        )
        existing_cancelled = _existing_event(
            integration, _raw(uid="cancelled@test"), status=EventStatus.DRAFT
        )
        existing_unchanged = _existing_event(
            integration, _raw(uid="same@test", content_hash="same-hash")
        )

        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = [raw_new, raw_changed, raw_cancelled, raw_unchanged]

        def _get_by_uid(uid, _int_id):
            return {
                "new@test": None,
                "changed@test": existing_changed,
                "cancelled@test": existing_cancelled,
                "same@test": existing_unchanged,
            }[uid]

        m.event_repo.get_by_external_uid.side_effect = _get_by_uid

        result = await run_sync(_INT_ID, m.session)

        assert result == {"created": 1, "updated": 1, "cancelled": 1}

    async def test_congregation_id_set_from_integration(self, m):
        """Events inherit congregation_id from the CalendarIntegration."""
        cong_id = uuid.uuid4()
        integration = _integration(congregation_id=cong_id)
        raw = _raw()

        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = [raw]
        m.event_repo.get_by_external_uid.return_value = None

        await run_sync(_INT_ID, m.session)

        saved: Event = m.event_repo.save.call_args[0][0]
        assert saved.congregation_id == cong_id

    async def test_district_level_integration_no_congregation(self, m):
        """Integration without congregation_id creates events at district level."""
        integration = _integration(congregation_id=None)
        raw = _raw()

        m.integration_repo.get.return_value = integration
        m.connector.fetch_events.return_value = [raw]
        m.event_repo.get_by_external_uid.return_value = None

        await run_sync(_INT_ID, m.session)

        saved: Event = m.event_repo.save.call_args[0][0]
        assert saved.congregation_id is None
