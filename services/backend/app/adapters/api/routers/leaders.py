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
from app.adapters.api.revisions import entity_revision, next_updated_at
from app.adapters.api.schemas.leader import (
    LeaderAssignmentCreate,
    LeaderAssignmentResponse,
    LeaderAssignmentUpdate,
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
from app.adapters.db.locks import acquire_advisory_xact_lock
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.domain.models.leader import (
    ROLE_LEVEL_MESSAGE,
    Leader,
    LeaderAssignment,
    LeaderRank,
    person_match_key,
    role_fits_level,
)
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/districts/{district_id}/leaders", tags=["leaders"])


class LeaderInlineUpdate(BaseModel):
    """Explicit inline contract: contact data, appointment attributes and activity.

    Notes, user link, list visibility and service end date stay workflow fields
    of the edit dialog. Authorisation, tenant checks and the DISTRICT_ADMIN
    requirement for activity changes are enforced by ``update_leader``.
    """

    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=100)
    rank: LeaderRank | None = None
    is_active: bool | None = None
    confirm_deactivation: bool = Field(
        False,
        description="Must be true to deactivate; an explicit acknowledgement, not a leader field.",
    )


def _touch_leader(leader: Leader) -> None:
    """Advance the revision after any leader write, even within a clock tick."""
    leader.updated_at = next_updated_at(leader.updated_at)


def _leader_revision(leader: Leader) -> str:
    """Opaque strong validator for a leader record."""
    return entity_revision(leader.id, leader.updated_at)


def _assignment_revision(assignment: LeaderAssignment) -> str:
    return entity_revision(assignment.id, assignment.updated_at)


def _assignment_response(assignment: LeaderAssignment) -> LeaderAssignmentResponse:
    return LeaderAssignmentResponse(
        id=assignment.id,
        congregation_id=assignment.congregation_id,
        role=assignment.role,
        is_home=assignment.is_home,
        revision=_assignment_revision(assignment),
    )


def _leader_response(leader: Leader) -> LeaderResponse:
    ordered = sorted(leader.assignments, key=lambda a: (not a.is_home, a.created_at))
    return LeaderResponse(
        id=leader.id,
        name=leader.name,
        district_id=leader.district_id,
        rank=leader.rank,
        assignments=[_assignment_response(a) for a in ordered],
        user_sub=leader.user_sub,
        email=leader.email,
        phone=leader.phone,
        notes=leader.notes,
        is_active=leader.is_active,
        hidden_from_lists=leader.hidden_from_lists,
        service_end_date=leader.service_end_date,
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
    include_inactive: bool = False,
) -> list[LeaderResponse]:
    require_role_in_district(auth, Role.VIEWER, district_id)
    if not await districts.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    if include_inactive:
        require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    leaders = await leaders_repo.list_by_district(district_id)
    if not include_inactive:
        leaders = [
            leader for leader in leaders if leader.is_active and not leader.hidden_from_lists
        ]
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
    for item in body.assignments or []:
        await ensure_congregation_in_district(db, district_id, item.congregation_id)
    if not body.is_active or body.hidden_from_lists or body.service_end_date is not None:
        require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    # One creation at a time per district: two concurrent requests with the same new name
    # must not both pass the duplicate check below before either is committed.
    await acquire_advisory_xact_lock(db, district_id)
    if not body.confirm_duplicate:
        key = person_match_key(body.name)
        matches = [
            known for known in await leaders_repo.list_by_district(district_id)
            if person_match_key(known.name) == key
        ]
        if matches:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "LEADER_DUPLICATE",
                    "message": "Eine Person mit diesem Namen existiert bereits.",
                    # No contact data: the creator may not be allowed to read it.
                    "matches": [
                        {
                            "id": str(known.id),
                            "name": known.name,
                            "congregation_ids": sorted(str(c) for c in known.congregation_ids),
                            "is_active": known.is_active,
                        }
                        for known in matches
                    ],
                },
            )
    leader = Leader.create(
        name=body.name,
        district_id=district_id,
        rank=body.rank,
        user_sub=body.user_sub,
        email=body.email,
        phone=body.phone,
        notes=body.notes,
        is_active=body.is_active,
        hidden_from_lists=body.hidden_from_lists,
        service_end_date=body.service_end_date,
    )
    if body.assignments is not None:
        leader.assignments = [
            LeaderAssignment.create(
                leader.id, district_id, item.congregation_id, item.role, is_home=item.is_home
            )
            for item in body.assignments
        ]
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
    fields = body.model_fields_set
    repo = leaders_repo
    if fields & {"is_active", "hidden_from_lists", "service_end_date"}:
        # Assignment eligibility checks take this same lock before reading the
        # leader. Taking it before the row lock keeps both write paths ordered.
        await acquire_advisory_xact_lock(db, leader_id)
    leader = await (repo.get_for_update(leader_id) if if_match is not None else repo.get(leader_id))
    if not leader or leader.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )
    lifecycle_changed = (
        ("is_active" in fields and body.is_active is not None and body.is_active != leader.is_active)
        or (
            "hidden_from_lists" in fields
            and body.hidden_from_lists is not None
            and body.hidden_from_lists != leader.hidden_from_lists
        )
        or (
            "service_end_date" in fields
            and body.service_end_date != leader.service_end_date
        )
    )
    if lifecycle_changed:
        require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match ist erforderlich.")
    if if_match != _leader_revision(leader):
        raise HTTPException(status_code=412, detail="Datensatz wurde zwischenzeitlich geändert.")
    if "name" in fields and body.name is not None:
        leader.name = body.name
    if "rank" in fields:
        leader.rank = body.rank
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
    if "hidden_from_lists" in fields and body.hidden_from_lists is not None:
        leader.hidden_from_lists = body.hidden_from_lists
    if "service_end_date" in fields:
        leader.service_end_date = body.service_end_date
    _touch_leader(leader)
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
    fields = body.model_fields_set - {"confirm_deactivation"}
    if not fields or any(
        field in fields and getattr(body, field) is None for field in ("name", "rank", "is_active")
    ):
        raise HTTPException(status_code=422, detail="Dieses Feld ist nicht inline editierbar.")
    if body.is_active is False and not body.confirm_deactivation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "deactivation_unconfirmed",
                "message": "Das Deaktivieren muss ausdrücklich bestätigt werden.",
            },
        )
    update = LeaderUpdate.model_validate(
        body.model_dump(exclude_unset=True, exclude={"confirm_deactivation"})
    )
    return await update_leader(
        district_id, leader_id, update, auth, db, leaders_repo=leaders_repo, if_match=if_match,
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
    # Inspect the target's scope before acquiring the write locks.
    candidate = await repo.get(body.leader_id)
    if not candidate or candidate.district_id != district_id:
        raise HTTPException(status_code=404, detail="Amtstragende:r nicht gefunden")
    require_role_in_district(
        auth, Role.VIEWER, district_id,
        congregation_ids_in_district=candidate.congregation_ids or None,
    )

    previous = await repo.get_by_user_sub(auth.user_sub, district_id=district_id)
    ids = {body.leader_id}
    if previous is not None:
        ids.add(previous.id)
    # Stable lock order also prevents a deadlock if two users swap leader links.
    locked = {leader_id: await repo.get_for_update(leader_id) for leader_id in sorted(ids)}
    target = locked[body.leader_id]
    if target is None or target.district_id != district_id:
        raise HTTPException(status_code=404, detail="Amtstragende:r nicht gefunden")
    if target.congregation_ids != candidate.congregation_ids:
        raise HTTPException(status_code=409, detail="Zuordnung wurde zwischenzeitlich geändert.")
    if target.user_sub and target.user_sub != auth.user_sub:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dieses Amt ist bereits mit einem anderen Benutzer verknuepft",
        )
    if previous is not None and previous.id != target.id:
        current = locked[previous.id]
        if current is not None and current.user_sub == auth.user_sub:
            current.user_sub = None
            _touch_leader(current)
            await repo.save(current)

    target.user_sub = auth.user_sub
    _touch_leader(target)
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
    require_role_in_district(
        auth, Role.VIEWER, district_id,
        congregation_ids_in_district=(linked.congregation_ids or None) if linked else None,
    )
    if not linked:
        return LeaderSelfLinkResponse(linked=False, leader=None)

    linked = await repo.get_for_update(linked.id)
    if linked is None or linked.user_sub != auth.user_sub:
        return LeaderSelfLinkResponse(linked=False, leader=None)
    linked.user_sub = None
    _touch_leader(linked)
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
    require_role_in_district(
        auth, Role.VIEWER, district_id,
        congregation_ids_in_district=(linked.congregation_ids or None) if linked else None,
    )
    if not linked:
        return LeaderSelfLinkResponse(linked=False, leader=None)
    return LeaderSelfLinkResponse(linked=True, leader=_leader_response(linked))


def _require_assignment_rights(
    auth: CurrentUserWithMemberships, district_id: uuid.UUID, congregation_id: uuid.UUID | None
) -> None:
    """District planners manage every assignment, congregation planners only their own."""
    require_role_in_district(
        auth, Role.PLANNER, district_id,
        congregation_ids_in_district={congregation_id} if congregation_id else None,
    )


