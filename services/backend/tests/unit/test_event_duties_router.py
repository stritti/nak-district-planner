# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.adapters.api.routers import event_duties as api
from app.adapters.api.schemas.event_duty import (
    AssignmentWrite,
    CategoryCreate,
    ConfigurationWrite,
    SuggestionUpdate,
    SuggestionWrite,
)
from app.domain.models.event_duty import DutyNameSuggestion, EventDutyAssignment
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role
from tests.unit.test_event_duties_service import Repository


def auth(repo, role=Role.PLANNER, congregation=None, district=False):
    return SimpleNamespace(
        user_sub="actor",
        user=SimpleNamespace(is_superadmin=False),
        memberships=[
            Membership.create(
                user_sub="actor",
                role=role,
                scope_type=ScopeType.DISTRICT if district else ScopeType.CONGREGATION,
                scope_id=repo.district if district else congregation or repo.congregation,
            )
        ],
    )


@pytest.fixture
def setup(monkeypatch):
    repo = Repository()
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=repo.slot),
        get=AsyncMock(),
        add=lambda x: None,
        flush=AsyncMock(),
        execute=AsyncMock(),
        scalars=AsyncMock(),
    )
    monkeypatch.setattr(api, "ensure_congregation_in_district", AsyncMock())
    repo.save_category = AsyncMock(side_effect=lambda category: category)
    repo.save_configuration = AsyncMock(side_effect=lambda configuration: configuration)
    repo.delete_configuration = AsyncMock()
    repo.list_suggestions = AsyncMock(
        side_effect=lambda district, congregation, category: repo.suggestions
    )
    repo.save_suggestion = AsyncMock(side_effect=lambda suggestion: suggestion)
    return repo, db


@pytest.mark.asyncio
async def test_assignment_router_connects_validated_input_to_service(setup):
    repo, db = setup
    result = await api.assign(
        repo.district,
        repo.slot_id,
        AssignmentWrite(duty_category_id=repo.categories[0].id, name="Anna"),
        auth(repo),
        db,
        repository=repo,
    )
    assert result["display_name"] == "Anna" and len(repo.assignments) == 1


@pytest.mark.asyncio
async def test_viewer_cannot_modify_assignment(setup):
    repo, db = setup
    with pytest.raises(HTTPException) as error:
        await api.assign(
            repo.district,
            repo.slot_id,
            AssignmentWrite(duty_category_id=repo.categories[0].id, name="Anna"),
            auth(repo, Role.VIEWER),
            db,
            repository=repo,
        )
    assert error.value.status_code == 403 and repo.assignments == []


@pytest.mark.asyncio
async def test_assignment_authorization_uses_locked_current_slot_scope(setup):
    repo, db = setup
    repo.slot.congregation_id = uuid4()

    with pytest.raises(HTTPException) as error:
        await api.assign(
            repo.district,
            repo.slot_id,
            AssignmentWrite(duty_category_id=repo.categories[0].id, name="Anna"),
            auth(repo),
            db,
            repository=repo,
        )

    assert error.value.status_code == 403
    assert repo.assignments == []


@pytest.mark.asyncio
async def test_assignment_delete_rechecks_locked_current_slot_scope(setup):
    repo, db = setup
    row = EventDutyAssignment.create(repo.slot_id, repo.categories[0], repo.congregation, "Anna")
    repo.assignments.append(row)
    repo.slot.congregation_id = uuid4()

    with pytest.raises(HTTPException) as error:
        await api.remove_assignment(repo.district, row.id, auth(repo), db, repository=repo)

    assert error.value.status_code == 403
    assert repo.assignments == [row]


@pytest.mark.asyncio
async def test_assignment_delete_does_not_restore_or_remove_a_concurrently_deleted_row(setup):
    repo, db = setup
    row = EventDutyAssignment.create(repo.slot_id, repo.categories[0], repo.congregation, "Anna")
    repo.assignments.append(row)
    repo.assignment_lock_result = None

    with pytest.raises(HTTPException) as error:
        await api.remove_assignment(repo.district, row.id, auth(repo), db, repository=repo)

    assert error.value.status_code == 404
    assert repo.assignments == [row]


