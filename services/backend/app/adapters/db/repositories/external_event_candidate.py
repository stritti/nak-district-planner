from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select

from app.adapters.db.orm_models.external_event_candidate import ExternalEventCandidateORM
from app.domain.models.external_event_candidate import CandidateStatus, ExternalEventCandidate


def to_domain(row):
    if row is None:
        return None
    values = {name: getattr(row, name) for name in ExternalEventCandidate.__dataclass_fields__}
    values["status"] = CandidateStatus(values["status"])
    return ExternalEventCandidate(**values)


class SqlExternalEventCandidateRepository:
    def __init__(self, session):
        self.session = session

    async def get(self, candidate_id: UUID, *, for_update=False):
        query = select(ExternalEventCandidateORM).where(ExternalEventCandidateORM.id == candidate_id)
        if for_update:
            query = query.with_for_update()
        return to_domain((await self.session.execute(query)).scalar_one_or_none())

    async def by_external_event(self, integration_id: UUID, external_id: str):
        query = select(ExternalEventCandidateORM).where(
            ExternalEventCandidateORM.calendar_integration_id == integration_id,
            ExternalEventCandidateORM.external_event_id == external_id,
        ).with_for_update()
        return to_domain((await self.session.execute(query)).scalar_one_or_none())

    async def list(self, district_id: UUID, status: CandidateStatus, limit=100, offset=0):
        query = select(ExternalEventCandidateORM).where(
            ExternalEventCandidateORM.district_id == district_id,
            ExternalEventCandidateORM.status == status,
        ).order_by(ExternalEventCandidateORM.created_at.desc(), ExternalEventCandidateORM.id).limit(limit).offset(offset)
        return [to_domain(row) for row in (await self.session.execute(query)).scalars().all()]

    async def save(self, candidate: ExternalEventCandidate):
        await self.session.merge(ExternalEventCandidateORM(**asdict(candidate)))
        await self.session.flush()
