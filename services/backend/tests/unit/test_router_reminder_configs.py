# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Reminder configuration endpoint tests, including district isolation and errors."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.adapters.api.revisions import entity_revision
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


def revision_of(config: DistrictReminderConfig) -> str:
    return entity_revision(config.id, config.updated_at)


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
    repo.get_for_update = AsyncMock(return_value=existing)
    repo.save = AsyncMock()
    response = await router.update_reminder_config(
        district_id, existing.id,
        ReminderConfigUpdate(subject_template="Neuer Betreff", day_of_month=30),
        auth_for(district_id), db, repo, if_match=revision_of(existing),
    )
    assert response.subject_template == "Neuer Betreff"
    assert response.revision != revision_of(existing)
    assert response.day_of_month == 30
    assert response.id == existing.id
    repo.get_for_update.assert_awaited_once_with(district_id, existing.id)
    repo.save.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_rejects_null_blank_and_unknown_config() -> None:
    district_id = uuid.uuid4()
    existing = persisted(district_id)
    db = AsyncMock()
    db.get.return_value = object()
    repo = AsyncMock()
    repo.get_for_update = AsyncMock(return_value=existing)
    repo.save = AsyncMock()
    for invalid in (ReminderConfigUpdate(time_of_day=None), ReminderConfigUpdate(body_template=" ")):
        with pytest.raises(HTTPException) as error:
            await router.update_reminder_config(
                district_id, existing.id, invalid, auth_for(district_id), db, repo,
                if_match=revision_of(existing),
            )
        assert error.value.status_code == 422
    repo.save.assert_not_awaited()
    repo.get_for_update.return_value = None
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
    repo.get_for_update = AsyncMock(return_value=existing)
    repo.save = AsyncMock()
    before = revision_of(existing)
    response = await router.deactivate_reminder_config(
        district_id, existing.id, auth_for(district_id), db, repo, if_match=before,
    )
    assert response.is_active is False
    assert response.revision != before
    assert existing.is_active is False
    repo.save.assert_awaited_once()
    db.commit.assert_awaited_once()
    repo.get_for_update.return_value = None
    with pytest.raises(HTTPException) as error:
        await router.deactivate_reminder_config(
            district_id, uuid.uuid4(), auth_for(district_id), db, repo,
        )
    assert error.value.status_code == 404


class TestConditionalWrites:
    """Updates and the active switch are conditional: 428 missing, 412 stale."""

    @staticmethod
    def _repo(existing):
        repo = AsyncMock()
        repo.get_for_update = AsyncMock(return_value=existing)
        repo.save = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_responses_carry_a_revision(self) -> None:
        district_id = uuid.uuid4()
        existing = persisted(district_id)
        repo = self._repo(existing)
        repo.list_by_district = AsyncMock(return_value=[existing])
        db = AsyncMock()
        db.get.return_value = object()
        listed = await router.list_reminder_configs(district_id, auth_for(district_id), db, repo)
        created = await router.create_reminder_config(
            district_id, payload(), auth_for(district_id), db, repo
        )
        assert listed[0].revision == revision_of(existing)
        assert created.revision

    @pytest.mark.asyncio
    @pytest.mark.parametrize("operation", ["update", "delete"])
    @pytest.mark.parametrize(("if_match", "status_code"), [(None, 428), ('"stale"', 412)])
    async def test_missing_or_stale_precondition_changes_nothing(
        self, operation, if_match, status_code
    ) -> None:
        district_id = uuid.uuid4()
        existing = persisted(district_id)
        repo = self._repo(existing)
        db = AsyncMock()
        db.get.return_value = object()
        with pytest.raises(HTTPException) as error:
            if operation == "update":
                await router.update_reminder_config(
                    district_id, existing.id, ReminderConfigUpdate(is_active=False),
                    auth_for(district_id), db, repo, if_match=if_match,
                )
            else:
                await router.deactivate_reminder_config(
                    district_id, existing.id, auth_for(district_id), db, repo, if_match=if_match,
                )
        assert error.value.status_code == status_code
        assert existing.is_active is True
        repo.save.assert_not_awaited()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_back_to_back_toggles_get_distinct_revisions(self) -> None:
        district_id = uuid.uuid4()
        existing = persisted(district_id)
        repo = self._repo(existing)
        db = AsyncMock()
        db.get.return_value = object()
        first = await router.update_reminder_config(
            district_id, existing.id, ReminderConfigUpdate(is_active=False),
            auth_for(district_id), db, repo, if_match=revision_of(existing),
        )
        repo.get_for_update.return_value = DistrictReminderConfig(
            **{**vars(existing), "is_active": False, "updated_at": repo.save.await_args.args[0].updated_at}
        )
        second = await router.update_reminder_config(
            district_id, existing.id, ReminderConfigUpdate(is_active=True),
            auth_for(district_id), db, repo, if_match=first.revision,
        )
        assert second.revision != first.revision

    @pytest.mark.asyncio
    async def test_permission_is_checked_before_the_lookup(self) -> None:
        district_id = uuid.uuid4()
        repo = self._repo(persisted(district_id))
        with pytest.raises(HTTPException) as error:
            await router.update_reminder_config(
                district_id, uuid.uuid4(), ReminderConfigUpdate(is_active=False),
                auth_for(uuid.uuid4()), AsyncMock(), repo,
            )
        assert error.value.status_code == 403
        repo.get_for_update.assert_not_awaited()
