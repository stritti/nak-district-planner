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
from app.adapters.db.repositories import (
    SqlEventInstanceRepository,
    SqlPlanningSlotRepository,
)
from app.adapters.db.repositories.congregation import SqlCongregationRepository
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
    planning_slot = await SqlPlanningSlotRepository(db).get(event_id)
    if planning_slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planungseintrag nicht gefunden")

    try:
        assert_has_role_in_district(auth, Role.PLANNER, planning_slot.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    try:
        invitations = await create_invitations_for_event(
            db, source_planning_slot_id=event_id, targets=body.targets
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
    planning_slot = await SqlPlanningSlotRepository(db).get(event_id)
    if planning_slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planungseintrag nicht gefunden")

    try:
        assert_has_role_in_district(auth, Role.VIEWER, planning_slot.district_id)
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

    planning_slot = await SqlPlanningSlotRepository(db).get(invitation.source_event_id)
    if planning_slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planungseintrag nicht gefunden")

    try:
        assert_has_role_in_district(auth, Role.PLANNER, planning_slot.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    removed = await delete_invitation(db, invitation_id=invitation_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Einladung nicht gefunden"
        )


def _build_overwrite_response(
    request,
    source_slot,
    target_slot,
    instance_by_slot: dict,
) -> OverwriteRequestResponse:
    """Build OverwriteRequestResponse from domain models."""
    src_title = source_slot.title if source_slot else None
    tgt_title = target_slot.title if target_slot else None
    tgt_cong_id = target_slot.congregation_id if target_slot else None

    # Try to get current actual times from target EventInstance
    tgt_instance = instance_by_slot.get(target_slot.id) if target_slot else None
    current_start = tgt_instance.actual_start_at if tgt_instance else None
    current_end = tgt_instance.actual_end_at if tgt_instance else None
    current_desc = tgt_instance.description if tgt_instance else None

    return OverwriteRequestResponse(
        id=request.id,
        invitation_id=request.invitation_id,
        source_event_id=request.source_event_id,
        source_event_title=src_title,
        target_event_id=request.target_event_id,
        target_event_title=tgt_title,
        target_congregation_id=tgt_cong_id,
        current_title=tgt_title,
        current_start_at=current_start,
        current_end_at=current_end,
        current_description=current_desc,
        current_category=target_slot.category if target_slot else None,
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
    slot_repo = SqlPlanningSlotRepository(db)
    instance_repo = SqlEventInstanceRepository(db)

    requests = await req_repo.list_open_by_district(district_id)

    # Collect all slot references (source_event_id and target_event_id are now planning_slot_ids)
    slot_ids = set()
    for req in requests:
        if req.source_event_id:
            slot_ids.add(req.source_event_id)
        if req.target_event_id:
            slot_ids.add(req.target_event_id)

    # Batch-load PlanningSlots
    slots: dict = {}
    instances: dict = {}
    for slot_id in slot_ids:
        slot = await slot_repo.get(slot_id)
        if slot:
            slots[slot_id] = slot
            inst = await instance_repo.get_by_planning_slot(slot_id)
            if inst:
                instances[slot_id] = inst

    return [
        _build_overwrite_response(
            req,
            source_slot=slots.get(req.source_event_id),
            target_slot=slots.get(req.target_event_id),
            instance_by_slot=instances,
        )
        for req in requests
    ]


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
    slot_repo = SqlPlanningSlotRepository(db)
    instance_repo = SqlEventInstanceRepository(db)

    existing = await req_repo.get(request_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anfrage nicht gefunden")

    target_slot = await slot_repo.get(existing.target_event_id)
    if target_slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ziel-Planungseintrag nicht gefunden"
        )

    try:
        assert_has_role_in_district(auth, Role.PLANNER, target_slot.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    updated = await apply_overwrite_decision(db, request_id=request_id, decision=body.decision)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anfrage nicht gefunden")

    source_slot = await slot_repo.get(existing.source_event_id)
    target_slot = await slot_repo.get(existing.target_event_id)
    instances: dict = {}
    if target_slot:
        inst = await instance_repo.get_by_planning_slot(target_slot.id)
        if inst:
            instances[target_slot.id] = inst

    return _build_overwrite_response(
        updated,
        source_slot=source_slot,
        target_slot=target_slot,
        instance_by_slot=instances,
    )
