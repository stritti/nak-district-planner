"""Router for the /api/v1/events endpoints.

Exposes PlanningSlot + EventInstance under the events API using typed
Pydantic schemas. Validation of enum values, UUIDs and datetimes is done
by Pydantic — the handlers only contain business logic.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.repositories import (
    SqlCongregationRepository,
    SqlEventInstanceRepository,
    SqlPlanningSlotRepository,
)
from app.domain.models.event_instance import (
    EventInstance,
    EventSource,
    EventVisibility,
)
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
)
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/events", tags=["events"])


# ── Pydantic schemas ─────────────────────────────────────────────────────────


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
    source: EventSource
    status: PlanningSlotStatus
    approval_status: EventApprovalStatus | None
    visibility: EventVisibility
    applicability: list[str]
    invitation_source_congregation_id: uuid.UUID | None = None
    invitation_source_event_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    limit: int
    offset: int


class EventUpdate(BaseModel):
    """Patch fields for an event. All fields optional; unknown-to-domain
    fields are not accepted (no silent drops).
    """

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    congregation_id: uuid.UUID | None = None
    status: PlanningSlotStatus | None = None
    approval_status: EventApprovalStatus | None = None
    category: str | None = Field(None, max_length=255)


class BulkApprovalStatusRequest(BaseModel):
    year: int = Field(ge=1900, le=9999)
    month: int = Field(ge=1, le=12)
    approval_status: EventApprovalStatus
    congregation_id: uuid.UUID | None = None


class BulkApprovalStatusResponse(BaseModel):
    updated_count: int


# ── Helpers ──────────────────────────────────────────────────────────────────


def _slot_start_at(slot: PlanningSlot) -> datetime:
    return datetime.combine(slot.planning_date, slot.planning_time or time.min, tzinfo=UTC)


def _slot_to_event(slot: PlanningSlot, instance: EventInstance | None) -> EventResponse:
    """Convert a PlanningSlot (+ optional EventInstance) to an EventResponse."""
    return EventResponse(
        id=slot.id,
        title=instance.title if instance else (slot.title or ""),
        description=instance.description if instance else None,
        start_at=instance.actual_start_at if instance else _slot_start_at(slot),
        end_at=instance.actual_end_at if instance else _slot_start_at(slot),
        district_id=slot.district_id,
        congregation_id=slot.congregation_id,
        category=slot.category,
        source=instance.source if instance else EventSource.INTERNAL,
        status=slot.status,
        approval_status=slot.approval_status,
        visibility=instance.visibility if instance else EventVisibility.PUBLIC,
        applicability=list(slot.applicability or []),
        invitation_source_congregation_id=slot.invitation_source_congregation_id,
        invitation_source_event_id=slot.invitation_source_event_id,
        created_at=slot.created_at,
        updated_at=slot.updated_at,
    )


async def _load_instances(
    slot_ids: list[uuid.UUID], session
) -> dict[uuid.UUID, EventInstance]:
    """Batch load EventInstances for the given slot IDs."""
    inst_repo = SqlEventInstanceRepository(session)
    instances = await inst_repo.list_by_planning_slots(slot_ids)
    return {inst.planning_slot_id: inst for inst in instances}


# ── Endpoints ─────────────────────────────────────────────────────────────────


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
    from_dt: date | None = Query(None),
    to_dt: date | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> EventListResponse:
    """List events (PlanningSlots) for a district with optional filters."""
    if district_id is None and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="district_id ist erforderlich, außer für Superadmin.",
        )
    if district_id is not None:
        require_role_in_district(auth, Role.VIEWER, district_id)

    slot_repo = SqlPlanningSlotRepository(session)
    now = datetime.now(UTC).date()
    from_date = from_dt or now - timedelta(days=365)
    to_date = to_dt or now + timedelta(days=365 * 2)

    all_slots = await slot_repo.list_for_date_range(
        district_id=district_id or uuid.UUID(int=0),
        from_date=from_date,
        to_date=to_date,
    )

    if only_district_level:
        all_slots = [s for s in all_slots if s.congregation_id is None]
    elif congregation_id is not None:
        # Congregation view: own slots + district-level slots distributed via
        # applicability ("all" sentinel or explicit congregation ID).
        all_slots = [
            s
            for s in all_slots
            if s.congregation_id == congregation_id
            or (
                s.congregation_id is None
                and s.status == PlanningSlotStatus.ACTIVE
                and ("all" in s.applicability or str(congregation_id) in s.applicability)
            )
        ]

    if group_id is not None:
        cong_repo = SqlCongregationRepository(session)
        congregations = await cong_repo.list_by_district(district_id or uuid.UUID(int=0))
        group_congregation_ids = {c.id for c in congregations if c.group_id == group_id}
        all_slots = [s for s in all_slots if s.congregation_id in group_congregation_ids]

    if status_filter is not None:
        all_slots = [s for s in all_slots if s.status == status_filter]

    if approval_status is not None:
        all_slots = [s for s in all_slots if s.approval_status == approval_status]

    total = len(all_slots)
    page = all_slots[offset : offset + limit]
    instances = await _load_instances([s.id for s in page], session)

    return EventListResponse(
        items=[_slot_to_event(s, instances.get(s.id)) for s in page],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> EventResponse:
    """Update a PlanningSlot (and its EventInstance when present)."""
    slot_repo = SqlPlanningSlotRepository(session)
    slot = await slot_repo.get(event_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ereignis nicht gefunden"
        )

    require_role_in_district(auth, Role.PLANNER, slot.district_id)

    inst_repo = SqlEventInstanceRepository(session)
    instance = await inst_repo.get_by_planning_slot(event_id)

    if body.congregation_id is not None and body.congregation_id != slot.congregation_id:
        cong_repo = SqlCongregationRepository(session)
        congregation = await cong_repo.get(body.congregation_id)
        if congregation is None or congregation.district_id != slot.district_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gemeinde gehört nicht zum Bezirk des Ereignisses.",
            )
        slot.congregation_id = body.congregation_id

    if body.status is not None:
        slot.status = body.status
    if body.approval_status is not None:
        slot.approval_status = body.approval_status
    if body.category is not None:
        slot.category = body.category
    if body.title is not None:
        slot.title = body.title

    if body.start_at is not None or body.end_at is not None:
        new_start = body.start_at or (
            instance.actual_start_at if instance else _slot_start_at(slot)
        )
        new_end = body.end_at or (instance.actual_end_at if instance else new_start)
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
            instance.updated_at = datetime.now(UTC)
            await inst_repo.save(instance)

    slot.updated_at = datetime.now(UTC)
    await slot_repo.save(slot)

    return _slot_to_event(slot, instance)


@router.post("/bulk-approval-status", response_model=BulkApprovalStatusResponse)
async def bulk_update_approval_status(
    body: BulkApprovalStatusRequest,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    district_id: uuid.UUID | None = Query(None),
) -> BulkApprovalStatusResponse:
    """Bulk-update approval_status for planning slots in a given month."""
    if district_id is None and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="district_id ist erforderlich, außer für Superadmin.",
        )
    if district_id is not None:
        require_role_in_district(auth, Role.PLANNER, district_id)

    slot_repo = SqlPlanningSlotRepository(session)
    from_date = date(body.year, body.month, 1)
    if body.month == 12:
        to_date = date(body.year + 1, 1, 1) - timedelta(days=1)
    else:
        to_date = date(body.year, body.month + 1, 1) - timedelta(days=1)

    all_slots = await slot_repo.list_for_date_range(
        district_id=district_id or uuid.UUID(int=0),
        from_date=from_date,
        to_date=to_date,
    )

    if body.congregation_id is not None:
        all_slots = [s for s in all_slots if s.congregation_id == body.congregation_id]

    now_dt = datetime.now(UTC)
    for slot in all_slots:
        slot.approval_status = body.approval_status
        slot.updated_at = now_dt
        await slot_repo.save(slot)

    return BulkApprovalStatusResponse(updated_count=len(all_slots))
