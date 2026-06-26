"""API router for in-app notifications (Task Group 2.1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    get_current_user_with_memberships,
    get_notification_service,
)
from app.adapters.auth.permissions import PermissionError, assert_has_role_in_district
from app.application.notification_service import NotificationService
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/{district_id}")
async def list_notifications(
    district_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    auth: CurrentUserWithMemberships = Depends(get_current_user_with_memberships),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """List notifications for a district, newest first."""
    try:
        assert_has_role_in_district(auth, Role.VIEWER, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return await service.list(district_id, unread_only=unread_only, limit=limit, offset=offset)


@router.get("/{district_id}/unread-count")
async def unread_count(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships = Depends(get_current_user_with_memberships),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Get unread notification count for a district."""
    try:
        assert_has_role_in_district(auth, Role.VIEWER, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    count = await service.get_unread_count(district_id)
    return {"count": count}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: uuid.UUID,
    auth: CurrentUserWithMemberships = Depends(get_current_user_with_memberships),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    """Mark a single notification as read."""
    notification = await service.get(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    try:
        assert_has_role_in_district(auth, Role.VIEWER, notification.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    await service.mark_read(notification_id)


@router.post("/{district_id}/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships = Depends(get_current_user_with_memberships),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Mark all unread notifications as read for a district."""
    try:
        assert_has_role_in_district(auth, Role.VIEWER, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    count = await service.mark_all_read(district_id, auth.user.sub)
    return {"marked_read": count}
