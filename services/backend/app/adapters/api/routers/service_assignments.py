# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/api/routers/service_assignments.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.adapters.api.conflict_http import raise_for_conflicts
from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_event_instance_repository,
    get_leader_repository,
    get_planning_slot_repository,
    get_service_assignment_repository,
)
from app.adapters.api.revisions import slot_revision
from app.adapters.api.schemas.service_assignment import (
    InlineAssignmentChange,
    InlineAssignmentResult,
    ServiceAssignmentCreate,
    ServiceAssignmentResponse,
    ServiceAssignmentUpdate,
)
from app.adapters.api.tenant_references import ensure_leader_in_district
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.locks import acquire_advisory_xact_lock
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.adapters.db.transactional_events import publish_after_commit
from app.application.service_assignment_conflict import check_service_assignment_conflicts
from app.domain.event_payloads import assignment_confirmed
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.role import Role
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment

router = APIRouter(
    prefix="/api/v1/events/{event_id}/assignments",
    tags=["service-assignments"],
)


async def _touch_slot(slots: SqlPlanningSlotRepository, planning_slot: PlanningSlot) -> None:
    """Bump the slot revision: assignments are part of the exported event (UC-05).

    ICS feeds derive DTSTAMP/LAST-MODIFIED/SEQUENCE from the slot's updated_at;
    touching it also covers deletions, which leave no assignment row behind.
    """
    previous = planning_slot.updated_at
    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=UTC)
    planning_slot.updated_at = max(datetime.now(UTC), previous + timedelta(microseconds=1))
    await slots.save(planning_slot)


async def _check_leader(
    db: DbSession,
    *,
    district_id: uuid.UUID,
    event_id: uuid.UUID,
    leader_id: uuid.UUID,
    confirm_warnings: bool,
    exclude_assignment_id: uuid.UUID | None = None,
) -> None:
    """Validate the leader reference and run the conflict check under a per-leader lock.

    The transaction-scoped advisory lock serializes concurrent assignments of the
    same leader, so check-then-insert cannot double-book; it is released on commit.
    """
    await ensure_leader_in_district(db, district_id, leader_id)
    await acquire_advisory_xact_lock(db, leader_id)
    conflicts = await check_service_assignment_conflicts(
        db, event_id=event_id, leader_id=leader_id, exclude_assignment_id=exclude_assignment_id
    )
    raise_for_conflicts(conflicts, confirm_warnings=confirm_warnings)


_ONE_ASSIGNMENT_PER_SLOT = "ix_service_assignments_planning_slot_id"


def _violated_constraint(exc: IntegrityError) -> str | None:
    """Constraint name of the driver error (asyncpg: cause of SQLAlchemy's ``orig``)."""
    driver_error = exc.orig.__cause__ or exc.orig
    return getattr(driver_error, "constraint_name", None)


async def _save(
    assignments_repo: SqlServiceAssignmentRepository, assignment: ServiceAssignment
) -> None:
    """Persist; the unique index allows one assignment per planning slot."""
    try:
        await assignments_repo.save(assignment)
    except IntegrityError as exc:
        if _violated_constraint(exc) != _ONE_ASSIGNMENT_PER_SLOT:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Planungseintrag hat bereits eine Zuweisung",
        ) from exc


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
    slots: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
) -> ServiceAssignmentResponse:
    planning_slot = await slots.get_for_update(event_id)
    if not planning_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Planungseintrag nicht gefunden"
        )

    require_role_in_district(auth, Role.PLANNER, planning_slot.district_id)

    if body.leader_id is not None:
        await _check_leader(
            db,
            district_id=planning_slot.district_id,
            event_id=event_id,
            leader_id=body.leader_id,
            confirm_warnings=body.confirm_warnings,
        )

    assignment = ServiceAssignment.create(
        event_id=event_id,
        leader_id=body.leader_id,
        leader_name=body.leader_name,
        status=body.status,
    )
    await _save(assignments_repo, assignment)
    await _touch_slot(slots, planning_slot)
    return _assignment_response(assignment)


@router.get("", response_model=list[ServiceAssignmentResponse])
async def list_assignments(
    event_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    slots: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
) -> list[ServiceAssignmentResponse]:
    planning_slot = await slots.get(event_id)
    if not planning_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Planungseintrag nicht gefunden"
        )

    require_role_in_district(auth, Role.VIEWER, planning_slot.district_id)

    assignments = await assignments_repo.list_by_planning_slot(event_id)
    return [_assignment_response(a) for a in assignments]


