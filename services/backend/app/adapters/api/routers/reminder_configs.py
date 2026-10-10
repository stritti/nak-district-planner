# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""District-scoped reminder configuration management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_district_reminder_config_repository,
)
from app.adapters.api.schemas.reminder_configs import (
    ReminderConfigCreate,
    ReminderConfigResponse,
    ReminderConfigUpdate,
)
from app.adapters.auth.permissions import require_role_in_district
from app.adapters.db.orm_models.district import DistrictORM
from app.adapters.db.repositories.district_reminder_config import (
    SqlDistrictReminderConfigRepository,
)
from app.domain.models.district_reminder_config import DistrictReminderConfig
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/districts/{district_id}/reminder-configs", tags=["reminder-configs"])


async def _require_district_admin(district_id: uuid.UUID, auth: CurrentUserWithMemberships, db: DbSession) -> None:
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    if await db.get(DistrictORM, district_id) is None:
        raise HTTPException(status_code=404, detail="District not found")


@router.post("", response_model=ReminderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder_config(
    district_id: uuid.UUID, body: ReminderConfigCreate,
    auth: CurrentUserWithMemberships, db: DbSession,
    repository: SqlDistrictReminderConfigRepository = Depends(
        get_district_reminder_config_repository
    ),
) -> ReminderConfigResponse:
    await _require_district_admin(district_id, auth, db)
    try:
        config = DistrictReminderConfig.create(district_id=district_id, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repository.save(config)
    await db.commit()
    return ReminderConfigResponse.model_validate(config)


@router.get("", response_model=list[ReminderConfigResponse])
async def list_reminder_configs(
    district_id: uuid.UUID, auth: CurrentUserWithMemberships, db: DbSession,
    repository: SqlDistrictReminderConfigRepository = Depends(
        get_district_reminder_config_repository
    ),
) -> list[ReminderConfigResponse]:
    await _require_district_admin(district_id, auth, db)
    configs = await repository.list_by_district(district_id)
    return [ReminderConfigResponse.model_validate(config) for config in configs]


@router.put("/{config_id}", response_model=ReminderConfigResponse)
async def update_reminder_config(
    district_id: uuid.UUID, config_id: uuid.UUID, body: ReminderConfigUpdate,
    auth: CurrentUserWithMemberships, db: DbSession,
    repository: SqlDistrictReminderConfigRepository = Depends(
        get_district_reminder_config_repository
    ),
) -> ReminderConfigResponse:
    await _require_district_admin(district_id, auth, db)
    config = await repository.get(district_id, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Reminder configuration not found")
    updates = body.model_dump(exclude_unset=True)
    if any(value is None for value in updates.values()):
        raise HTTPException(status_code=422, detail="Reminder fields cannot be null")
    payload = {**vars(config), **updates, "updated_at": datetime.now(UTC)}
    try:
        updated = DistrictReminderConfig(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repository.save(updated)
    await db.commit()
    return ReminderConfigResponse.model_validate(updated)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_reminder_config(
    district_id: uuid.UUID, config_id: uuid.UUID,
    auth: CurrentUserWithMemberships, db: DbSession,
    repository: SqlDistrictReminderConfigRepository = Depends(
        get_district_reminder_config_repository
    ),
) -> Response:
    await _require_district_admin(district_id, auth, db)
    config = await repository.get(district_id, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Reminder configuration not found")
    config.is_active = False
    config.updated_at = datetime.now(UTC)
    await repository.save(config)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
