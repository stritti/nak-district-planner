"""app/adapters/api/routers/export.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from icalendar import Calendar
from icalendar import Event as ICalEvent
from sqlalchemy import select

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.api.schemas.export_token import ExportTokenCreate, ExportTokenResponse
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.repositories import (
    SqlEventInstanceRepository,
    SqlPlanningSlotRepository,
)
from app.adapters.db.repositories.export_token import SqlExportTokenRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.domain.models.event_instance import EventInstance
from app.domain.models.export_token import ExportToken, TokenType
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlot
from app.domain.models.role import Role

router = APIRouter()


# ── Token management (requires API key) ──────────────────────────────────────


@router.post(
    "/export-tokens",
    response_model=ExportTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_export_token(
    auth: CurrentUserWithMemberships, body: ExportTokenCreate, session: DbSession
) -> ExportTokenResponse:
    require_role_in_district(auth, Role.DISTRICT_ADMIN, body.district_id)

    token = ExportToken.create(
        label=body.label,
        token_type=body.token_type,
        district_id=body.district_id,
        congregation_id=body.congregation_id,
        leader_id=body.leader_id,
    )
    repo = SqlExportTokenRepository(session)
    await repo.save(token)
    return _token_response(token)


@router.get(
    "/export-tokens",
    response_model=list[ExportTokenResponse],
)
async def list_export_tokens(
    auth: CurrentUserWithMemberships,
    session: DbSession,
    district_id: uuid.UUID | None = None,
) -> list[ExportTokenResponse]:
    if district_id is None and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="district_id ist erforderlich, außer für Superadmin.",
        )

    if district_id is not None:
        require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)

    repo = SqlExportTokenRepository(session)
    tokens = await repo.list_by_district(district_id) if district_id else await repo.list_all()
    return [_token_response(t) for t in tokens]


@router.delete(
    "/export-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_export_token(
    auth: CurrentUserWithMemberships,
    token_id: uuid.UUID,
    session: DbSession,
) -> None:
    repo = SqlExportTokenRepository(session)
    token = await repo.get(token_id)
    if token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token nicht gefunden")

    require_role_in_district(auth, Role.DISTRICT_ADMIN, token.district_id)

    await repo.delete(token_id)


def _token_response(token: ExportToken) -> ExportTokenResponse:
    return ExportTokenResponse(
        id=token.id,
        token=token.token,
        label=token.label,
        token_type=token.token_type,
        district_id=token.district_id,
        congregation_id=token.congregation_id,
        leader_id=token.leader_id,
        created_at=token.created_at,
    )


# ── Public ICS export (no auth) ──────────────────────────────────────────────

_EXPORT_WINDOW_YEARS = 3
# Default duration for events that only have a PlanningSlot (no EventInstance yet).
_SYNTHESIZED_EVENT_DURATION = timedelta(hours=2)


def _synthesize_datetime(slot: PlanningSlot, default_time: time = time(0, 0, 0)) -> datetime:
    """Synthesize a datetime from PlanningSlot date+time, with UTC timezone."""
    dt = datetime.combine(slot.planning_date, slot.planning_time or default_time, tzinfo=UTC)
    return dt


@router.get("/export/{token_str}/calendar.ics", include_in_schema=False)
async def export_calendar_ics(
    token_str: str,
    session: DbSession,
    approval_status: Literal["confirmed_only", "include_planned"] | None = Query(None),
) -> Response:
    token_repo = SqlExportTokenRepository(session)
    export_token = await token_repo.get_by_token(token_str)
    if not export_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token ungültig")

    slot_repo = SqlPlanningSlotRepository(session)
    instance_repo = SqlEventInstanceRepository(session)

    # Load PlanningSlots for a wide window (past 1 year, future 2 years)
    now = datetime.now(UTC).date()
    from_date = now - timedelta(days=365)
    to_date = now + timedelta(days=365 * 2)
    all_slots = await slot_repo.list_for_date_range(
        district_id=export_token.district_id,
        from_date=from_date,
        to_date=to_date,
    )

    # Narrow by congregation if token is congregation-scoped
    if export_token.congregation_id:
        all_slots = [s for s in all_slots if s.congregation_id == export_token.congregation_id]

    # Load all EventInstances for these slots
    slot_ids = [s.id for s in all_slots]
    instances: list[EventInstance] = []
    if slot_ids:
        instances = await instance_repo.list_by_planning_slots(slot_ids)
    instance_by_slot: dict[uuid.UUID, EventInstance] = {
        inst.planning_slot_id: inst for inst in instances
    }

    # Apply approval_status filter
    if approval_status is None:
        if export_token.token_type == TokenType.PUBLIC and export_token.leader_id is None:
            approval_status = "confirmed_only"
        else:
            approval_status = "include_planned"

    if approval_status == "confirmed_only":
        all_slots = [s for s in all_slots if s.approval_status == EventApprovalStatus.CONFIRMED]
    elif approval_status != "include_planned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger approval_status-Filter: {approval_status}. "
            f"Erlaubte Werte: confirmed_only, include_planned",
        )

    # Load assignments in one batch query (keyed by planning_slot_id via event_id)
    sa_repo = SqlServiceAssignmentRepository(session)
    assignments = await sa_repo.list_by_planning_slots(slot_ids)

    # For leader tokens: keep only assignments for this specific leader
    if export_token.leader_id:
        assignments = [a for a in assignments if a.leader_id == export_token.leader_id]

    # Batch-load leaders so leader_id-only assignments can be resolved to a display name
    if export_token.district_id:
        leader_repo = SqlLeaderRepository(session)
        leaders = await leader_repo.list_by_district(export_token.district_id)
        leaders_by_id = {ldr.id: ldr for ldr in leaders}
    else:
        leaders_by_id = {}

    # Build assignment_map: prefer non-empty leader_name; fall back to leader_id lookup
    assignment_map: dict[uuid.UUID, str | None] = {}
    for a in assignments:
        display_name: str | None = None
        if a.leader_name:
            display_name = a.leader_name
        elif a.leader_id and a.leader_id in leaders_by_id:
            ldr = leaders_by_id[a.leader_id]
            rank_prefix = f"{ldr.rank.value} " if ldr.rank else ""
            display_name = f"{rank_prefix}{ldr.name}"

        # For each slot keep the best name (non-None wins over None)
        slot_key = a.event_id  # event_id is now the planning_slot_id
        existing = assignment_map.get(slot_key)
        if slot_key not in assignment_map or (display_name is not None and existing is None):
            assignment_map[slot_key] = display_name

    # Load congregation names for LOCATION field
    cong_result = await session.execute(
        select(CongregationORM).where(CongregationORM.district_id == export_token.district_id)
    )
    cong_map: dict[uuid.UUID, str] = {c.id: c.name for c in cong_result.scalars()}

    # Build iCalendar
    cal = Calendar()
    cal.add("prodid", "-//NAK Bezirksplaner//nak-bezirksplaner//DE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", export_token.label)
    cal.add("x-wr-timezone", "Europe/Berlin")

    for slot in all_slots:
        instance = instance_by_slot.get(slot.id)
        # Use stable UID based on PlanningSlot ID (not EventInstance ID)
        vevent = ICalEvent()
        vevent.add("uid", f"{slot.id}@nak-bezirksplaner")

        title = instance.title if instance else (slot.title or "Gottesdienst")
        # Personal leader calendar: include congregation name in summary
        if export_token.leader_id and slot.congregation_id and slot.congregation_id in cong_map:
            vevent.add("summary", f"{title} – {cong_map[slot.congregation_id]}")
        else:
            vevent.add("summary", title)

        if instance:
            vevent.add("dtstart", instance.actual_start_at)
            vevent.add("dtend", instance.actual_end_at)
            vevent.add("dtstamp", instance.created_at)
        else:
            # Synthesize from PlanningSlot when no EventInstance exists
            vt = _synthesize_datetime(slot)
            vevent.add("dtstart", vt)
            vevent.add("dtend", vt + _SYNTHESIZED_EVENT_DURATION)
            vevent.add("dtstamp", slot.created_at)

        # Mark PLANNED events as tentative in the calendar
        if slot.approval_status == EventApprovalStatus.PLANNED:
            vevent.add("status", "TENTATIVE")
            vevent.add("x-nak-approval-status", "PLANNED")

        if slot.congregation_id and slot.congregation_id in cong_map:
            vevent.add("location", cong_map[slot.congregation_id])

        if slot.category:
            vevent.add("categories", slot.category)

        if instance and instance.description:
            vevent.add("description", instance.description)

        leader = assignment_map.get(slot.id)
        if leader:
            # Personal leader token → always show full name (INTERNAL behaviour)
            if export_token.leader_id or export_token.token_type == TokenType.INTERNAL:
                vevent.add("comment", f"Dienstleiter: {leader}")
            else:
                vevent.add("comment", "Dienstleiter: [Name anonymisiert]")

        cal.add_component(vevent)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="calendar.ics"'},
    )
