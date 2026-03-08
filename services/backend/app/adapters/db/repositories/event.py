from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.orm_models.event import EventORM
from app.domain.models.event import Event, EventSource, EventStatus, EventVisibility
from app.domain.ports.repositories import EventRepository


def _orm_to_domain(row: EventORM) -> Event:
    return Event(
        id=row.id,
        title=row.title,
        description=row.description,
        start_at=row.start_at,
        end_at=row.end_at,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        category=row.category,
        source=EventSource(row.source),
        status=EventStatus(row.status),
        visibility=EventVisibility(row.visibility),
        audiences=list(row.audiences or []),
        applicability=[uuid.UUID(str(u)) for u in (row.applicability or [])],
        external_uid=row.external_uid,
        calendar_integration_id=row.calendar_integration_id,
        content_hash=row.content_hash,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _domain_to_orm(event: Event, existing: EventORM | None = None) -> EventORM:
    row = existing or EventORM()
    row.id = event.id
    row.title = event.title
    row.description = event.description
    row.start_at = event.start_at
    row.end_at = event.end_at
    row.district_id = event.district_id
    row.congregation_id = event.congregation_id
    row.category = event.category
    row.source = event.source
    row.status = event.status
    row.visibility = event.visibility
    row.audiences = event.audiences
    row.applicability = event.applicability
    row.external_uid = event.external_uid
    row.calendar_integration_id = event.calendar_integration_id
    row.content_hash = event.content_hash
    row.created_at = event.created_at
    row.updated_at = event.updated_at
    return row


class SqlEventRepository(EventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, event_id: uuid.UUID) -> Event | None:
        row = await self._session.get(EventORM, event_id)
        return _orm_to_domain(row) if row else None

    async def get_by_external_uid(
        self, external_uid: str, calendar_integration_id: uuid.UUID
    ) -> Event | None:
        result = await self._session.execute(
            select(EventORM).where(
                EventORM.external_uid == external_uid,
                EventORM.calendar_integration_id == calendar_integration_id,
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_by_external_uid_district(
        self, external_uid: str, district_id: uuid.UUID
    ) -> Event | None:
        result = await self._session.execute(
            select(EventORM).where(
                EventORM.external_uid == external_uid,
                EventORM.district_id == district_id,
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list(
        self,
        *,
        district_id: uuid.UUID | None = None,
        congregation_id: uuid.UUID | None = None,
        group_id: uuid.UUID | None = None,
        only_district_level: bool = False,
        status: EventStatus | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Event], int]:
        query = select(EventORM)
        count_query = select(func.count()).select_from(EventORM)

        if district_id is not None:
            query = query.where(EventORM.district_id == district_id)
            count_query = count_query.where(EventORM.district_id == district_id)
        if congregation_id is not None:
            query = query.where(EventORM.congregation_id == congregation_id)
            count_query = count_query.where(EventORM.congregation_id == congregation_id)
        elif only_district_level:
            query = query.where(EventORM.congregation_id.is_(None))
            count_query = count_query.where(EventORM.congregation_id.is_(None))
        elif group_id is not None:
            query = query.join(CongregationORM, EventORM.congregation_id == CongregationORM.id)
            query = query.where(CongregationORM.group_id == group_id)
            count_query = count_query.join(
                CongregationORM, EventORM.congregation_id == CongregationORM.id
            )
            count_query = count_query.where(CongregationORM.group_id == group_id)
        if status is not None:
            query = query.where(EventORM.status == status)
            count_query = count_query.where(EventORM.status == status)
        if from_dt is not None:
            query = query.where(EventORM.start_at >= from_dt)
            count_query = count_query.where(EventORM.start_at >= from_dt)
        if to_dt is not None:
            query = query.where(EventORM.start_at <= to_dt)
            count_query = count_query.where(EventORM.start_at <= to_dt)

        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(EventORM.start_at).limit(limit).offset(offset)
        result = await self._session.execute(query)
        rows = result.scalars().all()

        return [_orm_to_domain(r) for r in rows], total

    async def save(self, event: Event) -> None:
        existing = await self._session.get(EventORM, event.id)
        row = _domain_to_orm(event, existing)
        if existing is None:
            self._session.add(row)
        await self._session.flush()
