from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.api.deps import CurrentUser, DbSession
import httpx

from app.adapters.api.schemas.district import (
    CongregationCreate,
    CongregationGroupCreate,
    CongregationGroupResponse,
    CongregationGroupUpdate,
    CongregationResponse,
    CongregationUpdate,
    DistrictCreate,
    DistrictResponse,
    DistrictUpdate,
    FeiertageImportRequest,
    FeiertageImportResult,
    ServiceTime,
)
from app.application.feiertage_service import (
    DE_STATES,
    import_feiertage,
    import_kirchliche_festtage,
)
from app.adapters.api.schemas.matrix import MatrixCell, MatrixResponse, MatrixRow
from app.adapters.db.repositories import (
    SqlCongregationRepository,
    SqlCongregationGroupRepository,
    SqlDistrictRepository,
    SqlEventRepository,
    SqlEventInstanceRepository,
    SqlLeaderRepository,
    SqlPlanningSlotRepository,
    SqlServiceAssignmentRepository,
)
from app.config import settings
from app.domain.models.congregation import Congregation
from app.domain.models.congregation_group import CongregationGroup
from app.domain.models.district import District

router = APIRouter(prefix="/api/v1/districts", tags=["districts"])


def _expected_dates(service_times: list[dict], from_date: date, to_date: date) -> list[str]:
    """Return ISO date strings for all expected Gottesdienst dates in [from_date, to_date]."""
    dates: list[str] = []
    seen: set[str] = set()
    current = from_date
    while current <= to_date:
        for st in service_times:
            if current.weekday() == st["weekday"]:
                iso = current.isoformat()
                if iso not in seen:
                    dates.append(iso)
                    seen.add(iso)
                break
        current += timedelta(days=1)
    return dates


# ── Districts ─────────────────────────────────────────────────────────────────


@router.post("", response_model=DistrictResponse, status_code=status.HTTP_201_CREATED)
async def create_district(body: DistrictCreate, _: CurrentUser, db: DbSession) -> DistrictResponse:
    district = District.create(name=body.name, state_code=body.state_code)
    await SqlDistrictRepository(db).save(district)
    return _district_response(district)


@router.get("", response_model=list[DistrictResponse])
async def list_districts(_: CurrentUser, db: DbSession) -> list[DistrictResponse]:
    districts = await SqlDistrictRepository(db).list_all()
    return [_district_response(d) for d in districts]


@router.patch("/{district_id}", response_model=DistrictResponse)
async def update_district(
    district_id: uuid.UUID,
    body: DistrictUpdate,
    _: CurrentUser,
    db: DbSession,
) -> DistrictResponse:
    repo = SqlDistrictRepository(db)
    district = await repo.get(district_id)
    if not district:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        district.name = body.name
    if "state_code" in fields:
        district.state_code = body.state_code
    district.updated_at = datetime.now(timezone.utc)
    await repo.save(district)
    return _district_response(district)


