# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/api/routers/leaders.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_district_repository,
    get_leader_repository,
)
from app.adapters.api.schemas.leader import (
    LeaderCreate,
    LeaderResponse,
    LeaderSelfLinkRequest,
    LeaderSelfLinkResponse,
    LeaderUpdate,
)
from app.adapters.api.tenant_references import ensure_congregation_in_district
from app.adapters.auth.permissions import (
    require_role_in_district,
)
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.domain.models.leader import Leader
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/districts/{district_id}/leaders", tags=["leaders"])


class LeaderInlineUpdate(BaseModel):
    """Explicit contact-only inline contract."""

    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=100)


def _to_utc(timestamp: datetime) -> datetime:
    return timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=UTC)


def _leader_revision(leader: Leader) -> str:
    """Opaque strong validator for a leader record."""
    timestamp = _to_utc(leader.updated_at)
    return '"' + str(leader.id) + ':' + timestamp.isoformat(timespec="microseconds") + '"'


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
        revision=_leader_revision(leader),
    )


@router.get("", response_model=list[LeaderResponse])
async def list_leaders(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    districts: SqlDistrictRepository = Depends(get_district_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> list[LeaderResponse]:
    require_role_in_district(auth, Role.VIEWER, district_id)
    if not await districts.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    leaders = await leaders_repo.list_by_district(district_id)
    return [_leader_response(leader) for leader in leaders]


@router.post("", response_model=LeaderResponse, status_code=status.HTTP_201_CREATED)
async def create_leader(
    district_id: uuid.UUID,
    body: LeaderCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    districts: SqlDistrictRepository = Depends(get_district_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> LeaderResponse:
    require_role_in_district(auth, Role.PLANNER, district_id)
    if not await districts.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    await ensure_congregation_in_district(db, district_id, body.congregation_id)
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
    await leaders_repo.save(leader)
    return _leader_response(leader)


@router.patch("/{leader_id}", response_model=LeaderResponse)
async def update_leader(
    district_id: uuid.UUID,
    leader_id: uuid.UUID,
    body: LeaderUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> LeaderResponse:
    require_role_in_district(auth, Role.PLANNER, district_id)
    repo = leaders_repo
    leader = await (repo.get_for_update(leader_id) if if_match is not None else repo.get(leader_id))
    if not leader or leader.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )
    if if_match is not None and if_match != _leader_revision(leader):
        raise HTTPException(status_code=412, detail="Datensatz wurde zwischenzeitlich geändert.")
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        leader.name = body.name
    if "rank" in fields:
        leader.rank = body.rank
    if "congregation_id" in fields:
        await ensure_congregation_in_district(db, district_id, body.congregation_id)
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
    timestamp = _to_utc(leader.updated_at)
    leader.updated_at = max(datetime.now(UTC), timestamp + timedelta(microseconds=1))
    await repo.save(leader)
    return _leader_response(leader)


@router.patch("/{leader_id}/inline", response_model=LeaderResponse)
async def inline_update_leader(
    district_id: uuid.UUID,
    leader_id: uuid.UUID,
    body: LeaderInlineUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> LeaderResponse:
    """Only non-workflow contact/name fields support inline updates."""
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match ist erforderlich.")
    fields = body.model_fields_set
    if not fields or (
        "name" in fields and body.name is None
    ):
        raise HTTPException(status_code=422, detail="Dieses Feld ist nicht inline editierbar.")
    return await update_leader(
        district_id, leader_id, LeaderUpdate.model_validate(body.model_dump(exclude_unset=True)), auth, db, leaders_repo=leaders_repo, if_match=if_match,
    )


@router.post("/link-self", response_model=LeaderSelfLinkResponse)
async def link_self_to_leader(
    district_id: uuid.UUID,
    body: LeaderSelfLinkRequest,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> LeaderSelfLinkResponse:
    repo = leaders_repo
    target = await repo.get(body.leader_id)
    if not target or target.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )
    congregation_ids = {target.congregation_id} if target.congregation_id else None
    require_role_in_district(
        auth, Role.VIEWER, district_id, congregation_ids_in_district=congregation_ids
    )

    existing_link = await repo.get_by_user_sub(auth.user_sub, district_id=district_id)
    if existing_link and existing_link.id != target.id:
        existing_link.user_sub = None
        existing_link.updated_at = datetime.now(UTC)
        await repo.save(existing_link)

    if target.user_sub and target.user_sub != auth.user_sub:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dieses Amt ist bereits mit einem anderen Benutzer verknuepft",
        )

    target.user_sub = auth.user_sub
    target.updated_at = datetime.now(UTC)
    await repo.save(target)
    return LeaderSelfLinkResponse(linked=True, leader=_leader_response(target))


@router.delete("/link-self", response_model=LeaderSelfLinkResponse)
async def unlink_self_from_leader(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    districts: SqlDistrictRepository = Depends(get_district_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> LeaderSelfLinkResponse:
    repo = leaders_repo
    linked = await repo.get_by_user_sub(auth.user_sub, district_id=district_id)
    congregation_ids = {linked.congregation_id} if linked and linked.congregation_id else None
    require_role_in_district(
        auth, Role.VIEWER, district_id, congregation_ids_in_district=congregation_ids
    )
    if not linked:
        return LeaderSelfLinkResponse(linked=False, leader=None)

    linked.user_sub = None
    linked.updated_at = datetime.now(UTC)
    await repo.save(linked)
    return LeaderSelfLinkResponse(linked=False, leader=None)


@router.get("/link-self", response_model=LeaderSelfLinkResponse)
async def get_self_link(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    districts: SqlDistrictRepository = Depends(get_district_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> LeaderSelfLinkResponse:
    repo = leaders_repo
    linked = await repo.get_by_user_sub(auth.user_sub, district_id=district_id)
    congregation_ids = {linked.congregation_id} if linked and linked.congregation_id else None
    require_role_in_district(
        auth, Role.VIEWER, district_id, congregation_ids_in_district=congregation_ids
    )
    if not linked:
        return LeaderSelfLinkResponse(linked=False, leader=None)
    return LeaderSelfLinkResponse(linked=True, leader=_leader_response(linked))


@router.delete("/{leader_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_leader(
    district_id: uuid.UUID,
    leader_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> None:
    require_role_in_district(auth, Role.PLANNER, district_id)
    repo = leaders_repo
    leader = await repo.get(leader_id)
    if not leader or leader.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )
    await repo.delete(leader_id)