@router.put("/inline", response_model=InlineAssignmentResult)
async def inline_change_assignment(
    event_id: uuid.UUID,
    body: InlineAssignmentChange,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    slots: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    instance_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
) -> InlineAssignmentResult:
    """Change an assigned minister atomically against the event's strong revision.

    Clearing or deleting an assignment must use the existing confirmed dialog,
    not this text-cell mutation.
    """
    slot = await (slots.get_for_update(event_id) if if_match is not None else slots.get(event_id))
    if slot is None:
        raise HTTPException(status_code=404, detail="Planungseintrag nicht gefunden")
    require_role_in_district(auth, Role.PLANNER, slot.district_id)
    if slot.invitation_source_event_id is not None:
        raise HTTPException(status_code=403, detail="Eingeladene Gemeinde darf Gastgeber-Zuweisung nicht ändern.")
    if slot.status != PlanningSlotStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Abgesagte Termine können nicht inline zugewiesen werden.")
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match ist erforderlich.")
    instance = await instance_repo.get_by_planning_slot(event_id, for_update=True)
    if if_match != slot_revision(slot, instance):
        raise HTTPException(status_code=412, detail="Zuweisung wurde zwischenzeitlich geändert.")

    assignments = await assignments_repo.list_by_planning_slot(event_id)
    if len(assignments) > 1:
        raise HTTPException(status_code=409, detail="Mehrere Zuweisungen für Planungseintrag.")
    existing = assignments[0] if assignments else None
    if existing is not None and existing.leader_id == body.leader_id:
        return InlineAssignmentResult(
            **_assignment_response(existing).model_dump(),
            event_revision=slot_revision(slot, instance),
        )

    await _check_leader(
        db,
        district_id=slot.district_id,
        event_id=event_id,
        leader_id=body.leader_id,
        confirm_warnings=body.confirm_warnings,
        exclude_assignment_id=existing.id if existing else None,
    )
    if existing is None:
        assignment = ServiceAssignment.create(
            event_id=event_id,
            leader_id=body.leader_id,
            status=AssignmentStatus.ASSIGNED,
        )
    else:
        assignment = existing
        assignment.leader_id = body.leader_id
        assignment.leader_name = None
        assignment.status = AssignmentStatus.ASSIGNED
        assignment.updated_at = datetime.now(UTC)
    await _save(assignments_repo, assignment)
    await _touch_slot(slots, slot)
    return InlineAssignmentResult(
        **_assignment_response(assignment).model_dump(),
        event_revision=slot_revision(slot, instance),
    )


@router.put("/{assignment_id}", response_model=ServiceAssignmentResponse)
async def update_assignment(
    event_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: ServiceAssignmentUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    slots: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> ServiceAssignmentResponse:
    # Lock the slot before reading its assignment: dependent event updates hold
    # the same lock, so every writer observes a consistent schedule snapshot.
    planning_slot = await slots.get_for_update(event_id)
    if not planning_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Planungseintrag nicht gefunden"
        )
    require_role_in_district(auth, Role.PLANNER, planning_slot.district_id)

    assignment = await assignments_repo.get(assignment_id)
    if not assignment or assignment.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zuweisung nicht gefunden"
        )

    fields = body.model_fields_set
    if "leader_id" in fields:
        if body.leader_id is not None:
            await _check_leader(
                db,
                district_id=planning_slot.district_id,
                event_id=event_id,
                leader_id=body.leader_id,
                confirm_warnings=body.confirm_warnings,
                exclude_assignment_id=assignment.id,
            )
        assignment.leader_id = body.leader_id
    if "leader_name" in fields:
        assignment.leader_name = body.leader_name
    newly_confirmed = (
        body.status == AssignmentStatus.CONFIRMED and assignment.status != AssignmentStatus.CONFIRMED
    )
    if body.status is not None:
        assignment.status = body.status
    assignment.updated_at = datetime.now(UTC)
    await assignments_repo.save(assignment)
    await _touch_slot(slots, planning_slot)
    if newly_confirmed:
        publish_after_commit(
            db,
            assignment_confirmed(
                planning_slot.district_id,
                leader_name=await _leader_display_name(leaders_repo, assignment),
                event_title=planning_slot.title or "",
                event_date=planning_slot.planning_date,
            ),
        )
    return _assignment_response(assignment)


async def _leader_display_name(
    leaders_repo: SqlLeaderRepository, assignment: ServiceAssignment
) -> str:
    if assignment.leader_name:
        return assignment.leader_name
    if assignment.leader_id is None:
        return ""
    leader = await leaders_repo.get(assignment.leader_id)
    return leader.name if leader else ""


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    event_id: uuid.UUID,
    assignment_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    slots: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
) -> None:
    # Lock the slot before reading its assignment: dependent event updates hold
    # the same lock, so every writer observes a consistent schedule snapshot.
    planning_slot = await slots.get_for_update(event_id)
    if not planning_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Planungseintrag nicht gefunden"
        )
    require_role_in_district(auth, Role.PLANNER, planning_slot.district_id)

    assignment = await assignments_repo.get(assignment_id)
    if not assignment or assignment.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zuweisung nicht gefunden"
        )

    await assignments_repo.delete(assignment_id)
    await _touch_slot(slots, planning_slot)
