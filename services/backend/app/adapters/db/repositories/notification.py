# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLAlchemy notification repository with independent per-user acknowledgement state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.notification import NotificationORM, NotificationUserStateORM
from app.domain.models.notification import Notification, NotificationType
from app.domain.ports.repositories import NotificationRepository


# Notifications acknowledged before per-user state existed carry a single global
# ``read_at``/``dismissed_at``. It stays authoritative for those legacy rows (new
# rows never set it), so a deploy neither resurrects dismissed notifications nor
# lets one user's acknowledgement affect another's.
def _effective_read_at(state):
    return func.coalesce(state.read_at, NotificationORM.read_at)


def _effective_dismissed_at(state):
    return func.coalesce(state.dismissed_at, NotificationORM.dismissed_at)


def _orm_to_domain(
    row: NotificationORM, state: NotificationUserStateORM | None = None
) -> Notification:
    return Notification(
        id=row.id, district_id=row.district_id, congregation_id=row.congregation_id,
        type=NotificationType(row.type), title=row.title, body=row.body,
        payload=dict(row.payload or {}), created_at=row.created_at,
        read_at=(state.read_at if state is not None else None) or row.read_at,
        dismissed_at=(state.dismissed_at if state is not None else None) or row.dismissed_at,
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
        user_sub: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        state = NotificationUserStateORM
        join_condition = and_(
            state.notification_id == NotificationORM.id, state.user_sub == user_sub
        )
        visibility = [
            NotificationORM.district_id == district_id,
            _effective_dismissed_at(state).is_(None),
        ]
        if unread_only:
            visibility.append(_effective_read_at(state).is_(None))

        total_result = await self._session.execute(
            select(func.count()).select_from(NotificationORM)
            .outerjoin(state, join_condition).where(*visibility)
        )
        result = await self._session.execute(
            select(NotificationORM, state).outerjoin(state, join_condition)
            .where(*visibility)
            .order_by(NotificationORM.created_at.desc(), NotificationORM.id.desc())
            .offset(offset).limit(limit)
        )
        return [
            _orm_to_domain(notification, user_state)
            for notification, user_state in result.all()
        ], total_result.scalar() or 0

    async def save(self, notification: Notification) -> None:
        row = NotificationORM(
            id=notification.id, district_id=notification.district_id,
            congregation_id=notification.congregation_id, type=notification.type,
            title=notification.title, body=notification.body,
            payload=notification.payload, created_at=notification.created_at,
        )
        self._session.add(row)
        await self._session.flush()

    async def mark_read(self, notification_id: uuid.UUID, user_sub: str) -> None:
        statement = insert(NotificationUserStateORM).values(
            notification_id=notification_id, user_sub=user_sub, read_at=datetime.now(UTC)
        )
        await self._session.execute(statement.on_conflict_do_update(
            index_elements=[
                NotificationUserStateORM.notification_id,
                NotificationUserStateORM.user_sub,
            ],
            set_={"read_at": statement.excluded.read_at},
            where=NotificationUserStateORM.read_at.is_(None),
        ))

    async def mark_dismissed(self, notification_id: uuid.UUID, user_sub: str) -> None:
        statement = insert(NotificationUserStateORM).values(
            notification_id=notification_id, user_sub=user_sub,
            dismissed_at=datetime.now(UTC),
        )
        await self._session.execute(statement.on_conflict_do_update(
            index_elements=[
                NotificationUserStateORM.notification_id,
                NotificationUserStateORM.user_sub,
            ],
            set_={"dismissed_at": statement.excluded.dismissed_at},
            where=NotificationUserStateORM.dismissed_at.is_(None),
        ))

    async def mark_all_read(self, district_id: uuid.UUID, user_sub: str) -> int:
        """Atomic upsert of this subject's still visible unread rows."""
        state = NotificationUserStateORM
        rows = (
            select(
                NotificationORM.id, literal(user_sub), literal(datetime.now(UTC)),
            )
            .outerjoin(
                state, and_(
                    state.notification_id == NotificationORM.id,
                    state.user_sub == user_sub,
                ),
            )
            .where(
                NotificationORM.district_id == district_id,
                _effective_read_at(state).is_(None),
                _effective_dismissed_at(state).is_(None),
            )
        )
        statement = insert(state).from_select(
            ["notification_id", "user_sub", "read_at"], rows
        )
        statement = statement.on_conflict_do_update(
            index_elements=[state.notification_id, state.user_sub],
            set_={"read_at": statement.excluded.read_at},
            where=and_(state.read_at.is_(None), state.dismissed_at.is_(None)),
        )
        result = await self._session.execute(statement)
        return result.rowcount
