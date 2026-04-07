from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.api.deps import CurrentUser, CurrentUserWithMemberships, DbSession
from app.adapters.auth.permissions import (
    PermissionError,
    assert_has_role_in_district,
)
from app.adapters.api.schemas.event import (
    EventCreate,
    EventListResponse,
    EventResponse,
    EventUpdate,
)
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.event import SqlEventRepository
from app.application.invitation_service import propagate_source_event_update
from app.domain.models.event import Event, EventStatus
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> EventResponse:
    # Check if user has PLANNER role (or higher) in the district
    try:
        assert_has_role_in_district(auth, Role.PLANNER, body.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

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
    _: CurrentUser,
    db: DbSession,
    district_id: uuid.UUID | None = Query(None),
    congregation_id: uuid.UUID | None = Query(None),
    group_id: uuid.UUID | None = Query(None),
    only_district_level: bool = Query(False),
    status: EventStatus | None = Query(None),
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> EventListResponse:
    repo = SqlEventRepository(db)
    congregation_repo = SqlCongregationRepository(db)
    events, total = await repo.list(
        district_id=district_id,
        congregation_id=congregation_id,
        group_id=group_id,
        only_district_level=only_district_level,
        status=status,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit,
        offset=offset,
    )

    invitation_source_ids = list(
        {
            e.invitation_source_congregation_id
            for e in events
            if e.invitation_source_congregation_id is not None
        }
    )
    source_congregation_names: dict[uuid.UUID, str] = {}
    if invitation_source_ids:
        source_congregations = await congregation_repo.list_by_ids(invitation_source_ids)
        source_congregation_names = {c.id: c.name for c in source_congregations}

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
                invitation_source_congregation_id=e.invitation_source_congregation_id,
                invitation_source_congregation_name=source_congregation_names.get(
                    e.invitation_source_congregation_id
                )
                if e.invitation_source_congregation_id is not None
                else None,
                invitation_source_event_id=e.invitation_source_event_id,
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
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> EventResponse:
    """Reassign district/congregation or change status/category of an existing event."""
    repo = SqlEventRepository(db)
    event = await repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Check if user has PLANNER role (or higher) in the current district
    try:
        assert_has_role_in_district(auth, Role.PLANNER, event.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # If reassigning to a different district, check access there too
    fields = body.model_fields_set
    if (
        "district_id" in fields
        and body.district_id is not None
        and body.district_id != event.district_id
    ):
        try:
            assert_has_role_in_district(auth, Role.PLANNER, body.district_id)
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        event.district_id = body.district_id

    if "congregation_id" in fields:
        event.congregation_id = body.congregation_id  # None = district-level
    if "title" in fields and body.title is not None:
        event.title = body.title
    if "description" in fields:
        event.description = body.description
    if "start_at" in fields and body.start_at is not None:
        event.start_at = body.start_at
    if "end_at" in fields and body.end_at is not None:
        event.end_at = body.end_at
    if "status" in fields and body.status is not None:
        event.status = body.status
    if "category" in fields:
        event.category = body.category

    event.updated_at = datetime.now(timezone.utc)
    await repo.save(event)

    propagated_fields = {"title", "description", "start_at", "end_at", "category"}
    if propagated_fields.intersection(fields) and event.invitation_source_event_id is None:
        await propagate_source_event_update(db, source_event=event)

    source_name = None
    if event.invitation_source_congregation_id is not None:
        source_congregation = await SqlCongregationRepository(db).get(
            event.invitation_source_congregation_id
        )
        source_name = source_congregation.name if source_congregation else None

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
        invitation_source_congregation_id=event.invitation_source_congregation_id,
        invitation_source_congregation_name=source_name,
        invitation_source_event_id=event.invitation_source_event_id,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )
