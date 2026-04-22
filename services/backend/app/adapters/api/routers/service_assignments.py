"""app/adapters/api/routers/service_assignments.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.api.schemas.service_assignment import (
    ServiceAssignmentCreate,
    ServiceAssignmentResponse,
    ServiceAssignmentUpdate,
)
from app.adapters.auth.permissions import (
    PermissionError,
    assert_has_role_in_district,
)
from app.adapters.db.repositories.event import SqlEventRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.domain.models.role import Role
from app.domain.models.service_assignment import ServiceAssignment

router = APIRouter(
    prefix="/api/v1/events/{event_id}/assignments",
    tags=["service-assignments"],
)


def _assignment_response(assignment: ServiceAssignment) -> ServiceAssignmentResponse:
    return ServiceAssignmentResponse(
        id=assignment.id,
        event_id=assignment.event_id,
        leader_id=assignment.leader_id,
        leader_name=assignment.leader_name,
        status=assignment.status,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


@router.post("", response_model=ServiceAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    event_id: uuid.UUID,
    body: ServiceAssignmentCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> ServiceAssignmentResponse:
    event_repo = SqlEventRepository(db)
    event = await event_repo.get(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    # Check if user has PLANNER role (or higher) in the district
    try:
        assert_has_role_in_district(auth, Role.PLANNER, event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    assignment = ServiceAssignment.create(
        event_id=event_id,
        leader_id=body.leader_id,
        leader_name=body.leader_name,
        status=body.status,
    )
    await SqlServiceAssignmentRepository(db).save(assignment)
    return _assignment_response(assignment)


@router.get("", response_model=list[ServiceAssignmentResponse])
async def list_assignments(
    event_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> list[ServiceAssignmentResponse]:
    event_repo = SqlEventRepository(db)
    event = await event_repo.get(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    # Check if user has VIEWER role (or higher) in the district
    try:
        assert_has_role_in_district(auth, Role.VIEWER, event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    assignments = await SqlServiceAssignmentRepository(db).list_by_event(event_id)
    return [_assignment_response(a) for a in assignments]


@router.put("/{assignment_id}", response_model=ServiceAssignmentResponse)
async def update_assignment(
    event_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: ServiceAssignmentUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> ServiceAssignmentResponse:
    repo = SqlServiceAssignmentRepository(db)
    assignment = await repo.get(assignment_id)
    if not assignment or assignment.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zuweisung nicht gefunden"
        )

    # Get the event to check district access
    event_repo = SqlEventRepository(db)
    event = await event_repo.get(assignment.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    # Check if user has PLANNER role (or higher) in the district
    try:
        assert_has_role_in_district(auth, Role.PLANNER, event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    fields = body.model_fields_set
    if "leader_id" in fields:
        assignment.leader_id = body.leader_id
    if "leader_name" in fields:
        assignment.leader_name = body.leader_name
    if body.status is not None:
        assignment.status = body.status
    assignment.updated_at = datetime.now(UTC)
    await repo.save(assignment)
    return _assignment_response(assignment)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    event_id: uuid.UUID,
    assignment_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> None:
    repo = SqlServiceAssignmentRepository(db)
    assignment = await repo.get(assignment_id)
    if not assignment or assignment.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zuweisung nicht gefunden"
        )

    event_repo = SqlEventRepository(db)
    event = await event_repo.get(assignment.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    try:
        assert_has_role_in_district(auth, Role.PLANNER, event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    await repo.delete(assignment_id)
