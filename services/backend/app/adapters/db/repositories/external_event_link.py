"""app/adapters/db/repositories/external_event_link.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.external_event_link import ExternalEventLinkORM
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.ports.repositories import ExternalEventLinkRepository


def _orm_to_domain(row: ExternalEventLinkORM) -> ExternalEventLink:
    return ExternalEventLink(
        id=row.id,
        event_instance_id=row.event_instance_id,
        provider=row.provider,
        external_event_id=row.external_event_id,
        last_synced_hash=row.last_synced_hash,
        revision_marker=row.revision_marker,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlExternalEventLinkRepository(ExternalEventLinkRepository):
    """SQLAlchemy repository for ExternalEventLink."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, link_id: uuid.UUID) -> ExternalEventLink | None:
        row = await self._session.get(ExternalEventLinkORM, link_id)
        return _orm_to_domain(row) if row else None

    async def get_by_external_event(
        self, provider: str, external_event_id: str
    ) -> ExternalEventLink | None:
        result = await self._session.execute(
            select(ExternalEventLinkORM).where(
                ExternalEventLinkORM.provider == provider,
                ExternalEventLinkORM.external_event_id == external_event_id,
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list_by_event_instance(
        self, event_instance_id: uuid.UUID
    ) -> list[ExternalEventLink]:
        result = await self._session.execute(
            select(ExternalEventLinkORM).where(
                ExternalEventLinkORM.event_instance_id == event_instance_id,
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def save(self, link: ExternalEventLink) -> None:
        existing = await self._session.get(ExternalEventLinkORM, link.id)
        if existing is None:
            row = ExternalEventLinkORM()
            self._session.add(row)
        else:
            row = existing
        row.id = link.id
        row.event_instance_id = link.event_instance_id
        row.provider = link.provider
        row.external_event_id = link.external_event_id
        row.last_synced_hash = link.last_synced_hash
        row.revision_marker = link.revision_marker
        row.created_at = link.created_at or datetime.now(UTC)
        row.updated_at = link.updated_at or datetime.now(UTC)
        await self._session.flush()

    async def delete(self, link_id: uuid.UUID) -> None:
        row = await self._session.get(ExternalEventLinkORM, link_id)
        if row:
            await self._session.delete(row)
