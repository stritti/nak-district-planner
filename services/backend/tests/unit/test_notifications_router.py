"""Unit tests for notifications API router endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import notifications as r
from app.domain.models.user import User


def _fake_user() -> User:
    return User(sub="test-user", email="test@example.com", username="test-user", name="Test")


class TestNotificationsRouter:
    """Tests for notification API endpoints."""

    async def test_list_notifications(self):
        service = AsyncMock()
        service.list = AsyncMock(return_value={"items": [], "total": 0, "limit": 50, "offset": 0})
        district_id = uuid.uuid4()

        result = await r.list_notifications(
            district_id=district_id,
            unread_only=False,
            limit=50,
            offset=0,
            _user=_fake_user(),
            service=service,
        )
        assert result["total"] == 0
        assert result["items"] == []
        service.list.assert_awaited_once_with(district_id, unread_only=False, limit=50, offset=0)

    async def test_list_notifications_unread_only(self):
        service = AsyncMock()
        service.list = AsyncMock()
        district_id = uuid.uuid4()

        await r.list_notifications(
            district_id=district_id,
            unread_only=True,
            limit=10,
            offset=5,
            _user=_fake_user(),
            service=service,
        )
        service.list.assert_awaited_once_with(district_id, unread_only=True, limit=10, offset=5)

    async def test_unread_count(self):
        service = AsyncMock()
        service.get_unread_count = AsyncMock(return_value=7)
        district_id = uuid.uuid4()

        result = await r.unread_count(
            district_id=district_id,
            _user=_fake_user(),
            service=service,
        )
        assert result == {"count": 7}
        service.get_unread_count.assert_awaited_once_with(district_id)

    async def test_unread_count_zero(self):
        service = AsyncMock()
        service.get_unread_count = AsyncMock(return_value=0)
        district_id = uuid.uuid4()

        result = await r.unread_count(
            district_id=district_id,
            _user=_fake_user(),
            service=service,
        )
        assert result == {"count": 0}

    async def test_mark_read_success(self):
        notification_id = uuid.uuid4()
        service = AsyncMock()
        service.mark_read = AsyncMock(return_value=True)

        result = await r.mark_read(
            notification_id=notification_id,
            _user=_fake_user(),
            service=service,
        )
        assert result is None  # 204 No Content
        service.mark_read.assert_awaited_once_with(notification_id)

    async def test_mark_read_not_found(self):
        notification_id = uuid.uuid4()
        service = AsyncMock()
        service.mark_read = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc:
            await r.mark_read(
                notification_id=notification_id,
                _user=_fake_user(),
                service=service,
            )
        assert exc.value.status_code == 404

    async def test_mark_all_read(self):
        district_id = uuid.uuid4()
        service = AsyncMock()
        service.mark_all_read = AsyncMock(return_value=3)

        result = await r.mark_all_read(
            district_id=district_id,
            _user=_fake_user(),
            service=service,
        )
        assert result == {"marked_read": 3}
        service.mark_all_read.assert_awaited_once_with(district_id, "test-user")

    async def test_mark_all_read_zero(self):
        district_id = uuid.uuid4()
        service = AsyncMock()
        service.mark_all_read = AsyncMock(return_value=0)

        result = await r.mark_all_read(
            district_id=district_id,
            _user=_fake_user(),
            service=service,
        )
        assert result == {"marked_read": 0}
