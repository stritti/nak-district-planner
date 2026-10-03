"""API routes for leader unavailability periods."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_leader_repository,
    get_leader_unavailability_repository,
)
from app.adapters.api.schemas.leader_unavailability import (
    LeaderUnavailabilityCreate,
    LeaderUnavailabilityResponse,
    LeaderUnavailabilityUpdate,
)
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.leader_unavailability import SqlLeaderUnavailabilityRepository
from app.domain.models.leader_unavailability import LeaderUnavailability
from app.domain.models.role import Role

router = APIRouter(
    prefix="/api/v1/districts/{district_id}/leader-unavailabilities",
    tags=["leader-unavailabilities"],
)


def _response(item: LeaderUnavailability) -> LeaderUnavailabilityResponse:
    return LeaderUnavailabilityResponse(
        id=item.id,
        leader_id=item.leader_id,
        start_at=item.start_at,
        end_at=item.end_at,
        reason=item.reason,
        note=item.note,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _leader_for_district(
    leaders: SqlLeaderRepository, district_id: uuid.UUID, leader_id: uuid.UUID
):
    leader = await leaders.get(leader_id)
    if leader is None or leader.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtsträger nicht gefunden"
        )
    return leader


@router.get("", response_model=list[LeaderUnavailabilityResponse])
async def list_unavailabilities(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leader_id: uuid.UUID | None = None,
    leaders: SqlLeaderRepository = Depends(get_leader_repository),
    repo: SqlLeaderUnavailabilityRepository = Depends(get_leader_unavailability_repository),
) -> list[LeaderUnavailabilityResponse]:
    require_role_in_district(auth, Role.VIEWER, district_id)
    if leader_id is not None:
        await _leader_for_district(leaders, district_id, leader_id)
        items = await repo.list_by_leader(leader_id)
    else:
        district_leaders = await leaders.list_by_district(district_id)
        items = [item for leader in district_leaders for item in await repo.list_by_leader(leader.id)]
        items.sort(key=lambda item: item.start_at)
    return [_response(item) for item in items]


@router.post("", response_model=LeaderUnavailabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_unavailability(
    district_id: uuid.UUID,
    body: LeaderUnavailabilityCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders: SqlLeaderRepository = Depends(get_leader_repository),
    repo: SqlLeaderUnavailabilityRepository = Depends(get_leader_unavailability_repository),
) -> LeaderUnavailabilityResponse:
    require_role_in_district(auth, Role.PLANNER, district_id)
    await _leader_for_district(leaders, district_id, body.leader_id)
    item = LeaderUnavailability.create(
        leader_id=body.leader_id,
        start_at=body.start_at,
        end_at=body.end_at,
        reason=body.reason,
        note=body.note,
    )
    await repo.save(item)
    return _response(item)


@router.patch("/{unavailability_id}", response_model=LeaderUnavailabilityResponse)
async def update_unavailability(
    district_id: uuid.UUID,
    unavailability_id: uuid.UUID,
    body: LeaderUnavailabilityUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders: SqlLeaderRepository = Depends(get_leader_repository),
    repo: SqlLeaderUnavailabilityRepository = Depends(get_leader_unavailability_repository),
) -> LeaderUnavailabilityResponse:
    require_role_in_district(auth, Role.PLANNER, district_id)
    item = await repo.get(unavailability_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Abwesenheit nicht gefunden"
        )
    await _leader_for_district(leaders, district_id, item.leader_id)
    fields = body.model_fields_set
    start_at = body.start_at if "start_at" in fields else item.start_at
    end_at = body.end_at if "end_at" in fields else item.end_at
    if end_at <= start_at:
        raise HTTPException(status_code=422, detail="end_at muss nach start_at liegen")
    item.start_at = start_at
    item.end_at = end_at
    if "reason" in fields and body.reason is not None:
        item.reason = body.reason
    if "note" in fields:
        item.note = body.note
    item.updated_at = datetime.now(UTC)
    await repo.save(item)
    return _response(item)


@router.delete("/{unavailability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unavailability(
    district_id: uuid.UUID,
    unavailability_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders: SqlLeaderRepository = Depends(get_leader_repository),
    repo: SqlLeaderUnavailabilityRepository = Depends(get_leader_unavailability_repository),
) -> None:
    require_role_in_district(auth, Role.PLANNER, district_id)
    item = await repo.get(unavailability_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Abwesenheit nicht gefunden"
        )
    await _leader_for_district(leaders, district_id, item.leader_id)
    await repo.delete(unavailability_id)
