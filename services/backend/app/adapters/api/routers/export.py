"""app/adapters/api/routers/export.py: Module."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from icalendar import Calendar
from icalendar import Event as ICalEvent
from sqlalchemy import select

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.auth.permissions import PermissionError, assert_has_role_in_district
from app.adapters.api.schemas.export_token import ExportTokenCreate, ExportTokenResponse
from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.adapters.db.repositories.event import SqlEventRepository
from app.adapters.db.repositories.export_token import SqlExportTokenRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.domain.models.event import EventStatus
from app.domain.models.export_token import ExportToken, TokenType
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
    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, body.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

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
        try:
            assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

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

    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, token.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

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


@router.get("/export/{token_str}/calendar.ics", include_in_schema=False)
async def export_calendar_ics(token_str: str, session: DbSession) -> Response:
    token_repo = SqlExportTokenRepository(session)
    export_token = await token_repo.get_by_token(token_str)
    if not export_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token ungültig")

    event_repo = SqlEventRepository(session)

    if export_token.leader_id:
        # Personal leader calendar: find all events with this leader assigned
        sa_result = await session.execute(
            select(ServiceAssignmentORM).where(
                ServiceAssignmentORM.leader_id == export_token.leader_id
            )
        )
        leader_assignments = {row.event_id: row for row in sa_result.scalars()}
        if not leader_assignments:
            events = []
        else:
            # Load matching events by id, keep only PUBLISHED
            all_events, _ = await event_repo.list(
                district_id=export_token.district_id,
                status=EventStatus.PUBLISHED,
                limit=2000,
                offset=0,
            )
            events = [e for e in all_events if e.id in leader_assignments]
    else:
        # District / congregation calendar
        events, _ = await event_repo.list(
            district_id=export_token.district_id,
            congregation_id=export_token.congregation_id,
            status=EventStatus.PUBLISHED,
            limit=1000,
            offset=0,
        )

    # Load assignments in one batch query
    sa_repo = SqlServiceAssignmentRepository(session)
    assignments = await sa_repo.list_by_events([e.id for e in events])

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

        # For each event keep the best name (non-None wins over None)
        existing = assignment_map.get(a.event_id)
        if a.event_id not in assignment_map or (display_name is not None and existing is None):
            assignment_map[a.event_id] = display_name

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

    for event in events:
        vevent = ICalEvent()
        vevent.add("uid", f"{event.id}@nak-bezirksplaner")

        # Personal leader calendar: include congregation name in summary
        if export_token.leader_id and event.congregation_id and event.congregation_id in cong_map:
            vevent.add("summary", f"{event.title} – {cong_map[event.congregation_id]}")
        else:
            vevent.add("summary", event.title)

        vevent.add("dtstart", event.start_at)
        vevent.add("dtend", event.end_at)
        vevent.add("dtstamp", event.created_at)

        if event.congregation_id and event.congregation_id in cong_map:
            vevent.add("location", cong_map[event.congregation_id])

        if event.category:
            vevent.add("categories", event.category)

        if event.description:
            vevent.add("description", event.description)

        leader = assignment_map.get(event.id)
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
