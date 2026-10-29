# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""District-scoped management of event-driven mail hooks (district admins only)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, replace
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_event_mail_hook_repository,
)
from app.adapters.api.district_guards import require_district_admin
from app.adapters.api.revisions import entity_revision, next_updated_at, require_current_revision
from app.adapters.api.schemas.event_hooks import (
    EventHookCreate,
    EventHookResponse,
    EventHookUpdate,
    EventTypeInfo,
)
from app.domain.events import EventType
from app.domain.models.event_mail_hook import EVENT_PLACEHOLDERS, EventMailHook
from app.domain.ports.event_mail_hooks import EventMailHookRepository

router = APIRouter(prefix="/api/v1/districts/{district_id}/event-hooks", tags=["event-hooks"])

IfMatch = Annotated[str | None, Header(alias="If-Match")]


def _response(hook: EventMailHook) -> EventHookResponse:
    return EventHookResponse.model_validate(
        {**asdict(hook), "revision": entity_revision(hook.id, hook.updated_at)}
    )


async def _existing_hook(
    repository: EventMailHookRepository, district_id: uuid.UUID, hook_id: uuid.UUID
) -> EventMailHook:
    hook = await repository.get_for_update(district_id, hook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Event-Hook nicht gefunden")
    return hook


@router.get("/event-types", response_model=list[EventTypeInfo])
async def list_event_types(
    district_id: uuid.UUID, auth: CurrentUserWithMemberships, db: DbSession
) -> list[EventTypeInfo]:
    """Return supported event types and placeholders for the editor."""
    await require_district_admin(district_id, auth, db)
    return [
        EventTypeInfo(event_type=event_type, placeholders=sorted(EVENT_PLACEHOLDERS[event_type]))
        for event_type in EventType
    ]


@router.get("", response_model=list[EventHookResponse])
async def list_event_hooks(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventMailHookRepository = Depends(get_event_mail_hook_repository),
) -> list[EventHookResponse]:
    await require_district_admin(district_id, auth, db)
    return [_response(hook) for hook in await repository.list_by_district(district_id)]


@router.post("", response_model=EventHookResponse, status_code=status.HTTP_201_CREATED)
async def create_event_hook(
    district_id: uuid.UUID,
    body: EventHookCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventMailHookRepository = Depends(get_event_mail_hook_repository),
) -> EventHookResponse:
    await require_district_admin(district_id, auth, db)
    try:
        hook = EventMailHook(district_id=district_id, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repository.save(hook)
    return _response(hook)


@router.put("/{hook_id}", response_model=EventHookResponse)
async def update_event_hook(
    district_id: uuid.UUID,
    hook_id: uuid.UUID,
    body: EventHookUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventMailHookRepository = Depends(get_event_mail_hook_repository),
    if_match: IfMatch = None,
) -> EventHookResponse:
    await require_district_admin(district_id, auth, db)
    hook = await _existing_hook(repository, district_id, hook_id)
    require_current_revision(if_match, entity_revision(hook.id, hook.updated_at))
    try:
        updated = replace(
            hook.update(**body.model_dump()), updated_at=next_updated_at(hook.updated_at)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repository.save(updated)
    return _response(updated)


@router.delete("/{hook_id}", response_model=EventHookResponse)
async def deactivate_event_hook(
    district_id: uuid.UUID,
    hook_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventMailHookRepository = Depends(get_event_mail_hook_repository),
    if_match: IfMatch = None,
) -> EventHookResponse:
    """Soft delete a hook while retaining it for audit visibility."""
    await require_district_admin(district_id, auth, db)
    hook = await _existing_hook(repository, district_id, hook_id)
    require_current_revision(if_match, entity_revision(hook.id, hook.updated_at))
    deactivated = replace(
        hook.update(is_active=False), updated_at=next_updated_at(hook.updated_at)
    )
    await repository.save(deactivated)
    return _response(deactivated)
