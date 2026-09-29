from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.external_event_candidate import ExternalEventCandidateORM
from app.domain.models.external_event_candidate import CandidateStatus, ExternalEventCandidate


def _orm_to_domain(row: ExternalEventCandidateORM) -> ExternalEventCandidate:
    return ExternalEventCandidate(
        id=row.id,
        district_id=row.district_id,
        calendar_integration_id=row.calendar_integration_id,
        external_event_id=row.external_event_id,
        source=row.source,
        congregation_id=row.congregation_id,
        title=row.title,
        category=row.category,
        start_at=row.start_at,
        end_at=row.end_at,
        description=row.description,
        content_hash=row.content_hash,
        status=CandidateStatus(row.status),
        matched_slot_id=row.matched_slot_id,
        reviewed_at=row.reviewed_at,
        reviewed_by=row.reviewed_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlExternalEventCandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, candidate_id: UUID, *, for_update: bool = False
    ) -> ExternalEventCandidate | None:
        query = select(ExternalEventCandidateORM).where(
            ExternalEventCandidateORM.id == candidate_id
        )
        if for_update:
            query = query.with_for_update()
        row = (await self._session.execute(query)).scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def by_external_event(
        self, integration_id: UUID, external_id: str
    ) -> ExternalEventCandidate | None:
        query = (
            select(ExternalEventCandidateORM)
            .where(
                ExternalEventCandidateORM.calendar_integration_id == integration_id,
                ExternalEventCandidateORM.external_event_id == external_id,
            )
            .with_for_update()
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list(
        self,
        district_id: UUID,
        status: CandidateStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExternalEventCandidate]:
        query = (
            select(ExternalEventCandidateORM)
            .where(
                ExternalEventCandidateORM.district_id == district_id,
                ExternalEventCandidateORM.status == status,
            )
            .order_by(
                ExternalEventCandidateORM.created_at.desc(),
                ExternalEventCandidateORM.id,
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return [_orm_to_domain(row) for row in rows]

    async def save(self, candidate: ExternalEventCandidate) -> None:
        row = await self._session.get(ExternalEventCandidateORM, candidate.id)
        if row is None:
            row = ExternalEventCandidateORM()
            self._session.add(row)

        row.id = candidate.id
        row.district_id = candidate.district_id
        row.calendar_integration_id = candidate.calendar_integration_id
        row.external_event_id = candidate.external_event_id
        row.source = candidate.source
        row.congregation_id = candidate.congregation_id
        row.title = candidate.title
        row.category = candidate.category
        row.start_at = candidate.start_at
        row.end_at = candidate.end_at
        row.description = candidate.description
        row.content_hash = candidate.content_hash
        row.status = candidate.status
        row.matched_slot_id = candidate.matched_slot_id
        row.reviewed_at = candidate.reviewed_at
        row.reviewed_by = candidate.reviewed_by
        row.created_at = candidate.created_at
        row.updated_at = candidate.updated_at
        await self._session.flush()
