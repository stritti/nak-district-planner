# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Event hook endpoints: RBAC, district isolation, validation and soft delete."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.routers import event_hooks as router
from app.adapters.api.schemas.event_hooks import EventHookCreate, EventHookUpdate
from app.domain.events import EventType
from app.domain.models.event_mail_hook import EVENT_PLACEHOLDERS, EventMailHook
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role

DISTRICT = uuid.uuid4()


def auth_for(district_id: uuid.UUID, role: Role = Role.DISTRICT_ADMIN, superadmin=False):
    return SimpleNamespace(
        user_sub="admin",
        user=SimpleNamespace(is_superadmin=superadmin),
        memberships=[
            Membership.create(
                user_sub="admin", role=role, scope_type=ScopeType.DISTRICT, scope_id=district_id
            )
        ],
    )


def create_body(**overrides) -> EventHookCreate:
    values = {
        "event_type": EventType.SYNC_ERROR,
        "recipient_role": Role.PLANNER,
        "subject_template": "Sync-Fehler: {integration_name}",
        "body_template": "{error_message} ({timestamp})",
    }
    return EventHookCreate(**{**values, **overrides})


def update_body(**overrides) -> EventHookUpdate:
    values = {
        "recipient_role": Role.DISTRICT_ADMIN,
        "subject_template": "Fehler in {district_name}",
        "body_template": "{error_message}",
        "is_active": True,
    }
    return EventHookUpdate(**{**values, **overrides})


def existing_hook(district_id: uuid.UUID = DISTRICT) -> EventMailHook:
    return EventMailHook(district_id=district_id, **create_body().model_dump())


@pytest.fixture
def db() -> AsyncMock:
    database = AsyncMock()
    database.get.return_value = object()
    return database


@pytest.fixture
def repo() -> AsyncMock:
    repository = AsyncMock()
    repository.save = AsyncMock()
    repository.get = AsyncMock(return_value=None)
    repository.list_by_district = AsyncMock(return_value=[])
    return repository


class TestAuthorization:
    @pytest.mark.parametrize(
        "auth",
        [auth_for(uuid.uuid4()), auth_for(DISTRICT, Role.PLANNER)],
        ids=["other-district-admin", "planner-in-district"],
    )
    async def test_non_admins_are_rejected_before_any_lookup(self, auth, db, repo) -> None:
        with pytest.raises(HTTPException) as error:
            await router.list_event_hooks(DISTRICT, auth, db, repo)
        assert error.value.status_code == 403
        db.get.assert_not_awaited()
        repo.list_by_district.assert_not_awaited()

    async def test_superadmin_is_allowed(self, db, repo) -> None:
        assert (
            await router.list_event_hooks(DISTRICT, auth_for(uuid.uuid4(), superadmin=True), db, repo)
            == []
        )

    async def test_unknown_district_returns_404(self, db, repo) -> None:
        db.get.return_value = None
        with pytest.raises(HTTPException) as error:
            await router.list_event_hooks(DISTRICT, auth_for(DISTRICT), db, repo)
        assert error.value.status_code == 404
        repo.list_by_district.assert_not_awaited()


class TestCrud:
    async def test_create_persists_active_hook(self, db, repo) -> None:
        hook = await router.create_event_hook(DISTRICT, create_body(), auth_for(DISTRICT), db, repo)

        assert hook.district_id == DISTRICT
        assert hook.is_active
        assert hook.recipient_role == Role.PLANNER
        repo.save.assert_awaited_once_with(hook)

    async def test_create_rejects_placeholder_of_other_event_type(self, db, repo) -> None:
        with pytest.raises(HTTPException) as error:
            await router.create_event_hook(
                DISTRICT,
                create_body(body_template="{leader_name}"),
                auth_for(DISTRICT),
                db,
                repo,
            )
        assert error.value.status_code == 422
        repo.save.assert_not_awaited()

    async def test_list_returns_district_hooks(self, db, repo) -> None:
        hooks = [existing_hook()]
        repo.list_by_district.return_value = hooks
        assert await router.list_event_hooks(DISTRICT, auth_for(DISTRICT), db, repo) == hooks
        repo.list_by_district.assert_awaited_once_with(DISTRICT)

    async def test_update_replaces_mutable_fields_and_keeps_identity(self, db, repo) -> None:
        hook = existing_hook()
        repo.get.return_value = hook

        updated = await router.update_event_hook(
            DISTRICT, hook.id, update_body(is_active=False), auth_for(DISTRICT), db, repo
        )

        assert updated.id == hook.id and updated.event_type == hook.event_type
        assert updated.recipient_role == Role.DISTRICT_ADMIN
        assert not updated.is_active
        repo.get.assert_awaited_once_with(DISTRICT, hook.id)
        repo.save.assert_awaited_once_with(updated)

    async def test_update_rejects_invalid_template(self, db, repo) -> None:
        repo.get.return_value = existing_hook()
        with pytest.raises(HTTPException) as error:
            await router.update_event_hook(
                DISTRICT,
                uuid.uuid4(),
                update_body(subject_template="{x.__class__}"),
                auth_for(DISTRICT),
                db,
                repo,
            )
        assert error.value.status_code == 422

    @pytest.mark.parametrize("operation", ["update", "delete"])
    async def test_hook_of_other_district_is_not_found(self, operation, db, repo) -> None:
        repo.get.return_value = None
        with pytest.raises(HTTPException) as error:
            if operation == "update":
                await router.update_event_hook(
                    DISTRICT, uuid.uuid4(), update_body(), auth_for(DISTRICT), db, repo
                )
            else:
                await router.deactivate_event_hook(
                    DISTRICT, uuid.uuid4(), auth_for(DISTRICT), db, repo
                )
        assert error.value.status_code == 404
        repo.save.assert_not_awaited()

    async def test_delete_is_soft(self, db, repo) -> None:
        hook = existing_hook()
        repo.get.return_value = hook

        response = await router.deactivate_event_hook(
            DISTRICT, hook.id, auth_for(DISTRICT), db, repo
        )

        assert response.status_code == 204
        saved = repo.save.await_args.args[0]
        assert saved.id == hook.id and not saved.is_active


async def test_event_types_list_placeholders_for_editor(db) -> None:
    types = await router.list_event_types(DISTRICT, auth_for(DISTRICT), db)
    assert {t.event_type for t in types} == set(EventType)
    sync_error = next(t for t in types if t.event_type == EventType.SYNC_ERROR)
    assert sync_error.placeholders == sorted(EVENT_PLACEHOLDERS[EventType.SYNC_ERROR])


@pytest.mark.parametrize(
    "overrides",
    [
        {"event_type": "UNKNOWN"},
        {"recipient_role": "OWNER"},
        {"subject_template": ""},
        {"extra": 1},
    ],
    ids=["unknown-event-type", "unknown-role", "empty-subject", "unknown-field"],
)
def test_create_schema_rejects_invalid_input(overrides) -> None:
    values = {
        "event_type": "SYNC_ERROR",
        "recipient_role": "PLANNER",
        "subject_template": "s",
        "body_template": "b",
        **overrides,
    }
    with pytest.raises(ValidationError):
        EventHookCreate.model_validate(values)
