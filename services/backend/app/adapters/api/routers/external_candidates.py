from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_candidate_review_service,
    get_external_event_candidate_repository,
)
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.locks import acquire_advisory_xact_lock
from app.adapters.db.repositories.external_event_candidate import SqlExternalEventCandidateRepository
from app.application.candidate_review import CandidateReviewService
from app.domain.errors import CandidateReviewError
from app.domain.models.external_event_candidate import CandidateStatus, ExternalEventCandidate
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
    district_id: UUID,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    repository: SqlExternalEventCandidateRepository = Depends(
        get_external_event_candidate_repository
    ),
    status: CandidateStatus = CandidateStatus.PENDING,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[ExternalEventCandidate]:
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    return await repository.list(
        district_id,
        status,
        limit,
        offset,
    )


async def load_for_review(
    candidate_id: UUID,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    repository: SqlExternalEventCandidateRepository,
    service: CandidateReviewService,
) -> tuple[ExternalEventCandidate, CandidateReviewService]:
    candidate = await repository.get(candidate_id, for_update=True)
    if candidate is None:
        raise HTTPException(404, "Kandidat nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, candidate.district_id)
    return candidate, service


@router.post("/{candidate_id}/accept", response_model=CandidateResponse)
async def accept_candidate(
    candidate_id: UUID,
    body: AcceptCandidate,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    repository: SqlExternalEventCandidateRepository = Depends(
        get_external_event_candidate_repository
    ),
    service: CandidateReviewService = Depends(get_candidate_review_service),
) -> ExternalEventCandidate:
    candidate, service = await load_for_review(candidate_id, auth, session, repository, service)
    if body.matched_slot_id is not None:
        await acquire_advisory_xact_lock(session, body.matched_slot_id)
    try:
        return await service.accept(
            candidate,
            user_sub=auth.user.sub,
            slot_id=body.matched_slot_id,
        )
    except CandidateReviewError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{candidate_id}/dismiss", response_model=CandidateResponse)
async def dismiss_candidate(
    candidate_id: UUID,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> ExternalEventCandidate:
    candidate, service = await load_for_review(candidate_id, auth, session)
    try:
        return await service.dismiss(candidate, user_sub=auth.user.sub)
    except CandidateReviewError as exc:
        raise HTTPException(409, str(exc)) from exc
