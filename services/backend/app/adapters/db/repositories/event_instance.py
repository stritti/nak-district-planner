# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import uuid
from typing import ClassVar

from sqlalchemy import select

from app.adapters.db.orm_models.event_instance import EventInstanceORM
from app.adapters.db.repository_base import SqlRepository
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.ports.repositories import EventInstanceRepository


def _orm_to_domain(row: EventInstanceORM) -> EventInstance:
    return EventInstance(
        id=row.id,
        planning_slot_id=row.planning_slot_id,
        title=row.title,
        description=row.description,
        actual_start_at=row.actual_start_at,
        actual_end_at=row.actual_end_at,
        source=EventSource(row.source),
        visibility=EventVisibility(row.visibility),
        deviation_flag=row.deviation_flag,
        sync_state=SyncState(row.sync_state),
        external_uid=row.external_uid,
        content_hash=row.content_hash,
        calendar_integration_id=row.calendar_integration_id,
        last_external_modified_at=row.last_external_modified_at,
        last_internal_modified_at=row.last_internal_modified_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlEventInstanceRepository(SqlRepository[EventInstanceORM, EventInstance], EventInstanceRepository):
    orm_type = EventInstanceORM
    _fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "planning_slot_id": "planning_slot_id",
        "title": "title",
        "description": "description",
        "actual_start_at": "actual_start_at",
        "actual_end_at": "actual_end_at",
        "source": "source",
        "visibility": "visibility",
        "deviation_flag": "deviation_flag",
        "sync_state": "sync_state",
        "external_uid": "external_uid",
        "content_hash": "content_hash",
        "calendar_integration_id": "calendar_integration_id",
        "last_external_modified_at": "last_external_modified_at",
        "last_internal_modified_at": "last_internal_modified_at",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }


    async def get(self, instance_id: uuid.UUID) -> EventInstance | None:
        row = await self._session.get(EventInstanceORM, instance_id)
        return _orm_to_domain(row) if row else None

    async def list_by_planning_slot(self, planning_slot_id: uuid.UUID) -> list[EventInstance]:
        """List all EventInstances for a specific PlanningSlot."""
        result = await self._session.execute(
            select(EventInstanceORM).where(EventInstanceORM.planning_slot_id == planning_slot_id)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def get_by_planning_slot(
        self, planning_slot_id: uuid.UUID, *, for_update: bool = False
    ) -> EventInstance | None:
        """Read an instance, optionally locking and refreshing its row for a versioned write."""
        stmt = select(EventInstanceORM).where(EventInstanceORM.planning_slot_id == planning_slot_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list_by_planning_slots(self, slot_ids: list[uuid.UUID]) -> list[EventInstance]:
        """List all EventInstances for multiple PlanningSlots."""
        if not slot_ids:
            return []
        result = await self._session.execute(
            select(EventInstanceORM).where(EventInstanceORM.planning_slot_id.in_(slot_ids))
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def get_by_external_uid(
        self, external_uid: str, calendar_integration_id: uuid.UUID
    ) -> EventInstance | None:
        """Get EventInstance by external UID and integration."""
        result = await self._session.execute(
            select(EventInstanceORM).where(
                EventInstanceORM.external_uid == external_uid,
                EventInstanceORM.calendar_integration_id == calendar_integration_id,
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list_by_calendar_integration(
        self, calendar_integration_id: uuid.UUID
    ) -> list[EventInstance]:
        """List all EventInstances for a CalendarIntegration."""
        result = await self._session.execute(
            select(EventInstanceORM).where(
                EventInstanceORM.calendar_integration_id == calendar_integration_id,
            )
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]


    async def delete(self, instance_id: uuid.UUID) -> None:
        row = await self._session.get(EventInstanceORM, instance_id)
        if row:
            await self._session.delete(row)
            await self._session.flush()
