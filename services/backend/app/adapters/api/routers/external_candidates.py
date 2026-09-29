from datetime import date, datetime, time
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.external_event_candidate import (
    SqlExternalEventCandidateRepository,
)
from app.adapters.db.repositories.external_event_link import SqlExternalEventLinkRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.application.candidate_review import CandidateReviewService
from app.domain.models.external_event_candidate import CandidateStatus
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/external-candidates", tags=["external-candidates"])


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    district_id: UUID
    calendar_integration_id: UUID
    external_event_id: str
    source: str
    congregation_id: UUID | None
    title: str
    category: str | None
    start_at: datetime
    end_at: datetime
    event_date: date
    event_time: time
    description: str | None
    status: CandidateStatus
    matched_slot_id: UUID | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None


class AcceptCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    matched_slot_id: UUID | None = None


@router.get("", response_model=list[CandidateResponse])
async def list_candidates(
    district_id: UUID, auth: CurrentUserWithMemberships, session: DbSession,
    status: CandidateStatus = CandidateStatus.PENDING,
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
):
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    return await SqlExternalEventCandidateRepository(session).list(district_id, status, limit, offset)


async def load_for_review(candidate_id, auth, session):
    repo = SqlExternalEventCandidateRepository(session)
    candidate = await repo.get(candidate_id, for_update=True)
    if candidate is None:
        raise HTTPException(404, "Kandidat nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, candidate.district_id)
    return candidate, CandidateReviewService(repo, SqlPlanningSlotRepository(session), SqlEventInstanceRepository(session), SqlExternalEventLinkRepository(session))


@router.post("/{candidate_id}/accept", response_model=CandidateResponse)
async def accept_candidate(candidate_id: UUID, body: AcceptCandidate, auth: CurrentUserWithMemberships, session: DbSession):
    candidate, service = await load_for_review(candidate_id, auth, session)
    if body.matched_slot_id:
        # Different candidates must not claim the same slot concurrently.
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int.from_bytes(body.matched_slot_id.bytes[:8], "big", signed=True)})
    try:
        return await service.accept(candidate, user_sub=auth.user.sub, slot_id=body.matched_slot_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{candidate_id}/dismiss", response_model=CandidateResponse)
async def dismiss_candidate(candidate_id: UUID, auth: CurrentUserWithMemberships, session: DbSession):
    candidate, service = await load_for_review(candidate_id, auth, session)
    try:
        return await service.dismiss(candidate, user_sub=auth.user.sub)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
