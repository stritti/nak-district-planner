from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.api.deps import ApiKeyGuard, DbSession
from app.adapters.api.schemas.district import (
    CongregationCreate,
    CongregationResponse,
    CongregationUpdate,
    DistrictCreate,
    DistrictResponse,
    DistrictUpdate,
)
from app.adapters.api.schemas.matrix import MatrixCell, MatrixResponse, MatrixRow
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.event import SqlEventRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.domain.models.congregation import Congregation
from app.domain.models.district import District

router = APIRouter(prefix="/api/v1/districts", tags=["districts"])


@router.post("", response_model=DistrictResponse, status_code=status.HTTP_201_CREATED)
async def create_district(
    body: DistrictCreate,
    _: ApiKeyGuard,
    db: DbSession,
) -> DistrictResponse:
    district = District.create(name=body.name)
    repo = SqlDistrictRepository(db)
    await repo.save(district)
    return DistrictResponse(
        id=district.id,
        name=district.name,
        created_at=district.created_at,
        updated_at=district.updated_at,
    )


@router.get("", response_model=list[DistrictResponse])
async def list_districts(
    _: ApiKeyGuard,
    db: DbSession,
) -> list[DistrictResponse]:
    repo = SqlDistrictRepository(db)
    districts = await repo.list_all()
    return [
        DistrictResponse(id=d.id, name=d.name, created_at=d.created_at, updated_at=d.updated_at)
        for d in districts
    ]


@router.post(
    "/{district_id}/congregations",
    response_model=CongregationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_congregation(
    district_id: uuid.UUID,
    body: CongregationCreate,
    _: ApiKeyGuard,
    db: DbSession,
) -> CongregationResponse:
    district_repo = SqlDistrictRepository(db)
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")

    congregation = Congregation.create(name=body.name, district_id=district_id)
    repo = SqlCongregationRepository(db)
    await repo.save(congregation)
    return CongregationResponse(
        id=congregation.id,
        name=congregation.name,
        district_id=congregation.district_id,
        created_at=congregation.created_at,
        updated_at=congregation.updated_at,
    )


@router.get("/{district_id}/congregations", response_model=list[CongregationResponse])
async def list_congregations(
    district_id: uuid.UUID,
    _: ApiKeyGuard,
    db: DbSession,
) -> list[CongregationResponse]:
    district_repo = SqlDistrictRepository(db)
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")

    repo = SqlCongregationRepository(db)
    congregations = await repo.list_by_district(district_id)
    return [
        CongregationResponse(
            id=c.id,
            name=c.name,
            district_id=c.district_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in congregations
    ]


@router.patch("/{district_id}", response_model=DistrictResponse)
async def update_district(
    district_id: uuid.UUID,
    body: DistrictUpdate,
    _: ApiKeyGuard,
    db: DbSession,
) -> DistrictResponse:
    repo = SqlDistrictRepository(db)
    district = await repo.get(district_id)
    if not district:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    district.name = body.name
    district.updated_at = datetime.now(timezone.utc)
    await repo.save(district)
    return DistrictResponse(
        id=district.id,
        name=district.name,
        created_at=district.created_at,
        updated_at=district.updated_at,
    )


@router.patch("/{district_id}/congregations/{congregation_id}", response_model=CongregationResponse)
async def update_congregation(
    district_id: uuid.UUID,
    congregation_id: uuid.UUID,
    body: CongregationUpdate,
    _: ApiKeyGuard,
    db: DbSession,
) -> CongregationResponse:
    repo = SqlCongregationRepository(db)
    congregation = await repo.get(congregation_id)
    if not congregation or congregation.district_id != district_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gemeinde nicht gefunden")
    congregation.name = body.name
    congregation.updated_at = datetime.now(timezone.utc)
    await repo.save(congregation)
    return CongregationResponse(
        id=congregation.id,
        name=congregation.name,
        district_id=congregation.district_id,
        created_at=congregation.created_at,
        updated_at=congregation.updated_at,
    )


@router.get("/{district_id}/matrix", response_model=MatrixResponse)
async def get_matrix(
    district_id: uuid.UUID,
    _: ApiKeyGuard,
    db: DbSession,
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
) -> MatrixResponse:
    district_repo = SqlDistrictRepository(db)
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")

    congregations = await SqlCongregationRepository(db).list_by_district(district_id)

    # Load all events for the district in the date range (no pagination limit)
    events, _ = await SqlEventRepository(db).list(
        district_id=district_id,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=5000,
        offset=0,
    )

    # Load all assignments for these events in one query
    event_ids = [e.id for e in events]
    assignments = await SqlServiceAssignmentRepository(db).list_by_events(event_ids)

    # Build lookup: event_id → first assignment
    assignment_by_event: dict[uuid.UUID, object] = {}
    for a in assignments:
        if a.event_id not in assignment_by_event:
            assignment_by_event[a.event_id] = a

    # Group events by (congregation_id, date)
    from collections import defaultdict

    events_by_cong_date: dict[uuid.UUID, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for event in events:
        if event.congregation_id is None:
            continue
        date_key = event.start_at.date().isoformat()
        events_by_cong_date[event.congregation_id][date_key].append(event)

    # Collect all unique dates across all congregations
    all_dates: set[str] = set()
    for date_map in events_by_cong_date.values():
        all_dates.update(date_map.keys())
    sorted_dates = sorted(all_dates)

    # Build matrix rows
    rows: list[MatrixRow] = []
    for congregation in congregations:
        cells: dict[str, MatrixCell] = {}
        date_map = events_by_cong_date.get(congregation.id, {})

        for date_key in sorted_dates:
            cong_events = date_map.get(date_key, [])

            # Prioritize Gottesdienst events
            gottesdienst = [e for e in cong_events if e.category == "Gottesdienst"]
            primary = gottesdienst[0] if gottesdienst else (cong_events[0] if cong_events else None)

            if primary is None:
                cells[date_key] = MatrixCell()
                continue

            assignment = assignment_by_event.get(primary.id)
            is_gap = primary.category == "Gottesdienst" and assignment is None
            cells[date_key] = MatrixCell(
                event_id=primary.id,
                event_title=primary.title,
                category=primary.category,
                is_gap=is_gap,
                assignment_id=assignment.id if assignment else None,
                assignment_status=assignment.status if assignment else None,
                leader_name=assignment.leader_name if assignment else None,
            )

        rows.append(
            MatrixRow(
                congregation_id=congregation.id,
                congregation_name=congregation.name,
                cells=cells,
            )
        )

    return MatrixResponse(dates=sorted_dates, rows=rows)
