# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.event_duty import AssignmentWrite, CategoryCreate
from app.application.event_duties import (
    DutyConflictError,
    DutyNotFoundError,
    EventDutiesService,
)
from app.domain.models.event_duty import (
    DutyNameSuggestion,
    EventDutyAssignment,
    EventDutyCategory,
    EventTypeDutyConfiguration,
    normalize_name,
)

_USE_STORED_ASSIGNMENT = object()


class Repository:
    def __init__(self):
        self.district, self.congregation, self.slot_id = uuid4(), uuid4(), uuid4()
        self.slot = SimpleNamespace(
            id=self.slot_id,
            district_id=self.district,
            congregation_id=self.congregation,
            category="Gottesdienst",
        )
        self.categories = EventDutyCategory.defaults(self.district)
        self.overrides, self.assignments, self.suggestions = [], [], []
        self.locks = []
        self.users = [{"sub": "verified", "display_name": "User Name"}]
        self.assignment_lock_result = _USE_STORED_ASSIGNMENT

    async def lock_slot(self, slot_id, district_id):
        self.locks.append("slot")
        return self.slot if (slot_id, district_id) == (self.slot_id, self.district) else None

    async def get_slot(self, slot_id, district_id):
        return self.slot if (slot_id, district_id) == (self.slot_id, self.district) else None

    async def lock_category(self, category_id, district_id):
        self.locks.append("category")
        return next(
            (
                category
                for category in self.categories
                if category.id == category_id and category.district_id == district_id
            ),
            None,
        )

    async def catalog(self, *args):
        return self.categories, self.overrides

    async def list_assignments(self, slot_ids):
        return self.assignments

    async def count_assignments(self, slot_id, category_id):
        return sum(
            assignment.planning_slot_id == slot_id and assignment.duty_category_id == category_id
            for assignment in self.assignments
        )

    async def eligible_users(self, *args):
        return self.users

    async def eligible_user_display_name(self, district, congregation, user_sub):
        return next(
            (user["display_name"] for user in self.users if user["sub"] == user_sub),
            None,
        )

    async def get_suggestion(self, suggestion_id):
        return next((s for s in self.suggestions if s.id == suggestion_id), None)

    async def get_assignment(self, assignment_id):
        return next((a for a in self.assignments if a.id == assignment_id), None)

    async def lock_assignment(self, assignment_id):
        self.locks.append("assignment")
        if self.assignment_lock_result is not _USE_STORED_ASSIGNMENT:
            return self.assignment_lock_result
        return await self.get_assignment(assignment_id)

    async def remember(self, district, congregation, category, name, activate=False):
        old = next(
            (
                s
                for s in self.suggestions
                if s.normalized_name == normalize_name(name)
                and s.congregation_id == congregation
                and s.duty_category_id == category
            ),
            None,
        )
        row = (
            replace(old, hidden=False)
            if old and activate
            else old
            or DutyNameSuggestion(
                uuid4(), district, congregation, category, name, normalize_name(name)
            )
        )
        if old:
            self.suggestions.remove(old)
        self.suggestions.append(row)
        return row

    async def save_assignment(self, assignment):
        self.assignments = [a for a in self.assignments if a.id != assignment.id] + [assignment]

    async def delete_assignment(self, assignment_id):
        self.assignments = [a for a in self.assignments if a.id != assignment_id]


async def add(repo, **kwargs):
    service = EventDutiesService(repo)
    replacing = kwargs.pop("replacing", None)
    revalidate = kwargs.pop("revalidate", False)
    if revalidate:
        return await service.revalidate(repo.district, repo.slot_id, replacing)
    if replacing:
        return await service.replace(
            repo.district, repo.slot_id, repo.categories[0].id, replacing, **kwargs
        )
    return await service.assign(repo.district, repo.slot_id, repo.categories[0].id, **kwargs)


@pytest.mark.asyncio
async def test_linked_identity_and_optional_name_snapshot():
    repo = Repository()
    row = await add(repo, linked_user_sub="verified")
    assert row.display_name == "User Name"
    assert row.normalized_name is None and repo.suggestions == []
    assert repo.locks == ["slot", "category"]


@pytest.mark.asyncio
async def test_name_identity_remembers_deduplicated_scoped_suggestion():
    repo = Repository()
    row = await add(repo, name=" Anna  Beispiel ")
    assert row.display_name == "Anna Beispiel" and row.linked_user_sub is None
    with pytest.raises(DutyConflictError):
        await add(repo, name="anna beispiel")
    assert len(repo.suggestions) == 1 and len(repo.assignments) == 1


@pytest.mark.asyncio
async def test_capacity_reduction_retains_old_rows_and_rejects_new():
    repo = Repository()
    repo.categories[0] = replace(repo.categories[0], capacity=2)
    await add(repo, name="Anna")
    await add(repo, name="Bob")
    repo.categories[0] = replace(repo.categories[0], capacity=1)
    with pytest.raises(DutyConflictError):
        await add(repo, name="Carla")
    assert len(repo.assignments) == 2


@pytest.mark.asyncio
async def test_reassignment_to_full_category_does_not_bypass_capacity():
    repo = Repository()
    source = await add(repo, name="Anna")
    destination = repo.categories[1]
    await EventDutiesService(repo).assign(repo.district, repo.slot_id, destination.id, name="Bob")

    with pytest.raises(DutyConflictError):
        await EventDutiesService(repo).replace(
            repo.district,
            repo.slot_id,
            destination.id,
            source,
            name="Anna",
        )

    assert len(repo.assignments) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("revalidate", [False, True])
