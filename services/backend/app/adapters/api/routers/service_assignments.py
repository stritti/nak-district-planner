from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.adapters.api.deps import ApiKeyGuard, DbSession
from app.adapters.api.schemas.service_assignment import (
    ServiceAssignmentCreate,
    ServiceAssignmentResponse,
    ServiceAssignmentUpdate,
)
from app.adapters.db.repositories.event import SqlEventRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.domain.models.service_assignment import ServiceAssignment

router = APIRouter(
    prefix="/api/v1/events/{event_id}/assignments",
    tags=["service-assignments"],
)


@router.post("", response_model=ServiceAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    event_id: uuid.UUID,
    body: ServiceAssignmentCreate,
    _: ApiKeyGuard,
    db: DbSession,
) -> ServiceAssignmentResponse:
    if not await SqlEventRepository(db).get(event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    assignment = ServiceAssignment.create(
        event_id=event_id,
        leader_name=body.leader_name,
        status=body.status,
    )
    await SqlServiceAssignmentRepository(db).save(assignment)
    return ServiceAssignmentResponse(
        id=assignment.id,
        event_id=assignment.event_id,
        leader_name=assignment.leader_name,
        status=assignment.status,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


@router.get("", response_model=list[ServiceAssignmentResponse])
async def list_assignments(
    event_id: uuid.UUID,
    _: ApiKeyGuard,
    db: DbSession,
) -> list[ServiceAssignmentResponse]:
    if not await SqlEventRepository(db).get(event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event nicht gefunden")

    assignments = await SqlServiceAssignmentRepository(db).list_by_event(event_id)
    return [
        ServiceAssignmentResponse(
            id=a.id,
            event_id=a.event_id,
            leader_name=a.leader_name,
            status=a.status,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in assignments
    ]


@router.put("/{assignment_id}", response_model=ServiceAssignmentResponse)
async def update_assignment(
    event_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: ServiceAssignmentUpdate,
    _: ApiKeyGuard,
    db: DbSession,
) -> ServiceAssignmentResponse:
    repo = SqlServiceAssignmentRepository(db)
    assignment = await repo.get(assignment_id)
    if not assignment or assignment.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zuweisung nicht gefunden"
        )

    if body.leader_name is not None:
        assignment.leader_name = body.leader_name
    if body.status is not None:
        assignment.status = body.status
    assignment.updated_at = datetime.now(timezone.utc)
    await repo.save(assignment)
    return ServiceAssignmentResponse(
        id=assignment.id,
        event_id=assignment.event_id,
        leader_name=assignment.leader_name,
        status=assignment.status,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )
