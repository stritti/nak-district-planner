# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Router for the /api/v1/events endpoints.

Exposes PlanningSlot + EventInstance under the events API using typed
Pydantic schemas. Validation of enum values, UUIDs and datetimes is done
by Pydantic — the handlers only contain business logic.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from app.adapters.api.conflict_http import conflict_items, raise_for_conflicts
from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_congregation_repository,
    get_event_instance_repository,
    get_leader_repository,
    get_planning_slot_repository,
    get_service_assignment_repository,
)
from app.adapters.api.revisions import aware_timestamp, slot_revision
from app.adapters.api.schemas.conflict import ConflictItem
from app.adapters.api.tenant_references import ensure_leader_in_district
from app.adapters.auth.permissions import has_role_in_district, require_role_in_district
from app.adapters.db.locks import acquire_advisory_xact_lock
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.adapters.db.transactional_events import publish_after_commit
from app.application.deviation_service import DeviationService
from app.application.service_assignment_conflict import (
    ProposedService,
    check_service_assignment_conflicts,
)
from app.application.sync_service import push_conflict_resolution, push_deviation_resolution
from app.domain.errors import UnsupportedCalendarTypeError
from app.domain.event_payloads import plan_finalized
from app.domain.models.event_instance import (
    EventInstance,
    EventSource,
    EventVisibility,
    SyncState,
)
from app.domain.models.planning_slot import (
    DeletedPlanningSlotError,
    EventApprovalStatus,
    InvalidApplicabilityError,
    PlanningSlot,
    PlanningSlotStatus,
    ReleasedEventError,
)
from app.domain.models.role import Role
from app.domain.models.service_assignment import AssignmentStatus
from app.domain.ports.calendar import CalendarConnectorError, OccurrenceWriteBackError
from app.domain.services.sync_policy import internal_state, resolve_conflict

router = APIRouter(prefix="/api/v1/events", tags=["events"])

SERVICE_CATEGORY = "Gottesdienst"


class EventResponsible(BaseModel):
    """Person in charge of an event; for a Gottesdienst this is the Dienstleiter."""

    assignment_id: uuid.UUID
    leader_id: uuid.UUID | None
    name: str
    status: AssignmentStatus


class EventResponse(BaseModel):
    """Event as seen by the frontend: PlanningSlot + optional EventInstance."""

    id: uuid.UUID
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    category: str | None
    is_service: bool
    source: EventSource
    status: PlanningSlotStatus
    approval_status: EventApprovalStatus | None
    was_released: bool
    visibility: EventVisibility
    applicability: list[str]
    invitation_source_congregation_id: uuid.UUID | None = None
    invitation_source_event_id: uuid.UUID | None = None
    sync_state: SyncState | None = None
    responsible: EventResponsible | None = None
    created_at: datetime
    updated_at: datetime
    revision: str


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    limit: int
    offset: int


class EventCreate(BaseModel):
    """Create a manual, initially unpublished planning slot and occurrence."""

    model_config = ConfigDict(extra="forbid")

    district_id: uuid.UUID
    congregation_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category: str | None = Field(default=None, max_length=255)
    start_at: datetime
    end_at: datetime
    visibility: EventVisibility = EventVisibility.PUBLIC
    applicability: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(
        default_factory=list, max_length=500
    )


class EventInlineUpdate(BaseModel):
    """Explicit scalar-only contract; reject future workflow fields by default."""

    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None


class EventUpdate(BaseModel):
    """Strict full-editor request, including explicit workflow acknowledgement."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    congregation_id: uuid.UUID | None = None
    status: PlanningSlotStatus | None = None
    approval_status: EventApprovalStatus | None = None
    category: str | None = Field(None, max_length=255)
    applicability: list[Annotated[str, Field(min_length=1, max_length=64)]] | None = Field(
        None, max_length=500
    )
    confirm_warnings: bool = Field(
        False,
        description="Acknowledge WARN conflicts on dependent changes; not an event data field.",
    )


class EventChangeImpactRequest(BaseModel):
    """Schedule fields for a dry-run impact check; nothing is persisted."""

    model_config = ConfigDict(extra="forbid")

    start_at: datetime | None = None
    end_at: datetime | None = None
    congregation_id: uuid.UUID | None = None


class EventChangeImpactItem(BaseModel):
    assignment_id: uuid.UUID
    leader_id: uuid.UUID
    conflicts: list[ConflictItem]


class EventChangeImpact(BaseModel):
    blocked: bool
    requires_confirmation: bool
    items: list[EventChangeImpactItem]


class BulkApprovalStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int = Field(ge=1900, le=9999)
    month: int = Field(ge=1, le=12)
    approval_status: EventApprovalStatus
    congregation_id: uuid.UUID | None = None


class BulkApprovalStatusResponse(BaseModel):
    updated_count: int


def _slot_start_at(slot: PlanningSlot) -> datetime:
    return datetime.combine(slot.planning_date, slot.planning_time or time.min, tzinfo=UTC)


def _slot_to_event(
    slot: PlanningSlot,
    instance: EventInstance | None,
    responsible: EventResponsible | None = None,
) -> EventResponse:
    return EventResponse(
        id=slot.id,
        title=instance.title if instance else (slot.title or ""),
        description=instance.description if instance else None,
        start_at=instance.actual_start_at if instance else _slot_start_at(slot),
        end_at=instance.actual_end_at if instance else _slot_start_at(slot),
        district_id=slot.district_id,
        congregation_id=slot.congregation_id,
        category=slot.category,
        is_service=slot.category == SERVICE_CATEGORY,
        source=instance.source if instance else EventSource.INTERNAL,
        status=slot.status,
        approval_status=slot.approval_status,
        was_released=slot.was_released,
        visibility=instance.visibility if instance else EventVisibility.PUBLIC,
        applicability=list(slot.applicability or []),
        invitation_source_congregation_id=slot.invitation_source_congregation_id,
        invitation_source_event_id=slot.invitation_source_event_id,
        sync_state=instance.sync_state if instance else None,
        responsible=responsible,
        created_at=slot.created_at,
        updated_at=slot.updated_at,
        revision=slot_revision(slot, instance),
    )


async def _load_instances(
    inst_repo: SqlEventInstanceRepository, slot_ids: list[uuid.UUID]
) -> dict[uuid.UUID, EventInstance]:
    instances = await inst_repo.list_by_planning_slots(slot_ids)
    return {inst.planning_slot_id: inst for inst in instances}


async def _load_responsible(
    assignments_repo: SqlServiceAssignmentRepository,
    leaders_repo: SqlLeaderRepository,
    slots: list[PlanningSlot],
) -> dict[uuid.UUID, EventResponsible]:
    """Responsible person per slot id (first assignment wins, as in the matrix)."""
    assignments = await assignments_repo.list_by_planning_slots([s.id for s in slots])
    district_by_slot = {s.id: s.district_id for s in slots}
    leader_ids = {a.leader_id for a in assignments if a.leader_id is not None}
    leaders = {lid: await leaders_repo.get(lid) for lid in leader_ids}
    result: dict[uuid.UUID, EventResponsible] = {}
    for a in assignments:
        slot_id = a.planning_slot_id or a.event_id
        if slot_id in result or slot_id not in district_by_slot:
            continue
        leader = leaders.get(a.leader_id) if a.leader_id is not None else None
        # Never expose a leader of another tenant, even for inconsistent rows.
        if leader is not None and leader.district_id != district_by_slot[slot_id]:
            leader = None
        if leader is not None:
            name = f"{leader.rank.value} {leader.name}" if leader.rank else leader.name
        else:
            name = a.leader_name or ""
        result[slot_id] = EventResponsible(
            assignment_id=a.id, leader_id=a.leader_id, name=name, status=a.status
        )
    return result


@router.get("", response_model=EventListResponse)
async def list_events(
    auth: CurrentUserWithMemberships,
    session: DbSession,
    district_id: uuid.UUID | None = Query(None),
    congregation_id: uuid.UUID | None = Query(None),
    group_id: uuid.UUID | None = Query(None),
    only_district_level: bool = Query(False),
    status_filter: PlanningSlotStatus | None = Query(None, alias="status"),
    approval_status: EventApprovalStatus | None = Query(None),
    is_service: bool | None = Query(None),
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    inst_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> EventListResponse:
    if district_id is None and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="district_id ist erforderlich, außer für Superadmin.",
        )
    if district_id is not None:
        require_role_in_district(auth, Role.VIEWER, district_id)

    now = datetime.now(UTC).date()
    from_date = aware_timestamp(from_dt).date() if from_dt is not None else now - timedelta(days=365)
    to_date = aware_timestamp(to_dt).date() if to_dt is not None else now + timedelta(days=365 * 2)

    all_slots = await slot_repo.list_for_date_range(
        district_id=district_id or uuid.UUID(int=0),
        from_date=from_date,
        to_date=to_date,
    )

    if group_id is not None:
        congregations = await cong_repo.list_by_district(district_id or uuid.UUID(int=0))
        group_congregation_ids = {c.id for c in congregations if c.group_id == group_id}
        all_slots = [
            s
            for s in all_slots
            if s.congregation_id is None or s.congregation_id in group_congregation_ids
        ]

    if only_district_level:
        all_slots = [s for s in all_slots if s.congregation_id is None]
    elif congregation_id is not None:
        # Own slots in every state; district slots only once released (UC-04).
        all_slots = [
            s
            for s in all_slots
            if s.congregation_id == congregation_id
            or (s.status == PlanningSlotStatus.ACTIVE and s.is_distributed_to(congregation_id))
        ]

    if status_filter is not None:
        all_slots = [s for s in all_slots if s.status == status_filter]
    if approval_status is not None:
        all_slots = [s for s in all_slots if s.approval_status == approval_status]
    if is_service is not None:
        all_slots = [s for s in all_slots if (s.category == SERVICE_CATEGORY) == is_service]

    total = len(all_slots)
    page = all_slots[offset : offset + limit]
    instances = await _load_instances(inst_repo, [s.id for s in page])
    responsible = await _load_responsible(assignments_repo, leaders_repo, page)
    return EventListResponse(
        items=[_slot_to_event(s, instances.get(s.id), responsible.get(s.id)) for s in page],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreate,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    inst_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
) -> EventResponse:
    require_role_in_district(auth, Role.PLANNER, body.district_id)
    start_at = aware_timestamp(body.start_at).astimezone(UTC)
    end_at = aware_timestamp(body.end_at).astimezone(UTC)
    if end_at <= start_at:
        raise HTTPException(status_code=400, detail="end_at muss nach start_at liegen.")

    if body.congregation_id is not None:
        congregation = await cong_repo.get(body.congregation_id)
        if congregation is None or congregation.district_id != body.district_id:
            raise HTTPException(status_code=400, detail="Gemeinde gehört nicht zum Bezirk.")
        if body.applicability:
            raise HTTPException(status_code=400, detail="Gemeindetermine dürfen nicht verteilt werden.")

    slot = PlanningSlot.create(
        district_id=body.district_id,
        congregation_id=body.congregation_id,
        title=body.title,
        category=body.category,
        approval_status=EventApprovalStatus.PLANNED,
        planning_date=start_at.date(),
        planning_time=start_at.timetz().replace(tzinfo=None),
    )
    if body.congregation_id is None and body.applicability:
        congregations = await cong_repo.list_by_district(body.district_id)
        try:
            slot.distribute_to(body.applicability, {c.id for c in congregations})
        except InvalidApplicabilityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    instance = EventInstance.create(
        planning_slot_id=slot.id,
        title=body.title,
        description=body.description,
        actual_start_at=start_at,
        actual_end_at=end_at,
        source=EventSource.INTERNAL,
        visibility=body.visibility,
    )
    try:
        await slot_repo.save(slot)
        await inst_repo.save(instance)
    except IntegrityError as exc:
        # A competing planner may have taken the same congregation/time.
        # The failing flush poisons the DB transaction until it is rolled back.
        await session.rollback()
        sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
        if sqlstate == "23505":
            raise HTTPException(
                status_code=409,
                detail="Für diese Gemeinde besteht bereits ein Termin zu diesem Zeitpunkt.",
            ) from exc
        raise
    return _slot_to_event(slot, instance)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
) -> None:
    slot = await slot_repo.get(event_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Ereignis nicht gefunden")
    require_role_in_district(auth, Role.PLANNER, slot.district_id)
    if slot.was_released:
        raise HTTPException(status_code=409, detail="Freigegebene Ereignisse dürfen nur abgesagt werden.")
    try:
        # Repository rechecks publication under a row lock; FK cascades remove
        # EventInstance and linked assignments in the same transaction.
        await slot_repo.delete(event_id)
    except ReleasedEventError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _proposed_service(
    slot: PlanningSlot,
    instance: EventInstance | None,
    body: EventUpdate | EventChangeImpactRequest,
) -> ProposedService:
    """Apply the requested schedule fields without touching the persisted slot."""
    planning_date, planning_time = slot.planning_date, slot.planning_time
    start = aware_timestamp(instance.actual_start_at) if instance else None
    end = aware_timestamp(instance.actual_end_at) if instance else None
    if body.start_at is not None:
        start = aware_timestamp(body.start_at)
        planning_date, planning_time = start.date(), start.timetz()
    if body.end_at is not None:
        end = aware_timestamp(body.end_at)
    default_start = datetime.combine(planning_date, planning_time or time.min, tzinfo=UTC)
    window_start = start if start is not None else default_start
    window_end = end if end is not None else window_start
    if window_end < window_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_at muss nach start_at liegen.",
        )
    congregation_id = slot.congregation_id
    if "congregation_id" in body.model_fields_set:
        congregation_id = body.congregation_id
    return ProposedService(
        congregation_id=congregation_id,
        planning_date=planning_date,
        planning_time=planning_time,
        actual_start_at=start if instance else None,
        actual_end_at=end if instance else None,
    )


async def _revalidate_dependent_change(
    session: DbSession,
    *,
    assignments_repo: SqlServiceAssignmentRepository,
    slot: PlanningSlot,
    proposed: ProposedService,
    confirm_warnings: bool,
) -> None:
    """Re-check responsible ministers on the new schedule; leaders are locked in id order."""
    assignments = [
        a for a in await assignments_repo.list_by_planning_slot(slot.id) if a.leader_id is not None
    ]
    leader_ids = sorted({a.leader_id for a in assignments}, key=str)
    for leader_id in leader_ids:
        await ensure_leader_in_district(session, slot.district_id, leader_id)
    for leader_id in leader_ids:
        await acquire_advisory_xact_lock(session, leader_id)
    conflicts: list = []
    for assignment in assignments:
        conflicts += await check_service_assignment_conflicts(
            session,
            event_id=slot.id,
            leader_id=assignment.leader_id,
            exclude_assignment_id=assignment.id,
            proposed=proposed,
        )
    raise_for_conflicts(conflicts, confirm_warnings=confirm_warnings)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    inst_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> EventResponse:
    """Fetch an authoritative event snapshot for conditional writes in detail dialogs."""
    slot = await slot_repo.get(event_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Ereignis nicht gefunden")
    require_role_in_district(auth, Role.VIEWER, slot.district_id)
    instance = await inst_repo.get_by_planning_slot(event_id)
    responsible = await _load_responsible(assignments_repo, leaders_repo, [slot])
    return _slot_to_event(slot, instance, responsible.get(slot.id))


def _changes_service_dependencies(
    slot: PlanningSlot, instance: EventInstance | None, body: EventUpdate
) -> bool:
    """Only effective schedule/location changes require assignment revalidation.

    Category migration with existing assignments needs a separate explicit
    workflow and is deliberately outside this dependency trigger.
    """
    fields = body.model_fields_set
    if "congregation_id" in fields and body.congregation_id != slot.congregation_id:
        return True
    current_start = aware_timestamp(instance.actual_start_at) if instance else _slot_start_at(slot)
    if "start_at" in fields and body.start_at is not None and aware_timestamp(body.start_at) != current_start:
        return True
    return (
        "end_at" in fields
        and body.end_at is not None
        and instance is not None
        and aware_timestamp(body.end_at) != aware_timestamp(instance.actual_end_at)
    )


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    inst_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> EventResponse:
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match ist erforderlich.")
    slot = await slot_repo.get_for_update(event_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ereignis nicht gefunden")

    require_role_in_district(auth, Role.PLANNER, slot.district_id)
    instance = await inst_repo.get_by_planning_slot(event_id, for_update=True)
    if if_match != slot_revision(slot, instance):
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Ereignis wurde zwischenzeitlich geändert. Bitte Daten neu laden.",
        )
    if slot.was_released and "approval_status" in body.model_fields_set and body.approval_status != EventApprovalStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Eine Freigabe kann nicht zurückgenommen werden.")
    if slot.was_released and slot.status == PlanningSlotStatus.CANCELLED and body.status == PlanningSlotStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Eine veröffentlichte Absage kann nicht zurückgenommen werden.")
    proposed = _proposed_service(slot, instance, body)
    dependent = _changes_service_dependencies(slot, instance, body)

    if dependent:
        await _revalidate_dependent_change(
            session,
            assignments_repo=assignments_repo,
            slot=slot,
            proposed=proposed,
            confirm_warnings=body.confirm_warnings,
        )

    if "congregation_id" in body.model_fields_set:
        if body.congregation_id is None:
            slot.congregation_id = None
        elif body.congregation_id != slot.congregation_id:
            congregation = await cong_repo.get(body.congregation_id)
            if congregation is None or congregation.district_id != slot.district_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Gemeinde gehört nicht zum Bezirk des Ereignisses.",
                )
            slot.congregation_id = body.congregation_id

    if "applicability" in body.model_fields_set:
        congregations = await cong_repo.list_by_district(slot.district_id)
        try:
            slot.distribute_to(body.applicability or [], {c.id for c in congregations})
        except InvalidApplicabilityError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    elif slot.congregation_id is not None:
        # A congregation-level event is never distributed further (UC-04).
        slot.applicability = []

    if body.status is not None:
        slot.status = body.status
    if "approval_status" in body.model_fields_set:
        slot.approval_status = body.approval_status
    if "category" in body.model_fields_set:
        slot.category = body.category
    if body.title is not None:
        slot.title = body.title
        if instance is not None:
            instance.title = body.title

    instance_changed = instance is not None and (body.title is not None or body.status is not None)
    if "description" in body.model_fields_set:
        if instance is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Beschreibung kann nur bei einem Ereignis mit EventInstance geändert werden.",
            )
        instance.description = body.description
        instance_changed = True

    if body.start_at is not None or body.end_at is not None:
        new_start = aware_timestamp(
            body.start_at or (instance.actual_start_at if instance else _slot_start_at(slot))
        )
        new_end = aware_timestamp(body.end_at or (instance.actual_end_at if instance else new_start))
        if new_end < new_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_at muss nach start_at liegen.",
            )
        slot.planning_date = new_start.date()
        slot.planning_time = new_start.timetz()
        if instance is not None:
            instance.actual_start_at = new_start
            instance.actual_end_at = new_end
            instance_changed = True

    if instance_changed and instance is not None:
        instance.updated_at = datetime.now(UTC)
        instance.last_internal_modified_at = instance.updated_at
        instance.sync_state = internal_state(instance.sync_state)
        await inst_repo.save(instance)

    # A new revision is required even for multiple writes inside the same clock tick.
    slot.updated_at = max(datetime.now(UTC), aware_timestamp(slot.updated_at) + timedelta(microseconds=1))
    try:
        await slot_repo.save(slot, require_existing=True)
    except (ReleasedEventError, DeletedPlanningSlotError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    responsible = await _load_responsible(assignments_repo, leaders_repo, [slot])
    return _slot_to_event(slot, instance, responsible.get(slot.id))


@router.post("/{event_id}/change-impact", response_model=EventChangeImpact)
async def preview_event_change(
    event_id: uuid.UUID,
    body: EventChangeImpactRequest,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    inst_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
) -> EventChangeImpact:
    """Read-only impact using row locks for a consistent multi-entity snapshot.

    Locks serialize concurrent previews until this request transaction ends.
    The later PATCH runs in a separate transaction and revalidates independently.
    """
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match ist erforderlich.")
    slot = await slot_repo.get_for_update(event_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ereignis nicht gefunden")
    require_role_in_district(auth, Role.PLANNER, slot.district_id)
    instance = await inst_repo.get_by_planning_slot(event_id, for_update=True)
    if if_match != slot_revision(slot, instance):
        raise HTTPException(status_code=412, detail="Ereignis wurde zwischenzeitlich geändert.")
    proposed = _proposed_service(slot, instance, body)
    items: list[EventChangeImpactItem] = []
    for assignment in await assignments_repo.list_by_planning_slot(event_id):
        if assignment.leader_id is None:
            continue
        conflicts = await check_service_assignment_conflicts(
            session,
            event_id=event_id,
            leader_id=assignment.leader_id,
            exclude_assignment_id=assignment.id,
            proposed=proposed,
        )
        if conflicts:
            items.append(
                EventChangeImpactItem(
                    assignment_id=assignment.id,
                    leader_id=assignment.leader_id,
                    conflicts=conflict_items(conflicts),
                )
            )
    severities = {conflict.severity.value for item in items for conflict in item.conflicts}
    return EventChangeImpact(
        blocked="BLOCK" in severities,
        requires_confirmation="WARN" in severities,
        items=items,
    )


@router.patch("/{event_id}/inline", response_model=EventResponse)
async def inline_update_event(
    event_id: uuid.UUID,
    body: EventInlineUpdate,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    inst_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
    assignments_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
    leaders_repo: SqlLeaderRepository = Depends(get_leader_repository),
) -> EventResponse:
    """Safe scalar-only editing. Workflow and duty changes need their own adapters."""
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match ist erforderlich.")
    fields = body.model_fields_set
    if not fields or (
        "title" in fields and body.title is None
    ):
        raise HTTPException(status_code=422, detail="Dieses Feld kann nicht inline bearbeitet werden.")
    slot = await slot_repo.get_for_update(event_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Ereignis nicht gefunden")
    require_role_in_district(auth, Role.PLANNER, slot.district_id)
    if slot.status != PlanningSlotStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Abgesagte Termine können nicht inline bearbeitet werden.")
    instance = await inst_repo.get_by_planning_slot(event_id)
    if instance is not None and instance.source == EventSource.EXTERNAL:
        raise HTTPException(status_code=403, detail="Extern verwaltete Ereignisse sind nicht inline bearbeitbar.")
    return await update_event(
        event_id, EventUpdate.model_validate(body.model_dump(exclude_unset=True)), auth, session, slot_repo=slot_repo, cong_repo=cong_repo,
        inst_repo=inst_repo, assignments_repo=assignments_repo,
        leaders_repo=leaders_repo, if_match=if_match,
    )


def _provider_write_error(exc: CalendarConnectorError, detail: str) -> HTTPException:
    """409 for writes the provider model cannot express, 502 for provider failures."""
    if isinstance(exc, OccurrenceWriteBackError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


@router.post("/{event_id}/resolve-deviation", response_model=EventResponse)
async def resolve_event_deviation(
    event_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    instance_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
) -> EventResponse:
    slot = await slot_repo.get(event_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ereignis nicht gefunden")
    require_role_in_district(auth, Role.PLANNER, slot.district_id)
    instance = await instance_repo.get_by_planning_slot(event_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EventInstance nicht gefunden")
    resolved = await DeviationService(slot_repo, instance_repo).resolve_deviation(instance.id)
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Keine aktive Abweichung zum Auflösen vorhanden.",
        )
    current = await instance_repo.get(instance.id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EventInstance nicht gefunden")
    try:
        if current.calendar_integration_id is not None:
            await push_deviation_resolution(current, session)
    except UnsupportedCalendarTypeError as exc:
        current.deviation_flag = True
        current.sync_state = SyncState.DIRTY_INTERNAL
        await instance_repo.save(current)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CalendarConnectorError as exc:
        current.deviation_flag = True
        current.sync_state = SyncState.DIRTY_INTERNAL
        await instance_repo.save(current)
        raise _provider_write_error(
            exc, "Abweichung lokal aufgelöst, Provider-Aktualisierung fehlgeschlagen."
        ) from exc
    return _slot_to_event(slot, await instance_repo.get(instance.id))


@router.post("/{event_id}/resolve-conflict", response_model=EventResponse)
async def resolve_event_conflict(
    event_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    instance_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
) -> EventResponse:
    """Resolve a sync CONFLICT in favour of the internal planning data.

    The internal payload is pushed to writable provider links. The link
    baselines are advanced so the echoed provider state is suppressed on the
    next inbound sync run instead of re-entering CONFLICT.
    """
    slot = await slot_repo.get(event_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ereignis nicht gefunden")
    require_role_in_district(auth, Role.PLANNER, slot.district_id)
    instance = await instance_repo.get_by_planning_slot(event_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EventInstance nicht gefunden")
    if instance.sync_state != SyncState.CONFLICT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kein aktiver Konflikt zum Auflösen vorhanden.",
        )
    instance.sync_state = resolve_conflict(instance.sync_state)
    instance.updated_at = datetime.now(UTC)
    instance.last_internal_modified_at = instance.updated_at
    await instance_repo.save(instance)
    try:
        if instance.calendar_integration_id is not None:
            await push_conflict_resolution(instance, session)
    except UnsupportedCalendarTypeError as exc:
        instance.sync_state = SyncState.CONFLICT
        await instance_repo.save(instance)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CalendarConnectorError as exc:
        instance.sync_state = SyncState.CONFLICT
        await instance_repo.save(instance)
        raise _provider_write_error(
            exc, "Konflikt lokal aufgelöst, Provider-Aktualisierung fehlgeschlagen."
        ) from exc
    return _slot_to_event(slot, await instance_repo.get(instance.id))


@router.post("/bulk-approval-status", response_model=BulkApprovalStatusResponse)
async def bulk_update_approval_status(
    body: BulkApprovalStatusRequest,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    district_id: uuid.UUID | None = Query(None),
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
) -> BulkApprovalStatusResponse:
    if district_id is None and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="district_id ist erforderlich, außer für Superadmin.",
        )
    if body.congregation_id is None:
        # District-wide publication remains restricted to district planners.
        if district_id is not None:
            require_role_in_district(auth, Role.PLANNER, district_id)
    else:
        # Resolve and authorize the *requested* congregation before reading any
        # planning slots. A membership for another congregation is insufficient.
        if district_id is None:
            raise HTTPException(status_code=400, detail="district_id ist erforderlich.")
        congregation = await cong_repo.get(body.congregation_id)
        if congregation is None or congregation.district_id != district_id:
            raise HTTPException(status_code=403, detail="Gemeinde gehört nicht zum Bezirk.")
        if not has_role_in_district(auth, Role.PLANNER, district_id):
            require_role_in_district(
                auth,
                Role.CONGREGATION_ADMIN,
                district_id,
                congregation_ids_in_district={body.congregation_id},
            )

    first_local_day = date(body.year, body.month, 1)
    last_local_day = date(body.year, body.month, calendar.monthrange(body.year, body.month)[1])
    # Slots use UTC date/time, whereas monthly approval is a local calendar operation.
    # A 00:30 Berlin event on Dec 1 may occupy Nov 30 in the slot table.
    all_slots = await slot_repo.list_for_date_range(
        district_id=district_id or uuid.UUID(int=0),
        from_date=first_local_day - timedelta(days=1),
        to_date=last_local_day,
    )
    berlin = ZoneInfo("Europe/Berlin")
    all_slots = [
        slot for slot in all_slots
        if first_local_day <= _slot_start_at(slot).astimezone(berlin).date() <= last_local_day
        and (body.congregation_id is None or slot.congregation_id == body.congregation_id)
    ]

    if body.approval_status == EventApprovalStatus.PLANNED and any(slot.was_released for slot in all_slots):
        raise HTTPException(status_code=409, detail="Bereits freigegebene Ereignisse können nicht zurückgestuft werden.")

    now_dt = datetime.now(UTC)
    for slot in all_slots:
        slot.approval_status = body.approval_status
        slot.updated_at = now_dt
        try:
            await slot_repo.save(slot, require_existing=True)
        except (ReleasedEventError, DeletedPlanningSlotError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if (
        district_id is not None
        and body.congregation_id is None
        and body.approval_status == EventApprovalStatus.CONFIRMED
        and all_slots
    ):
        publish_after_commit(session, plan_finalized(district_id, year=body.year, month=body.month))

    return BulkApprovalStatusResponse(updated_count=len(all_slots))
