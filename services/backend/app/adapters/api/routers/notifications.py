# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""API router for in-app notifications."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapters.api.deps import CurrentUserWithMemberships, get_notification_service
from app.adapters.auth.permissions import require_role_in_district
from app.application.notification_service import NotificationService
from app.domain.models.notification import Notification
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _authorized_notification(
    notification: Notification | None,
    auth: CurrentUserWithMemberships,
) -> Notification:
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    require_role_in_district(auth, Role.VIEWER, notification.district_id)
    return notification


@router.get("/{district_id}")
async def list_notifications(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    require_role_in_district(auth, Role.VIEWER, district_id)
    return await service.list(district_id, unread_only=unread_only, limit=limit, offset=offset)


@router.get("/{district_id}/unread-count")
async def unread_count(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    require_role_in_district(auth, Role.VIEWER, district_id)
    count = await service.get_unread_count(district_id)
    return {"count": count}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    service: NotificationService = Depends(get_notification_service),
) -> None:
    _authorized_notification(await service.get(notification_id), auth)
    await service.mark_read(notification_id)


@router.post("/{notification_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_notification(
    notification_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    service: NotificationService = Depends(get_notification_service),
) -> None:
    """Dismiss a notification; repeated requests are idempotent."""
    _authorized_notification(await service.get(notification_id), auth)
    await service.dismiss(notification_id)


@router.post("/{district_id}/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    require_role_in_district(auth, Role.VIEWER, district_id)
    count = await service.mark_all_read(district_id, auth.user.sub)
    return {"marked_read": count}
