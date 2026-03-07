from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.api.deps import ApiKeyGuard, DbSession
from app.adapters.api.schemas.event import (
    EventCreate,
    EventListResponse,
    EventResponse,
    EventUpdate,
)
from app.adapters.db.repositories.event import SqlEventRepository
from app.domain.models.event import Event, EventStatus

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreate,
    _: ApiKeyGuard,
    db: DbSession,
) -> EventResponse:
    event = Event.create(
        title=body.title,
        description=body.description,
        start_at=body.start_at,
        end_at=body.end_at,
        district_id=body.district_id,
        congregation_id=body.congregation_id,
        category=body.category,
        source=body.source,
        status=body.status,
        visibility=body.visibility,
        audiences=body.audiences,
        applicability=body.applicability,
    )
    repo = SqlEventRepository(db)
    await repo.save(event)
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        start_at=event.start_at,
        end_at=event.end_at,
        district_id=event.district_id,
        congregation_id=event.congregation_id,
        category=event.category,
        source=event.source,
        status=event.status,
        visibility=event.visibility,
        audiences=event.audiences,
        applicability=event.applicability,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("", response_model=EventListResponse)
async def list_events(
    _: ApiKeyGuard,
    db: DbSession,
    district_id: uuid.UUID | None = Query(None),
    congregation_id: uuid.UUID | None = Query(None),
    status: EventStatus | None = Query(None),
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> EventListResponse:
    repo = SqlEventRepository(db)
    events, total = await repo.list(
        district_id=district_id,
        congregation_id=congregation_id,
        status=status,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit,
        offset=offset,
    )
    return EventListResponse(
        items=[
            EventResponse(
                id=e.id,
                title=e.title,
                description=e.description,
                start_at=e.start_at,
                end_at=e.end_at,
                district_id=e.district_id,
                congregation_id=e.congregation_id,
                category=e.category,
                source=e.source,
                status=e.status,
                visibility=e.visibility,
                audiences=e.audiences,
                applicability=e.applicability,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in events
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    _: ApiKeyGuard,
    db: DbSession,
) -> EventResponse:
    """Reassign district/congregation or change status/category of an existing event."""
    repo = SqlEventRepository(db)
    event = await repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    fields = body.model_fields_set
    if "district_id" in fields and body.district_id is not None:
        event.district_id = body.district_id
    if "congregation_id" in fields:
        event.congregation_id = body.congregation_id  # None = district-level
    if "status" in fields and body.status is not None:
        event.status = body.status
    if "category" in fields:
        event.category = body.category

    event.updated_at = datetime.now(timezone.utc)
    await repo.save(event)
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        start_at=event.start_at,
        end_at=event.end_at,
        district_id=event.district_id,
        congregation_id=event.congregation_id,
        category=event.category,
        source=event.source,
        status=event.status,
        visibility=event.visibility,
        audiences=event.audiences,
        applicability=event.applicability,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )
