"""Application service for the notification system."""

from __future__ import annotations

import uuid

from app.domain.models.notification import Notification, NotificationType
from app.domain.ports.repositories import NotificationRepository


class NotificationService:
    """Creates and manages in-app notifications."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        self._repo = notification_repo

    async def get(self, notification_id: uuid.UUID) -> Notification | None:
        """Retrieve a single notification by ID."""
        return await self._repo.get(notification_id)

    async def create_notification(
        self,
        *,
        district_id: uuid.UUID,
        type: NotificationType,
        title: str,
        body: str = "",
        congregation_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> Notification:
        """Create and persist a new notification."""
        notification = Notification.create(
            district_id=district_id,
            type=type,
            title=title,
            body=body,
            congregation_id=congregation_id,
            payload=payload,
        )
        await self._repo.save(notification)
        return notification

    async def list(
        self,
        district_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List visible, non-dismissed notifications for a district."""
        items, total = await self._repo.list_by_district(
            district_id, unread_only=unread_only, limit=limit, offset=offset
        )
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def mark_read(self, notification_id: uuid.UUID) -> bool:
        notification = await self._repo.get(notification_id)
        if notification is None:
            return False
        if not notification.is_read:
            await self._repo.mark_read(notification_id)
        return True

    async def dismiss(self, notification_id: uuid.UUID) -> bool:
        """Dismiss a notification if it exists; repeated dismissals succeed."""
        notification = await self._repo.get(notification_id)
        if notification is None:
            return False
        if not notification.is_dismissed:
            await self._repo.mark_dismissed(notification_id)
        return True

    async def mark_all_read(self, district_id: uuid.UUID, user_sub: str) -> int:
        return await self._repo.mark_all_read(district_id, user_sub)

    async def get_unread_count(self, district_id: uuid.UUID) -> int:
        _, total = await self._repo.list_by_district(district_id, unread_only=True, limit=1)
        return total
