"""app/adapters/api/routers/export.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from icalendar import Calendar
from icalendar import Event as ICalEvent
from sqlalchemy import select

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_event_instance_repository,
    get_export_token_repository,
    get_leader_repository,
    get_planning_slot_repository,
    get_service_assignment_repository,
)
from app.adapters.api.schemas.export_token import ExportTokenCreate, ExportTokenResponse
from app.adapters.api.tenant_references import (
    ensure_congregation_in_district,
    ensure_leader_in_district,
)
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.export_token import SqlExportTokenRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.domain.models.event_instance import EventInstance, EventVisibility
from app.domain.models.export_token import ExportToken, TokenType
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
)
from app.domain.models.role import Role
from app.domain.models.service_assignment import ServiceAssignment

router = APIRouter(prefix="/api/v1")


# ── Token management (DISTRICT_ADMIN, OIDC Bearer) ───────────────────────────


@router.post(
    "/export-tokens",
    response_model=ExportTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_export_token(
    auth: CurrentUserWithMemberships,
    body: ExportTokenCreate,
    session: DbSession,
    repo: SqlExportTokenRepository = Depends(get_export_token_repository),
) -> ExportTokenResponse:
    require_role_in_district(auth, Role.DISTRICT_ADMIN, body.district_id)
    await ensure_congregation_in_district(session, body.district_id, body.congregation_id)
    await ensure_leader_in_district(session, body.district_id, body.leader_id)

    token = ExportToken.create(
        label=body.label,
        token_type=body.token_type,
        district_id=body.district_id,
        congregation_id=body.congregation_id,
        leader_id=body.leader_id,
    )
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
    repo: SqlExportTokenRepository = Depends(get_export_token_repository),
) -> list[ExportTokenResponse]:
    if district_id is None and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="district_id ist erforderlich, außer für Superadmin.",
        )

    if district_id is not None:
        require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)

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
    repo: SqlExportTokenRepository = Depends(get_export_token_repository),
) -> None:
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


def _slot_key(assignment: ServiceAssignment) -> uuid.UUID:
    """Canonical slot key; ``event_id`` is the legacy compatibility fallback."""
    return assignment.planning_slot_id or assignment.event_id


# RFC 5545 INTEGER is 32-bit; Unix-epoch seconds would overflow in 2038.
_SEQUENCE_EPOCH = datetime(2020, 1, 1, tzinfo=UTC)


def _sequence(last_modified: datetime) -> int:
    """Return the iCal SEQUENCE: seconds since 2020 of the last revision (monotonic)."""
    return int((last_modified - _SEQUENCE_EPOCH).total_seconds())


@router.get("/export/{token_str}/calendar.ics", include_in_schema=False)
async def export_calendar_ics(
    token_str: str,
    session: DbSession,
    approval_status: Literal["confirmed_only", "include_planned"] | None = Query(None),
    token_repo: SqlExportTokenRepository = Depends(get_export_token_repository),
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    instance_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
    sa_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
    leader_repo_dep: SqlLeaderRepository = Depends(get_leader_repository),
) -> Response:
    from sqlalchemy import text

    await session.execute(
        text("SELECT set_config('app.current_export_token', :val, true)"),
        {"val": token_str},
    )
    export_token = await token_repo.get_by_token(token_str)
    if not export_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token ungültig")

    # RLS public export policies use app.current_export_token for scoped reads.

    # Load PlanningSlots for a wide window (past 1 year, future 2 years)
    now = datetime.now(UTC).date()
    from_date = now - timedelta(days=365)
    to_date = now + timedelta(days=365 * 2)
    all_slots = await slot_repo.list_for_date_range(
        district_id=export_token.district_id,
        from_date=from_date,
        to_date=to_date,
    )

    # Congregation feed: own slots plus district slots released to it (UC-04).
    # CANCELLED slots stay in and are emitted as STATUS:CANCELLED so subscribed
    # calendars remove previously synced events.
    if congregation_id := export_token.congregation_id:
        all_slots = [
            s
            for s in all_slots
            if s.congregation_id == congregation_id or s.is_distributed_to(congregation_id)
        ]

    # Load all EventInstances for these slots
    slot_ids = [s.id for s in all_slots]
    instances: list[EventInstance] = []
    if slot_ids:
        instances = await instance_repo.list_by_planning_slots(slot_ids)
    instance_by_slot: dict[uuid.UUID, EventInstance] = {
        inst.planning_slot_id: inst for inst in instances
    }

    # Personal and INTERNAL feeds are internal: they show leader names and
    # INTERNAL events. PUBLIC feeds anonymize names (like the leaders RLS policy,
    # they never load leader rows) and omit events with INTERNAL visibility.
    show_names = bool(export_token.leader_id) or export_token.token_type == TokenType.INTERNAL
    if not show_names:
        all_slots = [
            s
            for s in all_slots
            if (inst := instance_by_slot.get(s.id)) is None
            or inst.visibility != EventVisibility.INTERNAL
        ]

    # PUBLIC tokens always export CONFIRMED slots only; the query parameter can
    # only narrow INTERNAL feeds (ExportToken.confirmed_only).
    if export_token.confirmed_only(approval_status):
        all_slots = [s for s in all_slots if s.is_confirmed]

    # Load assignments in one batch query (keyed by planning_slot_id via event_id)
    assignments = await sa_repo.list_by_planning_slots(slot_ids)

    # Personal leader feed: only this leader's assignments and their slots
    if export_token.leader_id:
        assignments = [a for a in assignments if a.leader_id == export_token.leader_id]
        leader_slot_ids = {_slot_key(a) for a in assignments}
        all_slots = [s for s in all_slots if s.id in leader_slot_ids]

    # Batch-load leaders so leader_id-only assignments can be resolved to a display name
    if export_token.district_id and show_names:
        leader_repo = leader_repo_dep
        leaders = await leader_repo.list_by_district(export_token.district_id)
        leaders_by_id = {ldr.id: ldr for ldr in leaders}
    else:
        leaders_by_id = {}

    # Build assignment_map: prefer non-empty leader_name; fall back to leader_id lookup
    assignment_map: dict[uuid.UUID, str | None] = {}
    # Leader renames change the exported COMMENT without touching the slot
    leader_revision: dict[uuid.UUID, datetime] = {}
    for a in assignments:
        display_name: str | None = None
        if a.leader_name:
            display_name = a.leader_name
        elif a.leader_id and a.leader_id in leaders_by_id:
            ldr = leaders_by_id[a.leader_id]
            rank_prefix = f"{ldr.rank.value} " if ldr.rank else ""
            display_name = f"{rank_prefix}{ldr.name}"
            key = _slot_key(a)
            leader_revision[key] = max(ldr.updated_at, leader_revision.get(key, ldr.updated_at))
        elif a.leader_id and not show_names:
            display_name = "[Name anonymisiert]"

        # For each slot keep the best name (non-None wins over None)
        slot_key = _slot_key(a)
        existing = assignment_map.get(slot_key)
        if slot_key not in assignment_map or (display_name is not None and existing is None):
            assignment_map[slot_key] = display_name

    # Load congregation names for LOCATION field
    cong_result = await session.execute(
        select(CongregationORM).where(CongregationORM.district_id == export_token.district_id)
    )
    congregations = list(cong_result.scalars())
    cong_map: dict[uuid.UUID, str] = {c.id: c.name for c in congregations}
    cong_revision: dict[uuid.UUID, datetime] = {c.id: c.updated_at for c in congregations}

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
        else:
            # Synthesize from PlanningSlot when no EventInstance exists
            vt = _synthesize_datetime(slot)
            vevent.add("dtstart", vt)
            vevent.add("dtend", vt + _SYNTHESIZED_EVENT_DURATION)

        # Change metadata from the last revision of everything rendered into the
        # VEVENT (slot, instance, leader name, congregation name)
        revisions = [slot.updated_at]
        if instance:
            revisions.append(instance.updated_at)
        if slot.id in leader_revision:
            revisions.append(leader_revision[slot.id])
        if slot.congregation_id in cong_revision:
            revisions.append(cong_revision[slot.congregation_id])
        location_id = slot.invitation_source_congregation_id or slot.congregation_id
        if location_id in cong_revision:
            revisions.append(cong_revision[location_id])
        last_modified = max(revisions)
        vevent.add("dtstamp", last_modified)
        vevent.add("last-modified", last_modified)
        vevent.add("sequence", _sequence(last_modified))

        if slot.status == PlanningSlotStatus.CANCELLED:
            vevent.add("status", "CANCELLED")
        elif slot.approval_status == EventApprovalStatus.PLANNED:
            # Mark PLANNED events as tentative in the calendar
            vevent.add("status", "TENTATIVE")
            vevent.add("x-nak-approval-status", "PLANNED")

        # An invitation copy takes place in the host congregation.
        if location_id in cong_map:
            vevent.add("location", cong_map[location_id])

        if slot.category:
            vevent.add("categories", slot.category)

        if instance and instance.description:
            vevent.add("description", instance.description)

        leader = assignment_map.get(slot.id)
        if leader:
            name = leader if show_names else "[Name anonymisiert]"
            vevent.add("comment", f"Dienstleiter: {name}")

        cal.add_component(vevent)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="calendar.ics"'},
    )