@pytest.mark.asyncio
async def test_assignment_delete_uses_the_locked_current_row(setup):
    repo, db = setup
    row = EventDutyAssignment.create(repo.slot_id, repo.categories[0], repo.congregation, "Anna")
    repo.assignments.append(row)

    await api.remove_assignment(repo.district, row.id, auth(repo), db, repository=repo)

    assert repo.assignments == []
    assert repo.locks[-2:] == ["slot", "assignment"]


@pytest.mark.asyncio
async def test_assignment_delete_rejects_a_concurrently_changed_row(setup):
    repo, db = setup
    row = EventDutyAssignment.create(repo.slot_id, repo.categories[0], repo.congregation, "Anna")
    repo.assignments.append(row)
    repo.assignment_lock_result = replace(
        row,
        display_name="Bereits geändert",
        normalized_name="bereits geändert",
    )

    with pytest.raises(HTTPException) as error:
        await api.remove_assignment(repo.district, row.id, auth(repo), db, repository=repo)

    assert error.value.status_code == 409
    assert repo.assignments == [row]


@pytest.mark.asyncio
async def test_destination_views_cannot_disclose_quarantined_snapshots(setup):
    repo, db = setup
    row = EventDutyAssignment.create(repo.slot_id, repo.categories[0], uuid4(), "Secret Old Name")
    repo.assignments.append(row)
    result = await api.assignments(repo.district, repo.slot_id, auth(repo), db, repository=repo)
    assert result["assignments"] == []
    result = await api.assignments(
        repo.district,
        repo.slot_id,
        auth(repo),
        db,
        include_quarantined=True,
        repository=repo,
    )
    assert result["assignments"] == []
    admin = auth(repo, Role.DISTRICT_ADMIN, district=True)
    result = await api.assignments(
        repo.district,
        repo.slot_id,
        admin,
        db,
        include_quarantined=True,
        repository=repo,
    )
    assert result["assignments"][0]["display_name"] == "Secret Old Name"
    assert result["assignments"][0]["needs_review"]
    assert result["assignments"][0]["quarantined"]


@pytest.mark.asyncio
async def test_capacity_and_inapplicability_flag_historical_rows(setup):
    repo, db = setup
    repo.assignments = [
        EventDutyAssignment.create(repo.slot_id, repo.categories[0], repo.congregation, name)
        for name in ["Anna", "Bob"]
    ]
    result = await api.assignments(repo.district, repo.slot_id, auth(repo), db, repository=repo)
    assert all(a["over_capacity"] for a in result["assignments"])
    repo.categories[0] = replace(repo.categories[0], enabled=False)
    result = await api.assignments(repo.district, repo.slot_id, auth(repo), db, repository=repo)
    assert all(a["needs_review"] for a in result["assignments"])


@pytest.mark.asyncio
async def test_visible_assignment_counts_quarantined_rows_for_capacity(setup):
    repo, db = setup
    repo.assignments = [
        EventDutyAssignment.create(repo.slot_id, repo.categories[0], uuid4(), "Quarantined"),
        EventDutyAssignment.create(repo.slot_id, repo.categories[0], repo.congregation, "Visible"),
    ]

    result = await api.assignments(
        repo.district,
        repo.slot_id,
        auth(repo),
        db,
        repository=repo,
    )

    assert [assignment["display_name"] for assignment in result["assignments"]] == ["Visible"]
    assert result["assignments"][0]["over_capacity"] is True


@pytest.mark.asyncio
async def test_dual_scope_permission_required_before_revalidation(setup):
    repo, db = setup
    old_congregation = uuid4()
    row = EventDutyAssignment.create(repo.slot_id, repo.categories[0], old_congregation, "Anna")
    repo.assignments.append(row)
    with pytest.raises(HTTPException) as error:
        await api.revalidate_assignment(repo.district, row.id, auth(repo), db, repository=repo)
    assert error.value.status_code == 403
    result = await api.revalidate_assignment(
        repo.district,
        row.id,
        auth(repo, Role.DISTRICT_ADMIN, district=True),
        db,
        repository=repo,
    )
    assert result["congregation_id"] == repo.congregation


