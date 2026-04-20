"""app/adapters/db/repositories/invitation_overwrite_request.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.event import EventORM
from app.adapters.db.orm_models.invitation_overwrite_request import InvitationOverwriteRequestORM
from app.domain.models.invitation import InvitationOverwriteRequest, OverwriteDecisionStatus
from app.domain.ports.repositories import InvitationOverwriteRequestRepository


def _orm_to_domain(row: InvitationOverwriteRequestORM) -> InvitationOverwriteRequest:
    return InvitationOverwriteRequest(
        id=row.id,
        invitation_id=row.invitation_id,
        source_event_id=row.source_event_id,
        target_event_id=row.target_event_id,
        proposed_title=row.proposed_title,
        proposed_start_at=row.proposed_start_at,
        proposed_end_at=row.proposed_end_at,
        proposed_description=row.proposed_description,
        proposed_category=row.proposed_category,
        status=OverwriteDecisionStatus(row.status),
        decided_at=row.decided_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlInvitationOverwriteRequestRepository(InvitationOverwriteRequestRepository):
    """SQLAlchemy repository for InvitationOverwriteRequest."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, request_id: uuid.UUID) -> InvitationOverwriteRequest | None:
        row = await self._session.get(InvitationOverwriteRequestORM, request_id)
        return _orm_to_domain(row) if row else None

    async def list_open_by_district(
        self, district_id: uuid.UUID
    ) -> list[InvitationOverwriteRequest]:
        result = await self._session.execute(
            select(InvitationOverwriteRequestORM)
            .join(EventORM, InvitationOverwriteRequestORM.target_event_id == EventORM.id)
            .where(
                EventORM.district_id == district_id,
                InvitationOverwriteRequestORM.status == OverwriteDecisionStatus.PENDING_OVERWRITE,
            )
            .order_by(InvitationOverwriteRequestORM.created_at.asc())
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_open_by_source_event(
        self, source_event_id: uuid.UUID
    ) -> list[InvitationOverwriteRequest]:
        result = await self._session.execute(
            select(InvitationOverwriteRequestORM).where(
                InvitationOverwriteRequestORM.source_event_id == source_event_id,
                InvitationOverwriteRequestORM.status == OverwriteDecisionStatus.PENDING_OVERWRITE,
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def save(self, request: InvitationOverwriteRequest) -> None:
        existing = await self._session.get(InvitationOverwriteRequestORM, request.id)
        if existing is None:
            row = InvitationOverwriteRequestORM()
            self._session.add(row)
        else:
            row = existing
        row.id = request.id
        row.invitation_id = request.invitation_id
        row.source_event_id = request.source_event_id
        row.target_event_id = request.target_event_id
        row.proposed_title = request.proposed_title
        row.proposed_start_at = request.proposed_start_at
        row.proposed_end_at = request.proposed_end_at
        row.proposed_description = request.proposed_description
        row.proposed_category = request.proposed_category
        row.status = request.status
        row.decided_at = request.decided_at
        row.created_at = request.created_at
        row.updated_at = request.updated_at
        await self._session.flush()

    async def set_status(
        self,
        request_id: uuid.UUID,
        status: OverwriteDecisionStatus,
    ) -> InvitationOverwriteRequest | None:
        row = await self._session.get(InvitationOverwriteRequestORM, request_id)
        if row is None:
            return None
        row.status = status
        row.updated_at = datetime.now(timezone.utc)
        if status != OverwriteDecisionStatus.PENDING_OVERWRITE:
            row.decided_at = row.updated_at
        await self._session.flush()
        return _orm_to_domain(row)