async def test_deleted_assignment_is_not_recreated_by_replace_or_revalidation(revalidate):
    repo = Repository()
    row = await add(repo, name="Anna")
    repo.assignment_lock_result = None

    with pytest.raises(DutyNotFoundError):
        await add(repo, name="Anna", replacing=row, revalidate=revalidate)

    assert repo.assignments == [row]
    assert repo.locks[-2:] == ["slot", "assignment"]


@pytest.mark.asyncio
async def test_concurrently_changed_assignment_is_not_overwritten():
    repo = Repository()
    row = await add(repo, name="Anna")
    repo.assignment_lock_result = replace(
        row,
        display_name="Bereits geändert",
        normalized_name="bereits geändert",
    )

    with pytest.raises(DutyConflictError, match="changed concurrently"):
        await add(repo, name="Noch eine Änderung", replacing=row)

    assert repo.assignments == [row]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind",
    [
        "foreign_slot",
        "unknown_category",
        "disabled",
        "wrong_event",
        "foreign_user",
        "both",
        "neither",
    ],
)
async def test_invalid_assignments_never_write(kind):
    repo = Repository()
    category = repo.categories[0].id
    kwargs = {"name": "Anna"}
    slot = repo.slot_id
    if kind == "foreign_slot":
        slot = uuid4()
    if kind == "unknown_category":
        category = uuid4()
    if kind == "disabled":
        repo.categories[0] = replace(repo.categories[0], enabled=False)
    if kind == "wrong_event":
        repo.categories[0] = replace(repo.categories[0], event_categories=("Other",))
    if kind == "foreign_user":
        kwargs = {"linked_user_sub": "forged"}
    if kind == "both":
        kwargs = {"name": "Anna", "linked_user_sub": "verified"}
    if kind == "neither":
        kwargs = {}
    with pytest.raises((DutyNotFoundError, ValueError)):
        await EventDutiesService(repo).assign(repo.district, slot, category, **kwargs)
    assert repo.assignments == [] and repo.suggestions == []


@pytest.mark.asyncio
async def test_quarantined_replacement_denied_explicit_revalidation_preserves_snapshots():
    repo = Repository()
    row = await add(repo, name="Anna")
    repo.slot.congregation_id = uuid4()
    with pytest.raises(DutyNotFoundError):
        await add(repo, name="Bob", replacing=row)
    result = await add(repo, name="Anna", replacing=row, revalidate=True)
    assert result.id == row.id and result.display_name == row.display_name
    assert result.visible_in(repo.district, repo.slot.congregation_id)


@pytest.mark.asyncio
async def test_suppressed_suggestion_stays_hidden_on_resave_but_deliberate_add_restores():
    repo = Repository()
    row = await add(repo, name="Anna")
    repo.suggestions[0] = replace(repo.suggestions[0], hidden=True)
    await add(repo, name="Anna", replacing=row)
    assert repo.suggestions[0].hidden
    repo.assignments = []
    await add(repo, name="Anna")
    assert not repo.suggestions[0].hidden and len(repo.suggestions) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["scope", "category", "hidden", "name"])
async def test_suggestion_references_are_scoped_and_active(change):
    repo = Repository()
    suggestion = await repo.remember(
        repo.district, repo.congregation, repo.categories[0].id, "Anna"
    )
    changes = {
        "scope": {"congregation_id": uuid4()},
        "category": {"duty_category_id": uuid4()},
        "hidden": {"hidden": True},
        "name": {},
    }
    repo.suggestions[0] = replace(suggestion, **changes[change])
    with pytest.raises(DutyNotFoundError):
        await add(repo, name="Bob" if change == "name" else "Anna", suggestion_id=suggestion.id)
    assert repo.assignments == []


def test_schema_exclusivity_and_positive_capacity():
    for kwargs in (
        {},
        {"name": "  "},
        {"name": "Anna", "linked_user_sub": "verified"},
        {"linked_user_sub": "verified", "suggestion_id": uuid4()},
    ):
        with pytest.raises(ValidationError):
            AssignmentWrite(duty_category_id=uuid4(), **kwargs)
    with pytest.raises(ValidationError):
        CategoryCreate(code="test", label="Test", capacity=0)


@pytest.mark.parametrize("label", ["   ", "Valid\u0000Label"])
def test_category_labels_reject_blank_or_control_characters(label):
    with pytest.raises(ValidationError):
        CategoryCreate(code="test", label=label)


def test_event_category_values_are_bounded_before_persistence():
    from app.adapters.api.schemas.event_duty import CategoryUpdate, ConfigurationWrite

    too_long = "x" * 256
    with pytest.raises(ValidationError):
        CategoryCreate(code="test", label="Test", event_categories=[too_long])
    with pytest.raises(ValidationError):
        CategoryUpdate(event_categories=[too_long])
    with pytest.raises(ValidationError):
        ConfigurationWrite(
            congregation_id=uuid4(),
            duty_category_id=uuid4(),
            event_categories=[too_long],
        )


def test_category_update_rejects_explicit_null_but_allows_omission():
    from app.adapters.api.schemas.event_duty import CategoryUpdate

    assert CategoryUpdate().model_fields_set == set()
    with pytest.raises(ValidationError):
        CategoryUpdate(event_categories=None)


def test_overrides_are_exact_and_district_events_ignore_local_config():
    from app.domain.models.event_duty import effective_categories

    repo = Repository()
    override = EventTypeDutyConfiguration(
        uuid4(), repo.district, repo.congregation, repo.categories[1].id, (), False, 2
    )
    assert (
        len(effective_categories(repo.categories, [override], "Gottesdienst", repo.congregation))
        == 2
    )
    assert len(effective_categories(repo.categories, [override], "Gottesdienst", None)) == 3
    with pytest.raises(ValueError):
        replace(override, capacity=0)
