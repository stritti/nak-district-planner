from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.adapters.api.deps import CurrentUser, DbSession
from app.adapters.api.schemas.leader import (
    LeaderCreate,
    LeaderResponse,
    LeaderSelfLinkRequest,
    LeaderSelfLinkResponse,
    LeaderUpdate,
)
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.domain.models.leader import Leader

router = APIRouter(prefix="/api/v1/districts/{district_id}/leaders", tags=["leaders"])


def _leader_response(leader: Leader) -> LeaderResponse:
    return LeaderResponse(
        id=leader.id,
        name=leader.name,
        district_id=leader.district_id,
        rank=leader.rank,
        congregation_id=leader.congregation_id,
        special_role=leader.special_role,
        user_sub=leader.user_sub,
        email=leader.email,
        phone=leader.phone,
        notes=leader.notes,
        is_active=leader.is_active,
        created_at=leader.created_at,
        updated_at=leader.updated_at,
    )


@router.get("", response_model=list[LeaderResponse])
async def list_leaders(
    district_id: uuid.UUID,
    _: CurrentUser,
    db: DbSession,
) -> list[LeaderResponse]:
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    leaders = await SqlLeaderRepository(db).list_by_district(district_id)
    return [_leader_response(leader) for leader in leaders]


@router.post("", response_model=LeaderResponse, status_code=status.HTTP_201_CREATED)
async def create_leader(
    district_id: uuid.UUID,
    body: LeaderCreate,
    _: CurrentUser,
    db: DbSession,
) -> LeaderResponse:
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    leader = Leader.create(
        name=body.name,
        district_id=district_id,
        rank=body.rank,
        congregation_id=body.congregation_id,
        special_role=body.special_role,
        user_sub=body.user_sub,
        email=body.email,
        phone=body.phone,
        notes=body.notes,
        is_active=body.is_active,
    )
    await SqlLeaderRepository(db).save(leader)
    return _leader_response(leader)


@router.patch("/{leader_id}", response_model=LeaderResponse)
async def update_leader(
    district_id: uuid.UUID,
    leader_id: uuid.UUID,
    body: LeaderUpdate,
    _: CurrentUser,
    db: DbSession,
) -> LeaderResponse:
    repo = SqlLeaderRepository(db)
    leader = await repo.get(leader_id)
    if not leader or leader.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        leader.name = body.name
    if "rank" in fields:
        leader.rank = body.rank
    if "congregation_id" in fields:
        leader.congregation_id = body.congregation_id
    if "special_role" in fields:
        leader.special_role = body.special_role
    if "user_sub" in fields:
        leader.user_sub = body.user_sub
    if "email" in fields:
        leader.email = body.email
    if "phone" in fields:
        leader.phone = body.phone
    if "notes" in fields:
        leader.notes = body.notes
    if "is_active" in fields and body.is_active is not None:
        leader.is_active = body.is_active
    leader.updated_at = datetime.now(timezone.utc)
    await repo.save(leader)
    return _leader_response(leader)


@router.delete("/{leader_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_leader(
    district_id: uuid.UUID,
    leader_id: uuid.UUID,
    _: CurrentUser,
    db: DbSession,
) -> None:
    repo = SqlLeaderRepository(db)
    leader = await repo.get(leader_id)
    if not leader or leader.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )
    await repo.delete(leader_id)


@router.post("/link-self", response_model=LeaderSelfLinkResponse)
async def link_self_to_leader(
    district_id: uuid.UUID,
    body: LeaderSelfLinkRequest,
    user: CurrentUser,
    db: DbSession,
) -> LeaderSelfLinkResponse:
    repo = SqlLeaderRepository(db)
    target = await repo.get(body.leader_id)
    if not target or target.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )

    existing_link = await repo.get_by_user_sub(user.sub, district_id=district_id)
    if existing_link and existing_link.id != target.id:
        existing_link.user_sub = None
        existing_link.updated_at = datetime.now(timezone.utc)
        await repo.save(existing_link)

    if target.user_sub and target.user_sub != user.sub:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dieses Amt ist bereits mit einem anderen Benutzer verknuepft",
        )

    target.user_sub = user.sub
    target.updated_at = datetime.now(timezone.utc)
    await repo.save(target)
    return LeaderSelfLinkResponse(linked=True, leader=_leader_response(target))


@router.delete("/link-self", response_model=LeaderSelfLinkResponse)
async def unlink_self_from_leader(
    district_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> LeaderSelfLinkResponse:
    repo = SqlLeaderRepository(db)
    linked = await repo.get_by_user_sub(user.sub, district_id=district_id)
    if not linked:
        return LeaderSelfLinkResponse(linked=False, leader=None)

    linked.user_sub = None
    linked.updated_at = datetime.now(timezone.utc)
    await repo.save(linked)
    return LeaderSelfLinkResponse(linked=False, leader=None)


@router.get("/link-self", response_model=LeaderSelfLinkResponse)
async def get_self_link(
    district_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> LeaderSelfLinkResponse:
    repo = SqlLeaderRepository(db)
    linked = await repo.get_by_user_sub(user.sub, district_id=district_id)
    if not linked:
        return LeaderSelfLinkResponse(linked=False, leader=None)
    return LeaderSelfLinkResponse(linked=True, leader=_leader_response(linked))
