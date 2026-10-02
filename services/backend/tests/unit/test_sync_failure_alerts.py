"""SyncFailureAlerter: alert content, de-duplication and missing integrations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.sync_failure_alerts import (
    DEDUPLICATION_WINDOW,
    SYNC_FAILURE_ALERT_KIND,
    SyncFailure,
    SyncFailureAlerter,
)
from app.domain.events import EventType
from app.domain.models.calendar_integration import CalendarIntegration, CalendarType
from app.domain.models.event_mail_hook import EVENT_PLACEHOLDERS
from app.domain.models.notification import Notification, NotificationType


class FakeIntegrations:
    def __init__(self, *integrations: CalendarIntegration) -> None:
        self._by_id = {integration.id: integration for integration in integrations}

    async def get(self, integration_id: uuid.UUID) -> CalendarIntegration | None:
        return self._by_id.get(integration_id)


class FakeNotifications:
    def __init__(self) -> None:
        self.saved: list[Notification] = []
        self.list_calls: list[dict] = []

    async def save(self, notification: Notification) -> None:
        self.saved.append(notification)

    async def list_by_district(
        self, district_id: uuid.UUID, *, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> tuple[list[Notification], int]:
        self.list_calls.append({"unread_only": unread_only, "limit": limit})
        items = [
            n
            for n in self.saved
            if n.district_id == district_id and (not unread_only or not n.is_read)
        ]
        return items[:limit], len(items)


@pytest.fixture
def integration() -> CalendarIntegration:
    return CalendarIntegration.create(
        district_id=uuid.uuid4(),
        congregation_id=uuid.uuid4(),
        name="Gemeindekalender",
        type=CalendarType.ICS,
        credentials_enc="encrypted",
    )


def _failure(integration_id: uuid.UUID) -> SyncFailure:
    return SyncFailure(integration_id=integration_id, error_class="ConnectError", attempts=5)


async def test_alert_creates_system_notification_for_integration_scope(integration) -> None:
    notifications = FakeNotifications()
    alerter = SyncFailureAlerter(FakeIntegrations(integration), notifications)

    alert = await alerter.alert(_failure(integration.id))

    assert alert is not None
    assert notifications.saved == [alert]
    assert alert.type == NotificationType.SYSTEM
    assert alert.district_id == integration.district_id
    assert alert.congregation_id == integration.congregation_id
    assert "Gemeindekalender" in alert.title
    assert "5 Versuchen" in alert.body
    assert alert.payload == {
        "kind": SYNC_FAILURE_ALERT_KIND,
        "integration_id": str(integration.id),
        "error_class": "ConnectError",
        "attempts": 5,
    }


async def test_unread_alert_for_same_integration_suppresses_duplicate(integration) -> None:
    notifications = FakeNotifications()
    alerter = SyncFailureAlerter(FakeIntegrations(integration), notifications)

    first = await alerter.alert(_failure(integration.id))
    second = await alerter.alert(_failure(integration.id))

    assert first is not None
    assert second is None
    assert len(notifications.saved) == 1
    assert notifications.list_calls[-1] == {"unread_only": True, "limit": DEDUPLICATION_WINDOW}


async def test_read_alert_does_not_suppress_new_alert(integration) -> None:
    notifications = FakeNotifications()
    alerter = SyncFailureAlerter(FakeIntegrations(integration), notifications)
    first = await alerter.alert(_failure(integration.id))
    assert first is not None
    first.mark_read()

    second = await alerter.alert(_failure(integration.id))

    assert second is not None
    assert len(notifications.saved) == 2


async def test_alert_for_other_integration_does_not_suppress(integration) -> None:
    sibling = CalendarIntegration.create(
        district_id=integration.district_id,
        name="Bezirkskalender",
        type=CalendarType.CALDAV,
        credentials_enc="encrypted",
    )
    notifications = FakeNotifications()
    alerter = SyncFailureAlerter(FakeIntegrations(integration, sibling), notifications)

    assert await alerter.alert(_failure(sibling.id)) is not None
    assert await alerter.alert(_failure(integration.id)) is not None
    assert len(notifications.saved) == 2


async def test_unrelated_system_notification_does_not_suppress(integration) -> None:
    notifications = FakeNotifications()
    notifications.saved.append(
        Notification.create(
            district_id=integration.district_id,
            type=NotificationType.SYSTEM,
            title="Wartung",
            body="",
            payload={"integration_id": str(integration.id)},
        )
    )
    alerter = SyncFailureAlerter(FakeIntegrations(integration), notifications)

    assert await alerter.alert(_failure(integration.id)) is not None


async def test_missing_integration_is_skipped_without_alert(caplog) -> None:
    notifications = FakeNotifications()
    alerter = SyncFailureAlerter(FakeIntegrations(), notifications)
    missing_id = uuid.uuid4()

    with caplog.at_level("WARNING"):
        assert await alerter.alert(_failure(missing_id)) is None

    assert notifications.saved == []
    assert str(missing_id) in caplog.text


async def test_alert_publishes_sync_error_event_with_template_placeholders(integration) -> None:
    published = []
    alerter = SyncFailureAlerter(
        FakeIntegrations(integration),
        FakeNotifications(),
        publish=published.append,
        clock=lambda: datetime(2030, 3, 1, 6, 15, 42, tzinfo=UTC),
    )

    await alerter.alert(_failure(integration.id))

    [event] = published
    assert event.event_type == EventType.SYNC_ERROR
    assert event.district_id == integration.district_id
    assert event.payload == {
        "integration_name": "Gemeindekalender",
        "error_message": "Die Synchronisation ist nach 5 Versuchen fehlgeschlagen (ConnectError)",
        "timestamp": "2030-03-01T06:15+00:00",
    }
    # district_name is added by the dispatcher.
    assert set(event.payload) | {"district_name"} == EVENT_PLACEHOLDERS[EventType.SYNC_ERROR]


async def test_deduplicated_alert_publishes_no_second_event(integration) -> None:
    published = []
    alerter = SyncFailureAlerter(
        FakeIntegrations(integration), FakeNotifications(), publish=published.append
    )

    await alerter.alert(_failure(integration.id))
    assert await alerter.alert(_failure(integration.id)) is None

    assert len(published) == 1


async def test_missing_integration_publishes_no_event() -> None:
    published = []
    alerter = SyncFailureAlerter(FakeIntegrations(), FakeNotifications(), publish=published.append)

    await alerter.alert(_failure(uuid.uuid4()))

    assert published == []
