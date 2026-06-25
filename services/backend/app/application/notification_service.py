"""Application service for the notification system."""

from __future__ import annotations

import uuid

from app.domain.models.notification import Notification, NotificationType
from app.domain.ports.repositories import NotificationRepository


class NotificationService:
    """Creates and manages in-app notifications."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        self._repo = notification_repo

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
        """List notifications for a district."""
        items, total = await self._repo.list_by_district(
            district_id, unread_only=unread_only, limit=limit, offset=offset
        )
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def mark_read(self, notification_id: uuid.UUID) -> bool:
        """Mark a single notification as read."""
        notification = await self._repo.get(notification_id)
        if notification is None:
            return False
        notification.mark_read()
        await self._repo.mark_read(notification_id)
        return True

    async def mark_all_read(self, district_id: uuid.UUID, user_sub: str) -> int:
        """Mark all unread notifications as read for a district."""
        return await self._repo.mark_all_read(district_id, user_sub)

    async def get_unread_count(self, district_id: uuid.UUID) -> int:
        """Get the count of unread notifications for a district."""
        _, total = await self._repo.list_by_district(district_id, unread_only=True, limit=1)
        return total
