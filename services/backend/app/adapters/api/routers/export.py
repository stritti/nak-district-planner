from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from icalendar import Calendar
from icalendar import Event as ICalEvent

from app.adapters.api.deps import ApiKeyGuard, DbSession
from app.adapters.api.schemas.export_token import ExportTokenCreate, ExportTokenResponse
from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.repositories.event import SqlEventRepository
from app.adapters.db.repositories.export_token import SqlExportTokenRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.domain.models.event import EventStatus
from app.domain.models.export_token import ExportToken, TokenType

router = APIRouter()

# ── Token management (requires API key) ──────────────────────────────────────


@router.post(
    "/export-tokens",
    response_model=ExportTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_export_token(
    _: ApiKeyGuard, body: ExportTokenCreate, session: DbSession
) -> ExportTokenResponse:
    token = ExportToken.create(
        label=body.label,
        token_type=body.token_type,
        district_id=body.district_id,
        congregation_id=body.congregation_id,
    )
    repo = SqlExportTokenRepository(session)
    await repo.save(token)
    return ExportTokenResponse(
        id=token.id,
        token=token.token,
        label=token.label,
        token_type=token.token_type,
        district_id=token.district_id,
        congregation_id=token.congregation_id,
        created_at=token.created_at,
    )


@router.get(
    "/export-tokens",
    response_model=list[ExportTokenResponse],
)
async def list_export_tokens(
    _: ApiKeyGuard,
    session: DbSession,
    district_id: uuid.UUID | None = None,
) -> list[ExportTokenResponse]:
    repo = SqlExportTokenRepository(session)
    tokens = await repo.list_by_district(district_id) if district_id else await repo.list_all()
    return [
        ExportTokenResponse(
            id=t.id,
            token=t.token,
            label=t.label,
            token_type=t.token_type,
            district_id=t.district_id,
            congregation_id=t.congregation_id,
            created_at=t.created_at,
        )
        for t in tokens
    ]


@router.delete(
    "/export-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_export_token(_: ApiKeyGuard, token_id: uuid.UUID, session: DbSession) -> None:
    repo = SqlExportTokenRepository(session)
    deleted = await repo.delete(token_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token nicht gefunden")


# ── Public ICS export (no auth) ──────────────────────────────────────────────


@router.get("/export/{token_str}/calendar.ics", include_in_schema=False)
async def export_calendar_ics(token_str: str, session: DbSession) -> Response:
    token_repo = SqlExportTokenRepository(session)
    export_token = await token_repo.get_by_token(token_str)
    if not export_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token ungültig")

    # Load all PUBLISHED events for this token's scope
    event_repo = SqlEventRepository(session)
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
    # Take the first assignment per event (most recent)
    assignment_map: dict[uuid.UUID, str | None] = {}
    for a in assignments:
        if a.event_id not in assignment_map and a.leader_name:
            assignment_map[a.event_id] = a.leader_name

    # Load congregation names for LOCATION field
    from sqlalchemy import select

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
            if export_token.token_type == TokenType.INTERNAL:
                vevent.add("comment", f"Dienstleiter: {leader}")
            else:
                vevent.add("comment", "Dienstleiter: [Name anonymisiert]")

        cal.add_component(vevent)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="calendar.ics"'},
    )
