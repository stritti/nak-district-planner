# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Reminder configuration endpoint tests, including district isolation and errors."""

from __future__ import annotations

import uuid
from datetime import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import reminder_configs as router
from app.adapters.api.schemas.reminder_configs import ReminderConfigCreate, ReminderConfigUpdate
from app.domain.models.district_reminder_config import DistrictReminderConfig
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


def auth_for(district_id: uuid.UUID, role: Role = Role.DISTRICT_ADMIN):
    return SimpleNamespace(
        user_sub="admin",
        user=SimpleNamespace(is_superadmin=False),
        memberships=[Membership.create(
            user_sub="admin", role=role,
            scope_type=ScopeType.DISTRICT, scope_id=district_id,
        )],
    )


def payload() -> ReminderConfigCreate:
    return ReminderConfigCreate(
        day_of_month=31, time_of_day="10:30",
        subject_template="Planung {month}", body_template="Hallo {district_name}",
        recipient_role=Role.PLANNER,
    )


def persisted(district_id: uuid.UUID) -> DistrictReminderConfig:
    return DistrictReminderConfig.create(district_id=district_id, **payload().model_dump())


@pytest.mark.asyncio
async def test_create_and_list_configs() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    db.get.return_value = object()
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.list_by_district = AsyncMock(return_value=[])
    created = await router.create_reminder_config(
        district_id, payload(), auth_for(district_id), db, repo
    )
    assert created.district_id == district_id
    assert created.recipient_role == Role.PLANNER
    repo.save.assert_awaited_once()
    db.commit.assert_awaited_once()
    assert await router.list_reminder_configs(district_id, auth_for(district_id), db, repo) == []
    repo.list_by_district.assert_awaited_once_with(district_id)


@pytest.mark.asyncio
async def test_get_rejects_other_district_admin_before_db_access() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await router.list_reminder_configs(district_id, auth_for(uuid.uuid4()), db)
    assert error.value.status_code == 403
    db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_rejects_insufficient_role_and_missing_district() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await router.list_reminder_configs(district_id, auth_for(district_id, Role.PLANNER), db)
    assert error.value.status_code == 403
    db.get.assert_not_awaited()
    db.get.return_value = None
    with pytest.raises(HTTPException) as error:
        await router.list_reminder_configs(district_id, auth_for(district_id), db)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_update_validated_config() -> None:
    district_id = uuid.uuid4()
    existing = persisted(district_id)
    db = AsyncMock()
    db.get.return_value = object()
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=existing)
    repo.save = AsyncMock()
    response = await router.update_reminder_config(
        district_id, existing.id,
        ReminderConfigUpdate(subject_template="Neuer Betreff", day_of_month=30),
        auth_for(district_id), db, repo,
    )
    assert response.subject_template == "Neuer Betreff"
    assert response.day_of_month == 30
    assert response.id == existing.id
    repo.get.assert_awaited_once_with(district_id, existing.id)
    repo.save.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_rejects_null_blank_and_unknown_config() -> None:
    district_id = uuid.uuid4()
    existing = persisted(district_id)
    db = AsyncMock()
    db.get.return_value = object()
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=existing)
    repo.save = AsyncMock()
    for invalid in (ReminderConfigUpdate(time_of_day=None), ReminderConfigUpdate(body_template=" ")):
        with pytest.raises(HTTPException) as error:
            await router.update_reminder_config(
                district_id, existing.id, invalid, auth_for(district_id), db, repo,
            )
        assert error.value.status_code == 422
    repo.save.assert_not_awaited()
    repo.get.return_value = None
    with pytest.raises(HTTPException) as error:
        await router.update_reminder_config(
            district_id, existing.id, ReminderConfigUpdate(is_active=False),
            auth_for(district_id), db, repo,
        )
    assert error.value.status_code == 404
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_soft_disables_and_rejects_unknown_config() -> None:
    district_id = uuid.uuid4()
    existing = persisted(district_id)
    db = AsyncMock()
    db.get.return_value = object()
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=existing)
    repo.save = AsyncMock()
    response = await router.deactivate_reminder_config(
        district_id, existing.id, auth_for(district_id), db, repo,
    )
    assert response.status_code == 204
    assert existing.is_active is False
    repo.save.assert_awaited_once()
    db.commit.assert_awaited_once()
    repo.get.return_value = None
    with pytest.raises(HTTPException) as error:
        await router.deactivate_reminder_config(
            district_id, uuid.uuid4(), auth_for(district_id), db, repo,
        )
    assert error.value.status_code == 404
