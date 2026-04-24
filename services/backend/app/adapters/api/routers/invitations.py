"""app/adapters/api/routers/invitations.py: Module."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.api.schemas.invitation import (
    InvitationCreate,
    InvitationResponse,
    OverwriteDecisionRequest,
    OverwriteRequestResponse,
)
from app.adapters.auth.permissions import PermissionError, assert_has_role_in_district
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.event import SqlEventRepository
from app.adapters.db.repositories.invitation import SqlInvitationRepository
from app.adapters.db.repositories.invitation_overwrite_request import (
    SqlInvitationOverwriteRequestRepository,
)
from app.application.invitation_service import (
    apply_overwrite_decision,
    create_invitations_for_event,
    delete_invitation,
)
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1", tags=["invitations"])


@router.post(
    "/events/{event_id}/invitations",
    response_model=list[InvitationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_invitations(
    event_id: uuid.UUID,
    body: InvitationCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> list[InvitationResponse]:
    event_repo = SqlEventRepository(db)
    event = await event_repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    try:
        assert_has_role_in_district(auth, Role.PLANNER, event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    try:
        invitations = await create_invitations_for_event(
            db, source_event_id=event_id, targets=body.targets
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    return [
        InvitationResponse(
            id=inv.id,
            source_event_id=inv.source_event_id,
            source_congregation_id=inv.source_congregation_id,
            target_type=inv.target_type,
            target_congregation_id=inv.target_congregation_id,
            external_target_note=inv.external_target_note,
            linked_event_id=inv.linked_event_id,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )
        for inv in invitations
    ]


@router.get("/events/{event_id}/invitations", response_model=list[InvitationResponse])
async def list_event_invitations(
    event_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> list[InvitationResponse]:
    event_repo = SqlEventRepository(db)
    event = await event_repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    try:
        assert_has_role_in_district(auth, Role.VIEWER, event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    invitations = await SqlInvitationRepository(db).list_by_source_event(event_id)
    return [
        InvitationResponse(
            id=inv.id,
            source_event_id=inv.source_event_id,
            source_congregation_id=inv.source_congregation_id,
            target_type=inv.target_type,
            target_congregation_id=inv.target_congregation_id,
            external_target_note=inv.external_target_note,
            linked_event_id=inv.linked_event_id,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )
        for inv in invitations
    ]


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_invitation(
    invitation_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> None:
    invitation = await SqlInvitationRepository(db).get(invitation_id)
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Einladung nicht gefunden"
        )

    event = await SqlEventRepository(db).get(invitation.source_event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    try:
        assert_has_role_in_district(auth, Role.PLANNER, event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    removed = await delete_invitation(db, invitation_id=invitation_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Einladung nicht gefunden"
        )


@router.get("/invitations/overwrite-requests", response_model=list[OverwriteRequestResponse])
async def list_overwrite_requests(
    auth: CurrentUserWithMemberships,
    db: DbSession,
    district_id: uuid.UUID = Query(...),
) -> list[OverwriteRequestResponse]:
    try:
        assert_has_role_in_district(auth, Role.VIEWER, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    req_repo = SqlInvitationOverwriteRequestRepository(db)
    event_repo = SqlEventRepository(db)
    source_repo = SqlCongregationRepository(db)
    requests = await req_repo.list_open_by_district(district_id)

    result: list[OverwriteRequestResponse] = []
    for request in requests:
        source_event = await event_repo.get(request.source_event_id)
        target_event = await event_repo.get(request.target_event_id)
        source_name = None
        if target_event is not None and target_event.invitation_source_congregation_id is not None:
            source_congregation = await source_repo.get(
                target_event.invitation_source_congregation_id
            )
            source_name = source_congregation.name if source_congregation else None
        result.append(
            OverwriteRequestResponse(
                id=request.id,
                invitation_id=request.invitation_id,
                source_event_id=request.source_event_id,
                source_event_title=source_event.title if source_event else source_name,
                target_event_id=request.target_event_id,
                target_event_title=target_event.title if target_event else None,
                target_congregation_id=target_event.congregation_id if target_event else None,
                current_title=target_event.title if target_event else None,
                current_start_at=target_event.start_at if target_event else None,
                current_end_at=target_event.end_at if target_event else None,
                current_description=target_event.description if target_event else None,
                current_category=target_event.category if target_event else None,
                proposed_title=request.proposed_title,
                proposed_start_at=request.proposed_start_at,
                proposed_end_at=request.proposed_end_at,
                proposed_description=request.proposed_description,
                proposed_category=request.proposed_category,
                status=request.status,
                decided_at=request.decided_at,
                created_at=request.created_at,
                updated_at=request.updated_at,
            )
        )
    return result


@router.post(
    "/invitations/overwrite-requests/{request_id}/decision",
    response_model=OverwriteRequestResponse,
)
async def decide_overwrite_request(
    request_id: uuid.UUID,
    body: OverwriteDecisionRequest,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> OverwriteRequestResponse:
    req_repo = SqlInvitationOverwriteRequestRepository(db)
    existing = await req_repo.get(request_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anfrage nicht gefunden")

    target_event = await SqlEventRepository(db).get(existing.target_event_id)
    if target_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ziel-Event nicht gefunden"
        )

    try:
        assert_has_role_in_district(auth, Role.PLANNER, target_event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    updated = await apply_overwrite_decision(db, request_id=request_id, decision=body.decision)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anfrage nicht gefunden")

    source_event = await SqlEventRepository(db).get(updated.source_event_id)
    target_event = await SqlEventRepository(db).get(updated.target_event_id)
    return OverwriteRequestResponse(
        id=updated.id,
        invitation_id=updated.invitation_id,
        source_event_id=updated.source_event_id,
        source_event_title=source_event.title if source_event else None,
        target_event_id=updated.target_event_id,
        target_event_title=target_event.title if target_event else None,
        target_congregation_id=target_event.congregation_id if target_event else None,
        current_title=target_event.title if target_event else None,
        current_start_at=target_event.start_at if target_event else None,
        current_end_at=target_event.end_at if target_event else None,
        current_description=target_event.description if target_event else None,
        current_category=target_event.category if target_event else None,
        proposed_title=updated.proposed_title,
        proposed_start_at=updated.proposed_start_at,
        proposed_end_at=updated.proposed_end_at,
        proposed_description=updated.proposed_description,
        proposed_category=updated.proposed_category,
        status=updated.status,
        decided_at=updated.decided_at,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )
