# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLAlchemy repository for Notification aggregate."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.notification import NotificationORM
from app.domain.models.notification import Notification, NotificationType
from app.domain.ports.repositories import NotificationRepository


def _orm_to_domain(row: NotificationORM) -> Notification:
    return Notification(
        id=row.id,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        type=NotificationType(row.type),
        title=row.title,
        body=row.body,
        payload=dict(row.payload or {}),
        read_at=row.read_at,
        dismissed_at=row.dismissed_at,
        created_at=row.created_at,
    )


class SqlNotificationRepository(NotificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, notification_id: uuid.UUID) -> Notification | None:
        row = await self._session.get(NotificationORM, notification_id)
        return _orm_to_domain(row) if row else None

    async def list_by_district(
        self,
        district_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        visible = (
            NotificationORM.district_id == district_id,
            NotificationORM.dismissed_at.is_(None),
        )
        query = select(NotificationORM).where(*visible)
        count_query = select(func.count()).select_from(NotificationORM).where(*visible)

        if unread_only:
            query = query.where(NotificationORM.read_at.is_(None))
            count_query = count_query.where(NotificationORM.read_at.is_(None))

        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self._session.execute(
            query.order_by(NotificationORM.created_at.desc(), NotificationORM.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = [_orm_to_domain(row) for row in result.scalars().all()]
        return items, total

    async def save(self, notification: Notification) -> None:
        row = NotificationORM()
        row.id = notification.id
        row.district_id = notification.district_id
        row.congregation_id = notification.congregation_id
        row.type = notification.type
        row.title = notification.title
        row.body = notification.body
        row.payload = notification.payload
        row.read_at = notification.read_at
        row.dismissed_at = notification.dismissed_at
        row.created_at = notification.created_at
        self._session.add(row)
        await self._session.flush()

    async def mark_read(self, notification_id: uuid.UUID) -> None:
        await self._session.execute(
            update(NotificationORM)
            .where(NotificationORM.id == notification_id, NotificationORM.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )

    async def mark_dismissed(self, notification_id: uuid.UUID) -> None:
        """Dismiss idempotently without changing an existing dismissal timestamp."""
        await self._session.execute(
            update(NotificationORM)
            .where(
                NotificationORM.id == notification_id,
                NotificationORM.dismissed_at.is_(None),
            )
            .values(dismissed_at=datetime.now(UTC))
        )

    async def mark_all_read(self, district_id: uuid.UUID, user_sub: str) -> int:
        result = await self._session.execute(
            update(NotificationORM)
            .where(
                NotificationORM.district_id == district_id,
                NotificationORM.read_at.is_(None),
                NotificationORM.dismissed_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        return result.rowcount
