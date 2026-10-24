# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""District-scoped reminder configuration management."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_district_reminder_config_repository,
)
from app.adapters.api.district_guards import require_district_admin
from app.adapters.api.revisions import entity_revision, next_updated_at, require_current_revision
from app.adapters.api.schemas.reminder_configs import (
    ReminderConfigCreate,
    ReminderConfigResponse,
    ReminderConfigUpdate,
)
from app.adapters.db.repositories.district_reminder_config import (
    SqlDistrictReminderConfigRepository,
)
from app.domain.models.district_reminder_config import DistrictReminderConfig

router = APIRouter(prefix="/api/v1/districts/{district_id}/reminder-configs", tags=["reminder-configs"])

IfMatch = Annotated[str | None, Header(alias="If-Match")]


def _response(config: DistrictReminderConfig) -> ReminderConfigResponse:
    return ReminderConfigResponse.model_validate(
        {**vars(config), "revision": entity_revision(config.id, config.updated_at)}
    )


@router.post("", response_model=ReminderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder_config(
    district_id: uuid.UUID, body: ReminderConfigCreate,
    auth: CurrentUserWithMemberships, db: DbSession,
    repository: SqlDistrictReminderConfigRepository = Depends(
        get_district_reminder_config_repository
    ),
) -> ReminderConfigResponse:
    await require_district_admin(district_id, auth, db)
    try:
        config = DistrictReminderConfig.create(district_id=district_id, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repository.save(config)
    await db.commit()
    return _response(config)


@router.get("", response_model=list[ReminderConfigResponse])
async def list_reminder_configs(
    district_id: uuid.UUID, auth: CurrentUserWithMemberships, db: DbSession,
    repository: SqlDistrictReminderConfigRepository = Depends(
        get_district_reminder_config_repository
    ),
) -> list[ReminderConfigResponse]:
    await require_district_admin(district_id, auth, db)
    configs = await repository.list_by_district(district_id)
    return [_response(config) for config in configs]


@router.put("/{config_id}", response_model=ReminderConfigResponse)
async def update_reminder_config(
    district_id: uuid.UUID, config_id: uuid.UUID, body: ReminderConfigUpdate,
    auth: CurrentUserWithMemberships, db: DbSession,
    repository: SqlDistrictReminderConfigRepository = Depends(
        get_district_reminder_config_repository
    ),
    if_match: IfMatch = None,
) -> ReminderConfigResponse:
    await require_district_admin(district_id, auth, db)
    config = await repository.get_for_update(district_id, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Reminder configuration not found")
    require_current_revision(if_match, entity_revision(config.id, config.updated_at))
    updates = body.model_dump(exclude_unset=True)
    if any(value is None for value in updates.values()):
        raise HTTPException(status_code=422, detail="Reminder fields cannot be null")
    payload = {**vars(config), **updates, "updated_at": next_updated_at(config.updated_at)}
    try:
        updated = DistrictReminderConfig(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repository.save(updated)
    await db.commit()
    return _response(updated)


@router.delete("/{config_id}", response_model=ReminderConfigResponse)
async def deactivate_reminder_config(
    district_id: uuid.UUID, config_id: uuid.UUID,
    auth: CurrentUserWithMemberships, db: DbSession,
    repository: SqlDistrictReminderConfigRepository = Depends(
        get_district_reminder_config_repository
    ),
    if_match: IfMatch = None,
) -> ReminderConfigResponse:
    """Soft-deactivate; the updated record carries the new revision."""
    await require_district_admin(district_id, auth, db)
    config = await repository.get_for_update(district_id, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Reminder configuration not found")
    require_current_revision(if_match, entity_revision(config.id, config.updated_at))
    config.is_active = False
    config.updated_at = next_updated_at(config.updated_at)
    await repository.save(config)
    await db.commit()
    return _response(config)