def _district_response(d: District) -> DistrictResponse:
    return DistrictResponse(
        id=d.id,
        name=d.name,
        state_code=d.state_code,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


# ── Congregations ─────────────────────────────────────────────────────────────


@router.post(
    "/{district_id}/congregations",
    response_model=CongregationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_congregation(
    district_id: uuid.UUID,
    body: CongregationCreate,
    _: CurrentUser,
    db: DbSession,
) -> CongregationResponse:
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    service_times = (
        [st.model_dump() for st in body.service_times] if body.service_times is not None else None
    )
    congregation = Congregation.create(
        name=body.name,
        district_id=district_id,
        service_times=service_times,
        group_id=body.group_id,
    )
    await SqlCongregationRepository(db).save(congregation)
    return _cong_response(congregation)


@router.get("/{district_id}/congregations", response_model=list[CongregationResponse])
async def list_congregations(
    district_id: uuid.UUID,
    _: CurrentUser,
    db: DbSession,
    group_id: uuid.UUID | None = Query(None),
) -> list[CongregationResponse]:
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    congregations = await SqlCongregationRepository(db).list_by_district(
        district_id, group_id=group_id
    )
    return [_cong_response(c) for c in congregations]


@router.patch("/{district_id}/congregations/{congregation_id}", response_model=CongregationResponse)
async def update_congregation(
    district_id: uuid.UUID,
    congregation_id: uuid.UUID,
    body: CongregationUpdate,
    _: CurrentUser,
    db: DbSession,
) -> CongregationResponse:
    repo = SqlCongregationRepository(db)
    congregation = await repo.get(congregation_id)
    if not congregation or congregation.district_id != district_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gemeinde nicht gefunden")
    if body.name is not None:
        congregation.name = body.name
    if body.service_times is not None:
        congregation.service_times = [st.model_dump() for st in body.service_times]
    if "group_id" in body.model_fields_set:
        congregation.group_id = body.group_id
    congregation.updated_at = datetime.now(timezone.utc)
    await repo.save(congregation)
    return _cong_response(congregation)


def _cong_response(c: Congregation) -> CongregationResponse:
    return CongregationResponse(
        id=c.id,
        name=c.name,
        district_id=c.district_id,
        group_id=c.group_id,
        service_times=[ServiceTime(**st) for st in c.service_times],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ── Congregation Groups ───────────────────────────────────────────────────────


@router.post(
    "/{district_id}/groups",
    response_model=CongregationGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    district_id: uuid.UUID,
    body: CongregationGroupCreate,
    _: CurrentUser,
    db: DbSession,
) -> CongregationGroupResponse:
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    group = CongregationGroup.create(name=body.name, district_id=district_id)
    await SqlCongregationGroupRepository(db).save(group)
    return _group_response(group)


@router.get("/{district_id}/groups", response_model=list[CongregationGroupResponse])
async def list_groups(
    district_id: uuid.UUID,
    _: CurrentUser,
    db: DbSession,
) -> list[CongregationGroupResponse]:
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    groups = await SqlCongregationGroupRepository(db).list_by_district(district_id)
    return [_group_response(g) for g in groups]


@router.patch("/{district_id}/groups/{group_id}", response_model=CongregationGroupResponse)
async def update_group(
    district_id: uuid.UUID,
    group_id: uuid.UUID,
    body: CongregationGroupUpdate,
    _: CurrentUser,
    db: DbSession,
) -> CongregationGroupResponse:
    repo = SqlCongregationGroupRepository(db)
    group = await repo.get(group_id)
    if not group or group.district_id != district_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gruppe nicht gefunden")
    if body.name is not None:
        group.name = body.name
    group.updated_at = datetime.now(timezone.utc)
    await repo.save(group)
    return _group_response(group)


@router.delete("/{district_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    district_id: uuid.UUID,
    group_id: uuid.UUID,
    _: CurrentUser,
    db: DbSession,
) -> None:
    repo = SqlCongregationGroupRepository(db)
    group = await repo.get(group_id)
    if not group or group.district_id != district_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gruppe nicht gefunden")
    await repo.delete(group_id)


def _group_response(g: CongregationGroup) -> CongregationGroupResponse:
    return CongregationGroupResponse(
        id=g.id,
        name=g.name,
        district_id=g.district_id,
        created_at=g.created_at,
        updated_at=g.updated_at,
    )


# ── Matrix ────────────────────────────────────────────────────────────────────


@router.get("/{district_id}/matrix", response_model=MatrixResponse)
async def get_matrix(
    district_id: uuid.UUID,
    _: CurrentUser,
    db: DbSession,
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    group_id: uuid.UUID | None = Query(None),
) -> MatrixResponse:
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")

    congregations = await SqlCongregationRepository(db).list_by_district(
        district_id, group_id=group_id
    )
    from_date = from_dt.date()
    to_date = to_dt.date()

    # Compute expected Gottesdienst-Dates per congregation from their schedule
    expected_by_cong: dict[uuid.UUID, list[str]] = {
        c.id: _expected_dates(c.service_times, from_date, to_date) for c in congregations
    }

    # Load all events for the district in the date range (single query)
    events, _ = await SqlEventRepository(db).list(
        district_id=district_id,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=5000,
        offset=0,
    )

    # Build holidays dict and collect Feiertag dates for the column set
    holidays: dict[str, list[str]] = {}
    for event in events:
        if event.category == "Feiertag":
            date_key = event.start_at.date().isoformat()
            holidays.setdefault(date_key, []).append(event.title)

    # Collect all unique dates: congregation schedules + Feiertag dates
    all_dates: set[str] = set()
    for dates in expected_by_cong.values():
        all_dates.update(dates)
    all_dates.update(holidays.keys())  # kirchliche Feiertage immer als Spalten
    sorted_dates = sorted(all_dates)

    # Filter Gottesdienst events for the matrix cells (include district-level)
    gottesdienst_events = [e for e in events if e.category == "Gottesdienst"]

    # Build lookup: (congregation_id, date) → event
    event_by_cong_date: dict[tuple[uuid.UUID, str], object] = {}
    for event in gottesdienst_events:
        # Use district_id as key for district-level events
        cong_id = event.congregation_id or event.district_id
        key = (cong_id, event.start_at.date().isoformat())
        if key not in event_by_cong_date:
            event_by_cong_date[key] = event

    # Load all assignments for found events in one batch
    event_ids = [e.id for e in gottesdienst_events]
    assignment_lookup_ids = list(event_ids)

    # Batch-load leaders for this district
    leaders = await SqlLeaderRepository(db).list_by_district(district_id)
    leaders_by_id = {leader.id: leader for leader in leaders}

    slot_by_cong_date: dict[tuple[uuid.UUID, str], object] = {}
    instance_by_slot_id: dict[uuid.UUID, object] = {}
    if settings.use_planning_slot_model:
        slots = await SqlPlanningSlotRepository(db).list_for_date_range(
            district_id=district_id,
            from_date=from_date,
            to_date=to_date,
        )
        if slots:
            slot_by_cong_date = {
                ((slot.congregation_id or slot.district_id), slot.planning_date.isoformat()): slot
                for slot in slots
                if slot.category == "Gottesdienst"
            }
            instances = await SqlEventInstanceRepository(db).list_by_planning_slots(
                [slot.id for slot in slots]
            )
            instance_by_slot_id = {instance.planning_slot_id: instance for instance in instances}
            assignment_lookup_ids.extend(slot.id for slot in slots)

    assignments = await SqlServiceAssignmentRepository(db).list_by_events(assignment_lookup_ids)
    assignment_by_event: dict[uuid.UUID, object] = {}
    for a in assignments:
        assignment_key = a.planning_slot_id or a.event_id
        if assignment_key not in assignment_by_event:
            assignment_by_event[assignment_key] = a

    # Build matrix rows
    rows: list[MatrixRow] = []

    for congregation in congregations:
        cong_expected = set(expected_by_cong[congregation.id])
        cells: dict[str, MatrixCell] = {}

        for date_key in sorted_dates:
            if date_key not in cong_expected:
                # Feiertag-Spalte oder anderer Bezirks-Termin — nicht im Gemeinde-Zeitplan
                cells[date_key] = MatrixCell()
                continue

            slot = slot_by_cong_date.get((congregation.id, date_key))
            instance = instance_by_slot_id.get(slot.id) if slot else None
            event = event_by_cong_date.get((congregation.id, date_key)) if slot is None else None

            if slot is None and event is None:
                # Im Zeitplan erwartet, aber noch kein Event angelegt
                cells[date_key] = MatrixCell()
                continue

            assignment_key = slot.id if slot is not None else event.id
            assignment = assignment_by_event.get(assignment_key)
            # Resolve leader name from leader_id if leader_name is not set directly
            leader_name: str | None = None
            leader_id = None
            if assignment:
                leader_id = assignment.leader_id
                if assignment.leader_name:
                    leader_name = assignment.leader_name
                elif assignment.leader_id and assignment.leader_id in leaders_by_id:
                    ldr = leaders_by_id[assignment.leader_id]
                    rank_prefix = f"{ldr.rank.value} " if ldr.rank else ""
                    leader_name = f"{rank_prefix}{ldr.name}"
            cells[date_key] = MatrixCell(
                event_id=event.id if event is not None else instance.id if instance is not None else None,
                planning_slot_id=slot.id if slot is not None else None,
                event_title=event.title if event is not None else instance.title if instance else None,
                category=event.category if event is not None else slot.category if slot is not None else None,
                is_gap=assignment is None,
                planned_time=slot.planning_time if slot is not None else event.start_at.timetz().replace(tzinfo=None),
                actual_start_at=instance.actual_start_at if instance is not None else event.start_at,
                actual_end_at=instance.actual_end_at if instance is not None else event.end_at,
                has_deviation=instance.deviation_flag if instance is not None else False,
                assignment_id=assignment.id if assignment else None,
                assignment_status=assignment.status if assignment else None,
                leader_id=leader_id,
                leader_name=leader_name,
            )

        rows.append(
            MatrixRow(
                congregation_id=congregation.id,
                congregation_name=congregation.name,
                cells=cells,
            )
        )

    return MatrixResponse(dates=sorted_dates, rows=rows, holidays=holidays)


# ── Feiertage ─────────────────────────────────────────────────────────────────


@router.get("/{district_id}/feiertage/states")
async def list_de_states(_: CurrentUser) -> dict[str, str]:
    """Return mapping of 2-letter state codes to German names."""
    return DE_STATES


@router.post("/{district_id}/feiertage", response_model=FeiertageImportResult)
async def import_feiertage_endpoint(
    district_id: uuid.UUID,
    body: FeiertageImportRequest,
    _: CurrentUser,
    db: DbSession,
) -> FeiertageImportResult:
    """Import German public holidays from Nager.Date API into the district (idempotent)."""
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")

    if body.state_code and body.state_code.upper() not in DE_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unbekanntes Bundesland-Kürzel: {body.state_code}. Gültig: {', '.join(DE_STATES)}",
        )

    totals = {"created": 0, "updated": 0, "skipped": 0}

    # 1. Gesetzliche Feiertage via Nager.Date (nur wenn Bundesland konfiguriert)
    if body.state_code:
        try:
            r = await import_feiertage(
                district_id=district_id,
                year=body.year,
                state_code=body.state_code.upper(),
                session=db,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Feiertags-API nicht erreichbar: {exc}",
            ) from exc
        for k in totals:
            totals[k] += r[k]

    # 2. Kirchliche Festtage (Palmsonntag, Ostersonntag, Pfingstsonntag) — immer
    r = await import_kirchliche_festtage(
        district_id=district_id,
        year=body.year,
        session=db,
    )
    for k in totals:
        totals[k] += r[k]

    return FeiertageImportResult(**totals)