@pytest.mark.asyncio
async def test_category_management_has_separate_admin_scopes(setup):
    repo, db = setup
    body = CategoryCreate(code="custom", label="Custom")
    with pytest.raises(HTTPException) as error:
        await api.create_category(
            repo.district,
            body,
            auth(repo, Role.CONGREGATION_ADMIN),
            db,
            repository=repo,
        )
    assert error.value.status_code == 403
    await api.create_category(
        repo.district,
        body,
        auth(repo, Role.DISTRICT_ADMIN, district=True),
        db,
        repository=repo,
    )
    local = CategoryCreate(code="custom", label="Custom", congregation_id=repo.congregation)
    await api.create_category(
        repo.district,
        local,
        auth(repo, Role.CONGREGATION_ADMIN),
        db,
        repository=repo,
    )


@pytest.mark.asyncio
async def test_duplicate_category_code_returns_conflict(setup):
    repo, db = setup
    repo.save_category.side_effect = IntegrityError("insert", {}, Exception("duplicate"))

    with pytest.raises(HTTPException) as error:
        await api.create_category(
            repo.district,
            CategoryCreate(code="duplicate", label="Duplicate"),
            auth(repo, Role.DISTRICT_ADMIN, district=True),
            db,
            repository=repo,
        )

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_unknown_and_foreign_assignment_ids_are_identical(setup):
    repo, _db = setup
    for row in [None, SimpleNamespace(district_id=uuid4())]:
        repo.get_assignment = AsyncMock(return_value=row)
        with pytest.raises(HTTPException) as error:
            await api.assignment_for(repo, auth(repo), repo.district, uuid4())
        assert (error.value.status_code, error.value.detail) == (404, "Reference not found")


@pytest.mark.asyncio
async def test_suggestion_hiding_requires_scope_planner(setup):
    repo, db = setup
    suggestion = DutyNameSuggestion(
        uuid4(), repo.district, repo.congregation, repo.categories[0].id, "Anna", "anna"
    )
    repo.suggestions.append(suggestion)
    with pytest.raises(HTTPException) as error:
        await api.suppress(
            repo.district,
            suggestion.id,
            SuggestionUpdate(hidden=True),
            auth(repo, Role.VIEWER),
            db,
            repository=repo,
        )
    assert error.value.status_code == 403
    result = await api.suppress(
        repo.district,
        suggestion.id,
        SuggestionUpdate(hidden=True),
        auth(repo),
        db,
        repository=repo,
    )
    assert result["hidden"]


@pytest.mark.asyncio
async def test_suggestion_manual_add_checks_category_and_normalizes(setup):
    repo, db = setup
    with pytest.raises(HTTPException) as error:
        await api.remember(
            repo.district,
            SuggestionWrite(duty_category_id=uuid4(), name="Anna"),
            auth(repo, district=True),
            db,
            repository=repo,
        )
    assert error.value.status_code == 404
    result = await api.remember(
        repo.district,
        SuggestionWrite(
            congregation_id=repo.congregation,
            duty_category_id=repo.categories[0].id,
            name=" Anna  Beispiel ",
        ),
        auth(repo),
        db,
        repository=repo,
    )
    assert result["normalized_name"] == "anna beispiel"


@pytest.mark.asyncio
async def test_linked_user_picker_requires_scope_planner(setup):
    repo, db = setup
    assert (
        await api.eligible_users(
            repo.district,
            auth(repo),
            db,
            repo.congregation,
            repository=repo,
        )
        == repo.users
    )
    with pytest.raises(HTTPException) as error:
        await api.eligible_users(
            repo.district,
            auth(repo, Role.VIEWER),
            db,
            repo.congregation,
            repository=repo,
        )
    assert error.value.status_code == 403
