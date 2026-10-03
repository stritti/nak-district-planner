"""District-scoped management of event-driven mail hooks (district admins only)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_event_mail_hook_repository,
)
from app.adapters.api.schemas.event_hooks import (
    EventHookCreate,
    EventHookResponse,
    EventHookUpdate,
    EventTypeInfo,
)
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.orm_models.district import DistrictORM
from app.adapters.db.repositories.event_mail_hook import SqlEventMailHookRepository
from app.domain.events import EventType
from app.domain.models.event_mail_hook import EVENT_PLACEHOLDERS, EventMailHook
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/districts/{district_id}/event-hooks", tags=["event-hooks"])


async def _require_district_admin(
    district_id: uuid.UUID, auth: CurrentUserWithMemberships, db: DbSession
) -> None:
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    if await db.get(DistrictORM, district_id) is None:
        raise HTTPException(status_code=404, detail="Bezirk nicht gefunden")


async def _existing_hook(
    repository: SqlEventMailHookRepository, district_id: uuid.UUID, hook_id: uuid.UUID
) -> EventMailHook:
    hook = await repository.get(district_id, hook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Event-Hook nicht gefunden")
    return hook


@router.get("/event-types", response_model=list[EventTypeInfo])
async def list_event_types(
    district_id: uuid.UUID, auth: CurrentUserWithMemberships, db: DbSession
) -> list[EventTypeInfo]:
    """Return supported event types and placeholders for the editor."""
    await _require_district_admin(district_id, auth, db)
    return [
        EventTypeInfo(event_type=event_type, placeholders=sorted(EVENT_PLACEHOLDERS[event_type]))
        for event_type in EventType
    ]


@router.get("", response_model=list[EventHookResponse])
async def list_event_hooks(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: SqlEventMailHookRepository = Depends(get_event_mail_hook_repository),
) -> list[EventMailHook]:
    await _require_district_admin(district_id, auth, db)
    return await repository.list_by_district(district_id)


@router.post("", response_model=EventHookResponse, status_code=status.HTTP_201_CREATED)
async def create_event_hook(
    district_id: uuid.UUID,
    body: EventHookCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: SqlEventMailHookRepository = Depends(get_event_mail_hook_repository),
) -> EventMailHook:
    await _require_district_admin(district_id, auth, db)
    try:
        hook = EventMailHook(district_id=district_id, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repository.save(hook)
    return hook


@router.put("/{hook_id}", response_model=EventHookResponse)
async def update_event_hook(
    district_id: uuid.UUID,
    hook_id: uuid.UUID,
    body: EventHookUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: SqlEventMailHookRepository = Depends(get_event_mail_hook_repository),
) -> EventMailHook:
    await _require_district_admin(district_id, auth, db)
    hook = await _existing_hook(repository, district_id, hook_id)
    try:
        updated = hook.update(**body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repository.save(updated)
    return updated


@router.delete("/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_event_hook(
    district_id: uuid.UUID,
    hook_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: SqlEventMailHookRepository = Depends(get_event_mail_hook_repository),
) -> Response:
    """Soft delete a hook while retaining it for audit visibility."""
    await _require_district_admin(district_id, auth, db)
    hook = await _existing_hook(repository, district_id, hook_id)
    await repository.save(hook.update(is_active=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
