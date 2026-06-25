"""API router for in-app notifications (Task Group 2.1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.api.deps import get_current_user, get_notification_service
from app.application.notification_service import NotificationService
from app.domain.models.user import User

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/{district_id}")
async def list_notifications(
    district_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    _user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """List notifications for a district, newest first."""
    return await service.list(district_id, unread_only=unread_only, limit=limit, offset=offset)


@router.get("/{district_id}/unread-count")
async def unread_count(
    district_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Get unread notification count for a district."""
    count = await service.get_unread_count(district_id)
    return {"count": count}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    """Mark a single notification as read."""
    ok = await service.mark_read(notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/{district_id}/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    district_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Mark all unread notifications as read for a district."""
    count = await service.mark_all_read(district_id, _user.sub)
    return {"marked_read": count}
