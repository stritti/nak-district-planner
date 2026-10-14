# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLAlchemy adapters for event mail hooks and their recipients."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.district import DistrictORM
from app.adapters.db.orm_models.event_mail_hook import EventMailHookORM
from app.adapters.db.orm_models.membership import MembershipORM
from app.adapters.db.orm_models.user import UserORM
from app.domain.events import EventType
from app.domain.models.event_mail_hook import EventMailHook
from app.domain.models.role import Role
from app.domain.ports.event_mail_hooks import EventMailHookRepository, RecipientDirectory


def _to_domain(row: EventMailHookORM) -> EventMailHook:
    return EventMailHook(
        id=row.id,
        district_id=row.district_id,
        event_type=EventType(row.event_type),
        recipient_role=Role(row.recipient_role),
        subject_template=row.subject_template,
        body_template=row.body_template,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlEventMailHookRepository(EventMailHookRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, district_id: uuid.UUID, hook_id: uuid.UUID) -> EventMailHook | None:
        row = await self._session.scalar(
            select(EventMailHookORM).where(
                EventMailHookORM.id == hook_id, EventMailHookORM.district_id == district_id
            )
        )
        return _to_domain(row) if row else None

    async def list_by_district(self, district_id: uuid.UUID) -> list[EventMailHook]:
        rows = await self._session.scalars(
            select(EventMailHookORM)
            .where(EventMailHookORM.district_id == district_id)
            .order_by(EventMailHookORM.event_type, EventMailHookORM.created_at)
        )
        return [_to_domain(row) for row in rows]

    async def list_active(
        self, district_id: uuid.UUID, event_type: EventType
    ) -> list[EventMailHook]:
        rows = await self._session.scalars(
            select(EventMailHookORM)
            .where(
                EventMailHookORM.district_id == district_id,
                EventMailHookORM.event_type == event_type.value,
                EventMailHookORM.is_active.is_(True),
            )
            .order_by(EventMailHookORM.created_at)
        )
        return [_to_domain(row) for row in rows]

    async def save(self, hook: EventMailHook) -> None:
        row = await self._session.get(EventMailHookORM, hook.id)
        if row is None:
            row = EventMailHookORM(id=hook.id, district_id=hook.district_id)
            self._session.add(row)
        row.event_type = hook.event_type.value
        row.recipient_role = hook.recipient_role.value
        row.subject_template = hook.subject_template
        row.body_template = hook.body_template
        row.is_active = hook.is_active
        row.created_at = hook.created_at
        row.updated_at = hook.updated_at
        await self._session.flush()


class SqlRecipientDirectory(RecipientDirectory):
    """Same resolution rule as monthly reminders: exact role, district scope."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def emails_for_role(self, district_id: uuid.UUID, role: Role) -> list[str]:
        emails = await self._session.scalars(
            select(UserORM.email)
            .join(MembershipORM, MembershipORM.user_sub == UserORM.sub)
            .where(
                MembershipORM.scope_type == "DISTRICT",
                MembershipORM.scope_id == district_id,
                MembershipORM.role == role.value,
            )
            .distinct()
        )
        return sorted({email for email in emails if email})

    async def district_name(self, district_id: uuid.UUID) -> str | None:
        district = await self._session.get(DistrictORM, district_id)
        return district.name if district else None
