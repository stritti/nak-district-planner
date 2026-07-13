"""Compatibility router for the legacy /api/v1/events endpoints.

Provides GET/PATCH /api/v1/events and POST /api/v1/events/bulk-approval-status
using the new PlanningSlot + EventInstance model while preserving the old
EventResponse shape for the frontend, which has not yet been migrated.

This is a transitional layer — it should be removed once the frontend no
longer references the events API.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.repositories import (
    SqlEventInstanceRepository,
    SqlPlanningSlotRepository,
)
from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
)
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/events", tags=["events-compat"])


# ── Pydantic schemas (mirroring the removed EventResponse) ──────────────


class EventCompatResponse(BaseModel):
    """Matches the frontend EventResponse interface for backward compatibility."""

    id: str
    title: str
    description: str | None
    start_at: str
    end_at: str
    district_id: str
    congregation_id: str | None
    category: str | None
    source: str
    status: str
    approval_status: str | None
    visibility: str
    audiences: list[str]
    applicability: list[str]
    invitation_source_congregation_id: str | None = None
    invitation_source_event_id: str | None = None
    created_at: str
    updated_at: str


class EventCompatListResponse(BaseModel):
    items: list[EventCompatResponse]
    total: int
    limit: int
    offset: int


class EventCompatUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    district_id: str | None = None
    congregation_id: str | None = None
    status: str | None = None
    approval_status: str | None = None
    category: str | None = None


class BulkApprovalStatusRequest(BaseModel):
    year: int
    month: int
    approval_status: str
    congregation_id: str | None = Field(None, alias="congregation_id")
    congregation_id_str: str | None = None  # Raw string from JSON


class BulkApprovalStatusResponse(BaseModel):
    updated_count: int


# ── Helpers ─────────────────────────────────────────────────────────────


def _slot_to_event(slot: PlanningSlot, instance: EventInstance | None) -> EventCompatResponse:
    """Convert a PlanningSlot (+ optional EventInstance) to EventResponse shape."""
    # Map slot status to old Event status
    status_map = {
        PlanningSlotStatus.ACTIVE: "PUBLISHED",
        PlanningSlotStatus.CANCELLED: "CANCELLED",
    }
    source = instance.source if instance else "INTERNAL"
    return EventCompatResponse(
        id=str(slot.id),
        title=instance.title if instance else (slot.title or ""),
        description=instance.description if instance else None,
        start_at=(
            instance.actual_start_at.isoformat()
            if instance
            else datetime.combine(
                slot.planning_date,
                slot.planning_time or datetime.min.time(),
                tzinfo=UTC,
            ).isoformat()
        ),
        end_at=(
            instance.actual_end_at.isoformat()
            if instance
            else datetime.combine(
                slot.planning_date,
                slot.planning_time or datetime.min.time(),
                tzinfo=UTC,
            ).isoformat()
        ),
        district_id=str(slot.district_id),
        congregation_id=str(slot.congregation_id) if slot.congregation_id else None,
        category=slot.category,
        source=str(source.value) if hasattr(source, "value") else str(source),
        status=status_map.get(slot.status, "PUBLISHED"),
        approval_status=slot.approval_status.value if slot.approval_status else None,
        visibility=str(instance.visibility.value) if instance and instance.visibility else "PUBLIC",
        audiences=list(slot.audiences) if hasattr(slot, "audiences") and slot.audiences else [],
        applicability=list(slot.applicability or []),
        invitation_source_congregation_id=(
            str(slot.invitation_source_congregation_id)
            if slot.invitation_source_congregation_id
            else None
        ),
        invitation_source_event_id=(
            str(slot.invitation_source_event_id) if slot.invitation_source_event_id else None
        ),
        created_at=slot.created_at.isoformat()
        if slot.created_at
        else datetime.now(UTC).isoformat(),
        updated_at=slot.updated_at.isoformat()
        if slot.updated_at
        else datetime.now(UTC).isoformat(),
    )


async def _load_instances(slot_ids: list[uuid.UUID], session) -> dict[uuid.UUID, EventInstance]:
    """Batch load EventInstances for the given slot IDs."""
    inst_repo = SqlEventInstanceRepository(session)
    instances = await inst_repo.list_by_planning_slots(slot_ids)
    return {inst.planning_slot_id: inst for inst in instances}


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("", response_model=EventCompatListResponse)
async def compat_list_events(
    auth: CurrentUserWithMemberships,
    session: DbSession,
    district_id: uuid.UUID | None = Query(None),
    congregation_id: uuid.UUID | None = Query(None),
    approval_status: str | None = Query(None),
    from_dt: str | None = Query(None),
    to_dt: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> EventCompatListResponse:
    """List events (PlanningSlots) for a district with optional filters."""
    if district_id is None and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="district_id ist erforderlich, außer für Superadmin.",
        )
    if district_id is not None:
        require_role_in_district(auth, Role.VIEWER, district_id)

    slot_repo = SqlPlanningSlotRepository(session)

    # Parse date range (default: past year to future 2 years)
    now = datetime.now(UTC).date()
    from_date = date.fromisoformat(from_dt) if from_dt else now - timedelta(days=365)
    to_date = date.fromisoformat(to_dt) if to_dt else now + timedelta(days=365 * 2)

    all_slots = await slot_repo.list_for_date_range(
        district_id=district_id or uuid.UUID(int=0),
        from_date=from_date,
        to_date=to_date,
    )

    # Apply optional filters
    if congregation_id is not None:
        all_slots = [s for s in all_slots if s.congregation_id == congregation_id]
    if approval_status is not None:
        try:
            status_filter = EventApprovalStatus(approval_status)
            all_slots = [s for s in all_slots if s.approval_status == status_filter]
        except ValueError:
            pass  # Ignore invalid status values

    total = len(all_slots)
    page = all_slots[offset : offset + limit]
    instances = await _load_instances([s.id for s in page], session)

    return EventCompatListResponse(
        items=[_slot_to_event(s, instances.get(s.id)) for s in page],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{event_id}", response_model=EventCompatResponse)
async def compat_update_event(
    event_id: uuid.UUID,
    body: EventCompatUpdate,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> EventCompatResponse:
    """Update a PlanningSlot via the legacy event endpoint."""
    slot_repo = SqlPlanningSlotRepository(session)
    slot = await slot_repo.get(event_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ereignis nicht gefunden")

    require_role_in_district(auth, Role.PLANNER, slot.district_id)

    # Map updates to PlanningSlot fields
    changed = False
    if body.title is not None:
        slot.title = body.title
        changed = True
    if body.status is not None:
        try:
            slot.status = PlanningSlotStatus(
                body.status.lower() if isinstance(body.status, str) else body.status
            )
            changed = True
        except ValueError:
            pass
    if body.approval_status is not None:
        try:
            slot.approval_status = EventApprovalStatus(body.approval_status)
            changed = True
        except ValueError:
            pass
    if body.category is not None:
        slot.category = body.category
        changed = True
    if body.congregation_id is not None:
        slot.congregation_id = uuid.UUID(body.congregation_id)
        changed = True

    if changed:
        slot.updated_at = datetime.now(UTC)
        await slot_repo.save(slot)

    inst_repo = SqlEventInstanceRepository(session)
    instance = await inst_repo.get_by_planning_slot(event_id)

    return _slot_to_event(slot, instance)


@router.post("/bulk-approval-status", response_model=BulkApprovalStatusResponse)
async def compat_bulk_approval_status(
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

    # Apply congregation filter
    congregation_id = body.congregation_id_str or body.congregation_id
    if congregation_id is not None:
        all_slots = [s for s in all_slots if s.congregation_id == uuid.UUID(congregation_id)]

    # Map approval_status string
    try:
        new_status = EventApprovalStatus(body.approval_status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger approval_status: {body.approval_status}",
        )

    now_dt = datetime.now(UTC)
    updated = 0
    for slot in all_slots:
        slot.approval_status = new_status
        slot.updated_at = now_dt
        await slot_repo.save(slot)
        updated += 1

    return BulkApprovalStatusResponse(updated_count=updated)
