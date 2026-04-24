"""app/adapters/db/repositories/invitation.py: Module."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.invitation import CongregationInvitationORM
from app.domain.models.invitation import CongregationInvitation, InvitationTargetType
from app.domain.ports.repositories import InvitationRepository


def _orm_to_domain(row: CongregationInvitationORM) -> CongregationInvitation:
    return CongregationInvitation(
        id=row.id,
        source_event_id=row.source_event_id,
        source_congregation_id=row.source_congregation_id,
        target_type=InvitationTargetType(row.target_type),
        target_congregation_id=row.target_congregation_id,
        external_target_note=row.external_target_note,
        linked_event_id=row.linked_event_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlInvitationRepository(InvitationRepository):
    """SQLAlchemy repository for Invitation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, invitation_id: uuid.UUID) -> CongregationInvitation | None:
        row = await self._session.get(CongregationInvitationORM, invitation_id)
        return _orm_to_domain(row) if row else None

    async def list_by_source_event(
        self, source_event_id: uuid.UUID
    ) -> list[CongregationInvitation]:
        result = await self._session.execute(
            select(CongregationInvitationORM).where(
                CongregationInvitationORM.source_event_id == source_event_id
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_by_source_events(
        self, source_event_ids: list[uuid.UUID]
    ) -> list[CongregationInvitation]:
        if not source_event_ids:
            return []
        result = await self._session.execute(
            select(CongregationInvitationORM).where(
                CongregationInvitationORM.source_event_id.in_(source_event_ids)
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def save(self, invitation: CongregationInvitation) -> None:
        existing = await self._session.get(CongregationInvitationORM, invitation.id)
        if existing is None:
            row = CongregationInvitationORM()
            self._session.add(row)
        else:
            row = existing
        row.id = invitation.id
        row.source_event_id = invitation.source_event_id
        row.source_congregation_id = invitation.source_congregation_id
        row.target_type = invitation.target_type
        row.target_congregation_id = invitation.target_congregation_id
        row.external_target_note = invitation.external_target_note
        row.linked_event_id = invitation.linked_event_id
        row.created_at = invitation.created_at
        row.updated_at = invitation.updated_at
        await self._session.flush()

    async def delete(self, invitation_id: uuid.UUID) -> None:
        row = await self._session.get(CongregationInvitationORM, invitation_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()