def _assignment_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": message}
    )


async def _locked_leader(
    repo: SqlLeaderRepository, district_id: uuid.UUID, leader_id: uuid.UUID
) -> Leader:
    leader = await repo.get_for_update(leader_id)
    if not leader or leader.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )
    return leader


def _find_assignment(leader: Leader, assignment_id: uuid.UUID) -> LeaderAssignment:
    for assignment in leader.assignments:
        if assignment.id == assignment_id:
            return assignment
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zuordnung nicht gefunden")


def _check_revision(assignment: LeaderAssignment, if_match: str | None) -> None:
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match ist erforderlich.")
    if if_match != _assignment_revision(assignment):
        raise HTTPException(status_code=412, detail="Datensatz wurde zwischenzeitlich geändert.")


@router.post(
    "/{leader_id}/assignments",
    response_model=LeaderAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_leader_assignment(
    district_id: uuid.UUID,
    leader_id: uuid.UUID,
    body: LeaderAssignmentCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> LeaderAssignmentResponse:
    _require_assignment_rights(auth, district_id, body.congregation_id)
    await ensure_congregation_in_district(db, district_id, body.congregation_id)
    leader = await _locked_leader(leaders_repo, district_id, leader_id)
    if any(a.congregation_id == body.congregation_id for a in leader.assignments):
        raise _assignment_error("assignment_exists", "Die Person ist dieser Gemeinde bereits zugeordnet.")
    if body.is_home:
        # Taking over the home flag also changes the previous home assignment.
        previous = leader.home_assignment
        _require_assignment_rights(auth, district_id, previous.congregation_id if previous else None)
        if previous:
            previous.is_home = False
            previous.updated_at = next_updated_at(previous.updated_at)
    assignment = LeaderAssignment.create(
        leader.id, district_id, body.congregation_id, body.role,
        is_home=body.is_home or not leader.assignments,
    )
    leader.assignments.append(assignment)
    await leaders_repo.save(leader)
    return _assignment_response(assignment)


@router.patch("/{leader_id}/assignments/{assignment_id}", response_model=LeaderAssignmentResponse)
async def update_leader_assignment(
    district_id: uuid.UUID,
    leader_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: LeaderAssignmentUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> LeaderAssignmentResponse:
    if body.is_home is False:
        raise HTTPException(
            status_code=422, detail="Eine andere Zuordnung muss zur Heimat-Zuordnung werden."
        )
    leader = await _locked_leader(leaders_repo, district_id, leader_id)
    assignment = _find_assignment(leader, assignment_id)
    _require_assignment_rights(auth, district_id, assignment.congregation_id)
    _check_revision(assignment, if_match)
    fields = body.model_fields_set
    if "role" in fields:
        if not role_fits_level(body.role, assignment.congregation_id):
            raise HTTPException(status_code=422, detail=ROLE_LEVEL_MESSAGE)
        assignment.role = body.role
    if body.is_home and not assignment.is_home:
        previous = leader.home_assignment
        if previous is not None:
            _require_assignment_rights(auth, district_id, previous.congregation_id)
            previous.is_home = False
            previous.updated_at = next_updated_at(previous.updated_at)
        assignment.is_home = True
    assignment.updated_at = next_updated_at(assignment.updated_at)
    await leaders_repo.save(leader)
    return _assignment_response(assignment)


@router.delete(
    "/{leader_id}/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_leader_assignment(
    district_id: uuid.UUID,
    leader_id: uuid.UUID,
    assignment_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> None:
    leader = await _locked_leader(leaders_repo, district_id, leader_id)
    assignment = _find_assignment(leader, assignment_id)
    _require_assignment_rights(auth, district_id, assignment.congregation_id)
    _check_revision(assignment, if_match)
    if len(leader.assignments) == 1:
        raise _assignment_error(
            "last_assignment", "Die letzte Zuordnung kann nicht entfernt werden."
        )
    if assignment.is_home:
        raise _assignment_error(
            "home_assignment",
            "Die Heimat-Zuordnung kann erst entfernt werden, wenn eine andere Zuordnung Heimat ist.",
        )
    leader.assignments.remove(assignment)
    await leaders_repo.save(leader)


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
    await acquire_advisory_xact_lock(db, leader_id)
    leader = await repo.get(leader_id)
    if not leader or leader.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Amtstragende:r nicht gefunden"
        )
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    leader.is_active = False
    leader.hidden_from_lists = True
    leader.updated_at = datetime.now(UTC)
    await repo.save(leader)
