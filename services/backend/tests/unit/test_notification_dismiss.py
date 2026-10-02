"""Regression tests for idempotent, district-authorized notification dismissal."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers.notifications import dismiss_notification
from app.adapters.db.repositories.notification import SqlNotificationRepository
from app.application.notification_service import NotificationService
from app.domain.models.notification import Notification, NotificationType


def notification() -> Notification:
    return Notification.create(
        district_id=uuid.uuid4(),
        type=NotificationType.SYSTEM,
        title="Information",
        body="Details",
    )


def test_domain_dismissal_is_idempotent() -> None:
    item = notification()
    assert not item.is_dismissed
    assert item.dismissed_at is None

    item.dismiss()
    dismissed_at = item.dismissed_at
    assert item.is_dismissed
    assert dismissed_at is not None

    item.dismiss()
    assert item.dismissed_at == dismissed_at
    assert item.read_at is None


@pytest.mark.asyncio
async def test_service_dismisses_existing_notification() -> None:
    item = notification()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=item)
    repo.mark_dismissed = AsyncMock()

    assert await NotificationService(repo).dismiss(item.id)
    repo.mark_dismissed.assert_awaited_once_with(item.id)


@pytest.mark.asyncio
async def test_service_repeated_dismiss_preserves_timestamp() -> None:
    item = notification()
    item.dismiss()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=item)
    repo.mark_dismissed = AsyncMock()

    assert await NotificationService(repo).dismiss(item.id)
    repo.mark_dismissed.assert_not_awaited()


@pytest.mark.asyncio
async def test_service_unknown_notification_does_not_mutate() -> None:
    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)
    repo.mark_dismissed = AsyncMock()

    assert not await NotificationService(repo).dismiss(uuid.uuid4())
    repo.mark_dismissed.assert_not_awaited()


@pytest.mark.asyncio
async def test_repository_uses_idempotent_dismissal_condition() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    repo = SqlNotificationRepository(session)

    await repo.mark_dismissed(uuid.uuid4())
    statement = session.execute.await_args.args[0]
    compiled = str(statement)
    assert "dismissed_at IS NULL" in compiled
    assert "dismissed_at" in str(statement.compile().params)


@pytest.mark.asyncio
async def test_repository_lists_only_visible_notifications_even_without_unread_filter() -> None:
    session = MagicMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(side_effect=[count_result, list_result])
    repo = SqlNotificationRepository(session)

    assert await repo.list_by_district(uuid.uuid4(), unread_only=False) == ([], 0)
    count_sql = str(session.execute.await_args_list[0].args[0])
    list_sql = str(session.execute.await_args_list[1].args[0])
    assert "dismissed_at IS NULL" in count_sql
    assert "dismissed_at IS NULL" in list_sql


@pytest.mark.asyncio
async def test_repository_read_all_ignores_dismissed() -> None:
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(rowcount=2))
    repo = SqlNotificationRepository(session)

    assert await repo.mark_all_read(uuid.uuid4(), "subject") == 2
    assert "dismissed_at IS NULL" in str(session.execute.await_args.args[0])


@pytest.mark.asyncio
async def test_dismiss_endpoint_returns_404_for_missing_notification() -> None:
    service = MagicMock()
    service.get = AsyncMock(return_value=None)
    service.dismiss = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await dismiss_notification(uuid.uuid4(), MagicMock(), service)
    assert exc.value.status_code == 404
    service.dismiss.assert_not_awaited()


@pytest.mark.asyncio
async def test_dismiss_endpoint_rejects_cross_district_access() -> None:
    item = notification()
    service = MagicMock()
    service.get = AsyncMock(return_value=item)
    service.dismiss = AsyncMock()

    with patch(
        "app.adapters.api.routers.notifications.require_role_in_district",
        side_effect=HTTPException(status_code=403, detail="Forbidden"),
    ):
        with pytest.raises(HTTPException) as exc:
            await dismiss_notification(item.id, MagicMock(), service)
    assert exc.value.status_code == 403
    service.dismiss.assert_not_awaited()


@pytest.mark.asyncio
async def test_dismiss_endpoint_authorizes_before_mutation() -> None:
    item = notification()
    service = MagicMock()
    service.get = AsyncMock(return_value=item)
    service.dismiss = AsyncMock(return_value=True)

    with patch("app.adapters.api.routers.notifications.require_role_in_district") as authorize:
        await dismiss_notification(item.id, MagicMock(), service)
    authorize.assert_called_once()
    assert authorize.call_args.args[2] == item.district_id
    service.dismiss.assert_awaited_once_with(item.id)
