"""Unit tests for notification system — domain model, service, repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.notification_service import NotificationService
from app.domain.models.notification import Notification, NotificationType
from app.domain.ports.repositories import NotificationRepository

# ── Domain model tests ─────────────────────────────────────────────────────────


class TestNotificationDomain:
    def test_create_notification(self):
        district_id = uuid.uuid4()
        notification = Notification.create(
            district_id=district_id,
            type=NotificationType.SYSTEM,
            title="Test-Benachrichtigung",
            body="Test-Body",
        )
        assert notification.district_id == district_id
        assert notification.type == NotificationType.SYSTEM
        assert notification.title == "Test-Benachrichtigung"
        assert notification.body == "Test-Body"
        assert notification.congregation_id is None
        assert notification.payload == {}
        assert notification.read_at is None
        assert notification.created_at is not None
        assert not notification.is_read

    def test_create_notification_with_payload(self):
        notification = Notification.create(
            district_id=uuid.uuid4(),
            type=NotificationType.EXTERNAL_EVENT_DETECTED,
            title="Neues Ereignis",
            body="Ein externes Ereignis wurde erkannt",
            congregation_id=uuid.uuid4(),
            payload={"event_uid": "abc123", "source": "ical"},
        )
        assert notification.congregation_id is not None
        assert notification.payload == {"event_uid": "abc123", "source": "ical"}

    def test_mark_read(self):
        notification = Notification.create(
            district_id=uuid.uuid4(),
            type=NotificationType.ASSIGNMENT_REMINDER,
            title="Erinnerung",
            body="Bitte Dienst besetzen",
        )
        assert not notification.is_read
        assert notification.read_at is None

        notification.mark_read()
        assert notification.is_read
        assert notification.read_at is not None

    def test_notification_type_values(self):
        assert NotificationType.EXTERNAL_EVENT_DETECTED.value == "EXTERNAL_EVENT_DETECTED"
        assert NotificationType.SYNC_CONFLICT.value == "SYNC_CONFLICT"
        assert NotificationType.CANDIDATE_REVIEW.value == "CANDIDATE_REVIEW"
        assert NotificationType.ASSIGNMENT_REMINDER.value == "ASSIGNMENT_REMINDER"
        assert NotificationType.SYSTEM.value == "SYSTEM"


# ── Service tests ──────────────────────────────────────────────────────────────


class TestNotificationService:
    @pytest.fixture
    def repo(self) -> NotificationRepository:
        return MagicMock(spec=NotificationRepository)

    @pytest.fixture
    def service(self, repo: NotificationRepository) -> NotificationService:
        return NotificationService(notification_repo=repo)

    async def test_create(self, service: NotificationService, repo: MagicMock):
        district_id = uuid.uuid4()
        repo.save = AsyncMock()

        notification = await service.create_notification(
            district_id=district_id,
            type=NotificationType.SYSTEM,
            title="Test",
            body="Body",
        )
        assert notification.title == "Test"
        assert notification.district_id == district_id
        repo.save.assert_awaited_once()

    async def test_create_with_all_params(self, service: NotificationService, repo: MagicMock):
        district_id = uuid.uuid4()
        congregation_id = uuid.uuid4()
        repo.save = AsyncMock()

        notification = await service.create_notification(
            district_id=district_id,
            type=NotificationType.CANDIDATE_REVIEW,
            title="Kandidat",
            body="Prüfung erforderlich",
            congregation_id=congregation_id,
            payload={"leader_id": "abc"},
        )
        assert notification.congregation_id == congregation_id
        assert notification.payload == {"leader_id": "abc"}
        repo.save.assert_awaited_once()

    async def test_list(self, service: NotificationService, repo: MagicMock):
        district_id = uuid.uuid4()
        repo.list_by_district = AsyncMock(return_value=([], 0))

        result = await service.list(district_id)
        assert result == {"items": [], "total": 0, "limit": 50, "offset": 0}
        repo.list_by_district.assert_awaited_once_with(
            district_id, unread_only=False, limit=50, offset=0
        )

    async def test_list_unread_only(self, service: NotificationService, repo: MagicMock):
        district_id = uuid.uuid4()
        repo.list_by_district = AsyncMock(return_value=([], 0))

        await service.list(district_id, unread_only=True, limit=10, offset=5)
        repo.list_by_district.assert_awaited_once_with(
            district_id, unread_only=True, limit=10, offset=5
        )

    async def test_mark_read_existing(self, service: NotificationService, repo: MagicMock):
        notification_id = uuid.uuid4()
        repo.get = AsyncMock(
            return_value=Notification(
                id=notification_id,
                district_id=uuid.uuid4(),
                type=NotificationType.SYSTEM,
                title="Test",
                body="",
                created_at=datetime.now(timezone.utc),
            )
        )
        repo.mark_read = AsyncMock()

        result = await service.mark_read(notification_id)
        assert result is True
        repo.mark_read.assert_awaited_once_with(notification_id)

    async def test_mark_read_not_found(self, service: NotificationService, repo: MagicMock):
        repo.get = AsyncMock(return_value=None)

        result = await service.mark_read(uuid.uuid4())
        assert result is False
        repo.mark_read.assert_not_called()

    async def test_mark_all_read(self, service: NotificationService, repo: MagicMock):
        district_id = uuid.uuid4()
        repo.mark_all_read = AsyncMock(return_value=5)

        count = await service.mark_all_read(district_id, "user_sub_abc")
        assert count == 5
        repo.mark_all_read.assert_awaited_once_with(district_id, "user_sub_abc")

    async def test_get_unread_count(self, service: NotificationService, repo: MagicMock):
        district_id = uuid.uuid4()
        repo.list_by_district = AsyncMock(
            return_value=(
                [MagicMock(), MagicMock()],  # 2 items
                2,  # total
            )
        )

        count = await service.get_unread_count(district_id)
        assert count == 2
        repo.list_by_district.assert_awaited_once_with(district_id, unread_only=True, limit=1)


# ── Repository tests (mocked session) ──────────────────────────────────────────


class TestSqlNotificationRepository:
    @pytest.fixture
    def session(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, session):
        from app.adapters.db.repositories.notification import SqlNotificationRepository

        return SqlNotificationRepository(session)

    async def test_get_found(self, repo, session):
        notification_id = uuid.uuid4()
        session.get = AsyncMock(
            return_value=MagicMock(
                id=notification_id,
                district_id=uuid.uuid4(),
                congregation_id=None,
                type="SYSTEM",
                title="Test",
                body="Body",
                payload={},
                read_at=None,
                created_at=datetime.now(UTC),
            )
        )
        result = await repo.get(notification_id)
        assert result is not None
        assert result.title == "Test"

    async def test_get_not_found(self, repo, session):
        session.get = AsyncMock(return_value=None)
        result = await repo.get(uuid.uuid4())
        assert result is None

    async def test_save(self, repo, session):
        notification = Notification.create(
            district_id=uuid.uuid4(),
            type=NotificationType.SYSTEM,
            title="Test",
            body="Body",
        )
        session.add = MagicMock()
        session.flush = AsyncMock()

        await repo.save(notification)
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_mark_read(self, repo, session):
        notification_id = uuid.uuid4()
        session.execute = AsyncMock()

        await repo.mark_read(notification_id)
        session.execute.assert_awaited_once()

    async def test_mark_all_read(self, repo, session):
        district_id = uuid.uuid4()
        result_mock = MagicMock()
        result_mock.rowcount = 3
        session.execute = AsyncMock(return_value=result_mock)

        count = await repo.mark_all_read(district_id, "user_sub")
        assert count == 3
        session.execute.assert_awaited_once()

    @pytest.mark.parametrize("unread_only", [True, False])
    async def test_list_by_district(self, repo, session, unread_only):
        district_id = uuid.uuid4()

        # Mock count result
        count_result = MagicMock()
        count_result.scalar.return_value = 5
        # Mock list result
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []

        session.execute = AsyncMock()
        session.execute.side_effect = [count_result, list_result]

        items, total = await repo.list_by_district(
            district_id, unread_only=unread_only, limit=10, offset=0
        )
        assert total == 5
        assert items == []


import unittest.mock  # noqa: E402 (needed for the sentinel above)
