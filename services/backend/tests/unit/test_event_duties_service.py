# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.event_duty import AssignmentWrite, CategoryCreate
from app.application.event_duties import (
    DutyConflictError,
    DutyIdentityConflictError,
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
from app.domain.models.leader import Leader, LeaderRank
from app.domain.planning.conflict_result import ScheduledService, Severity
from app.domain.planning.duty_conflicts import ScheduledDuty

_USE_STORED_ASSIGNMENT = object()


class Repository:
    def __init__(self):
        self.district, self.congregation, self.slot_id = uuid4(), uuid4(), uuid4()
        self.slot = SimpleNamespace(
            id=self.slot_id,
            district_id=self.district,
            congregation_id=self.congregation,
            category="Gottesdienst",
            planning_date=date(2026, 11, 1),
        )
        self.categories = EventDutyCategory.defaults(self.district)
        self.overrides, self.assignments, self.suggestions = [], [], []
        self.locks = []
        self.identity_schedule, self.identity_queries = [], []
        self.leaders = {}
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

    async def list_leaders(self, district_id):
        return [leader for leader in self.leaders.values() if leader.district_id == district_id]

    async def lock_leader(self, leader_id):
        self.locks.append("leader")

    async def lock_account(self, user_sub):
        self.locks.append(f"account:{user_sub}")

    async def get_leader(self, district_id, leader_id):
        leader = self.leaders.get(leader_id)
        return leader if leader is not None and leader.district_id == district_id else None

    async def slot_schedule(self, slot_id):
        return ScheduledService(
            self.congregation, date(2026, 11, 1), time(9, 0), None, None
        )

    async def list_identity_schedule(self, district_id, **query):
        self.identity_queries.append(query)
        return self.identity_schedule

    async def lock_suggestion(self, suggestion_id):
        self.locks.append("suggestion")
        return await self.get_suggestion(suggestion_id)

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
    # The account lock a service of the leader linked to this account takes as well.
    assert repo.locks == ["slot", "category", "account:verified"]


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


@pytest.mark.asyncio
async def test_scope_change_preview_counts_only_newly_flagged_duties():
    repo = Repository()
    service = EventDutiesService(repo)
    category = next(c for c in repo.categories if "Gottesdienst" in c.event_categories)
    repo.assignments = [
        EventDutyAssignment.create(repo.slot_id, category, repo.congregation, name="Anna"),
    ]

    unchanged = await service.preview_scope_change(
        repo.district, repo.slot, category="Gottesdienst", congregation_id=repo.congregation
    )
    assert (unchanged.newly_flagged, unchanged.flagged_after) == (0, 0)

    moved = await service.preview_scope_change(
        repo.district, repo.slot, category="Gottesdienst", congregation_id=uuid4()
    )
    assert (moved.newly_flagged, moved.flagged_after) == (1, 1)
    assert (moved.newly_quarantined, moved.quarantined_after) == (1, 1)

    recategorised = await service.preview_scope_change(
        repo.district, repo.slot, category="Feiertag", congregation_id=repo.congregation
    )
    assert recategorised.newly_flagged == 1
    assert (recategorised.newly_quarantined, recategorised.quarantined_after) == (0, 0)


@pytest.mark.asyncio
async def test_scope_change_preview_does_not_recount_already_flagged_duties():
    repo = Repository()
    service = EventDutiesService(repo)
    category = next(c for c in repo.categories if "Gottesdienst" in c.event_categories)
    foreign = replace(
        EventDutyAssignment.create(repo.slot_id, category, uuid4(), name="Berta"),
    )
    repo.assignments = [foreign]  # already quarantined: owned by another scope

    impact = await service.preview_scope_change(
        repo.district, repo.slot, category="Feiertag", congregation_id=repo.congregation
    )
    assert impact.newly_flagged == 0
    assert impact.flagged_after == 1


@pytest.mark.asyncio
async def test_scope_change_preview_reports_quarantine_of_already_flagged_duty():
    """A duty already in review that is additionally hidden by a move is a new quarantine."""
    repo = Repository()
    service = EventDutiesService(repo)
    category = next(c for c in repo.categories if "Gottesdienst" in c.event_categories)
    repo.slot.category = "Feiertag"  # organist is not offered for this category: already flagged
    repo.assignments = [
        EventDutyAssignment.create(repo.slot_id, category, repo.congregation, name="Anna"),
    ]

    impact = await service.preview_scope_change(
        repo.district, repo.slot, category="Feiertag", congregation_id=uuid4()
    )
    assert impact.newly_flagged == 0
    assert impact.newly_quarantined == 1
    assert impact.quarantined_after == 1


def _overlapping(repo, *, strong, offset=30):
    start = datetime(2026, 11, 1, 9, 0, tzinfo=UTC) + timedelta(minutes=offset)
    return ScheduledDuty(uuid4(), uuid4(), start, start + timedelta(minutes=90), strong)


@pytest.mark.asyncio
async def test_a_verified_identity_with_an_overlapping_duty_is_blocked():
    repo = Repository()
    repo.identity_schedule = [_overlapping(repo, strong=True)]
    with pytest.raises(DutyIdentityConflictError) as error:
        await EventDutiesService(repo).assign(
            repo.district, repo.slot_id, repo.categories[0].id, linked_user_sub="verified"
        )
    assert [c.severity for c in error.value.conflicts] == [Severity.BLOCK]
    assert repo.assignments == []
    assert repo.identity_queries[0]["linked_user_sub"] == "verified"
    assert repo.identity_queries[0]["exclude_slot_id"] == repo.slot_id


@pytest.mark.asyncio
async def test_a_name_match_warns_until_it_is_confirmed():
    repo = Repository()
    repo.identity_schedule = [_overlapping(repo, strong=False)]
    service = EventDutiesService(repo)
    with pytest.raises(DutyIdentityConflictError) as error:
        await service.assign(repo.district, repo.slot_id, repo.categories[0].id, name="Anna")
    assert [c.severity for c in error.value.conflicts] == [Severity.WARN]
    assert repo.assignments == []
    saved = await service.assign(
        repo.district, repo.slot_id, repo.categories[0].id, name="Anna", confirm_warnings=True
    )
    assert repo.assignments == [saved]
    assert repo.identity_queries[-1]["normalized_name"] == "anna"


@pytest.mark.asyncio
async def test_a_block_cannot_be_confirmed_away():
    repo = Repository()
    repo.identity_schedule = [_overlapping(repo, strong=True), _overlapping(repo, strong=False)]
    with pytest.raises(DutyIdentityConflictError):
        await EventDutiesService(repo).assign(
            repo.district, repo.slot_id, repo.categories[0].id, linked_user_sub="verified",
            confirm_warnings=True,
        )
    assert repo.assignments == []


@pytest.mark.asyncio
async def test_replace_checks_the_new_identity():
    repo = Repository()
    row = EventDutyAssignment.create(repo.slot_id, repo.categories[0], repo.congregation, "Anna")
    repo.assignments.append(row)
    repo.identity_schedule = [_overlapping(repo, strong=False)]
    with pytest.raises(DutyIdentityConflictError):
        await EventDutiesService(repo).replace(
            repo.district, repo.slot_id, repo.categories[0].id, row, name="Berta"
        )
    assert repo.assignments == [row]


@pytest.mark.asyncio
async def test_no_overlap_and_a_disabled_check_assign_normally(monkeypatch):
    repo = Repository()
    saved = await EventDutiesService(repo).assign(
        repo.district, repo.slot_id, repo.categories[0].id, name="Anna"
    )
    assert repo.assignments == [saved]
    repo2 = Repository()
    repo2.identity_schedule = [_overlapping(repo2, strong=True)]
    monkeypatch.setattr("app.application.event_duties.settings.conflict_check_enabled", False)
    await EventDutiesService(repo2).assign(
        repo2.district, repo2.slot_id, repo2.categories[0].id, linked_user_sub="verified"
    )
    assert len(repo2.assignments) == 1 and repo2.identity_queries == []


def _leader(repo, **overrides):
    leader = Leader.create(
        name="Hans Müller", district_id=repo.district, rank=LeaderRank.EVANGELIST,
        user_sub="leader-account", **overrides,
    )
    repo.leaders[leader.id] = leader
    return leader


@pytest.mark.asyncio
async def test_a_duty_can_reference_an_existing_leader():
    repo = Repository()
    leader = _leader(repo)
    saved = await EventDutiesService(repo).assign(
        repo.district, repo.slot_id, repo.categories[0].id, leader_id=leader.id
    )
    assert saved.leader_id == leader.id
    assert saved.display_name == "Ev. Hans Müller"
    assert saved.linked_user_sub is None and saved.normalized_name is None
    assert repo.assignments == [saved]
    # No typed name is remembered for a leader, and the overlap lookup carries all identities.
    query = repo.identity_queries[0]
    assert query["leader_id"] == leader.id
    assert query["linked_user_sub"] == "leader-account"
    assert query["normalized_name"] == "hans müller"
    # The per-leader lock that service assignments take, after the slot lock (same order).
    assert repo.locks == ["slot", "category", "leader", "account:leader-account"]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["unknown", "other_district", "retired", "inactive"])
async def test_an_unusable_leader_is_a_plain_not_found(case):
    from datetime import date as _date

    repo = Repository()
    leader = _leader(repo)
    leader_id = leader.id
    if case == "unknown":
        leader_id = uuid4()
    elif case == "other_district":
        repo.leaders[leader.id] = replace(leader, district_id=uuid4())
    elif case == "retired":
        repo.leaders[leader.id] = replace(leader, service_end_date=_date(2020, 1, 1))
    else:
        repo.leaders[leader.id] = replace(leader, is_active=False)
    with pytest.raises(DutyNotFoundError):
        await EventDutiesService(repo).assign(
            repo.district, repo.slot_id, repo.categories[0].id, leader_id=leader_id
        )
    assert repo.assignments == []


@pytest.mark.asyncio
async def test_the_same_leader_cannot_hold_the_same_duty_twice():
    repo = Repository()
    repo.categories[0] = replace(repo.categories[0], capacity=2)
    leader = _leader(repo)
    service = EventDutiesService(repo)
    await service.assign(repo.district, repo.slot_id, repo.categories[0].id, leader_id=leader.id)
    with pytest.raises(DutyConflictError):
        await service.assign(
            repo.district, repo.slot_id, repo.categories[0].id, leader_id=leader.id
        )


@pytest.mark.asyncio
async def test_a_leaders_overlapping_service_blocks_the_duty():
    repo = Repository()
    leader = _leader(repo)
    repo.identity_schedule = [_overlapping(repo, strong=True)]
    with pytest.raises(DutyIdentityConflictError) as error:
        await EventDutiesService(repo).assign(
            repo.district, repo.slot_id, repo.categories[0].id, leader_id=leader.id
        )
    assert [c.severity for c in error.value.conflicts] == [Severity.BLOCK]
    assert repo.assignments == []


@pytest.mark.asyncio
async def test_replacing_with_a_leader_and_revalidating_keep_the_leader_identity():
    repo = Repository()
    leader = _leader(repo)
    row = EventDutyAssignment.create(repo.slot_id, repo.categories[0], repo.congregation, "Anna")
    repo.assignments.append(row)
    service = EventDutiesService(repo)
    replaced = await service.replace(
        repo.district, repo.slot_id, repo.categories[0].id, row, leader_id=leader.id
    )
    assert replaced.leader_id == leader.id and replaced.normalized_name is None
    repo.assignments[:] = [replaced]
    again = await service.revalidate(repo.district, repo.slot_id, replaced)
    assert again.leader_id == leader.id and again.id == replaced.id


def test_assignment_identity_is_exactly_one_of_name_account_or_leader():
    category = EventDutyCategory.defaults(uuid4())[0]
    slot_id, leader_id = uuid4(), uuid4()
    leader_row = EventDutyAssignment.create(
        slot_id, category, None, leader_id=leader_id, leader_display_name="Ev. Hans"
    )
    assert leader_row.leader_id == leader_id and leader_row.normalized_name is None
    for kwargs in (
        {"name": "A", "leader_id": leader_id, "leader_display_name": "L"},
        {"linked_user_sub": "s", "leader_id": leader_id, "leader_display_name": "L"},
        {},
    ):
        with pytest.raises(ValueError):
            EventDutyAssignment.create(slot_id, category, None, **kwargs)


@pytest.mark.parametrize(
    "extra",
    [{"name": "A"}, {"linked_user_sub": "s"}, {}, {"suggestion_id": uuid4()}],
    ids=["with-name", "with-account", "no-extra-but-suggestion-less", "with-suggestion"],
)
def test_the_write_schema_accepts_a_leader_only_alone(extra):
    base = {"duty_category_id": uuid4(), "leader_id": uuid4()}
    if extra == {}:
        assert AssignmentWrite(**base).leader_id
    else:
        with pytest.raises(ValidationError):
            AssignmentWrite(**base, **extra)


@pytest.mark.asyncio
@pytest.mark.parametrize("first", ["account", "leader"])
async def test_one_person_cannot_hold_the_same_duty_as_account_and_as_leader(first):
    """The leader's linked account and the leader record are the same person (capacity 2)."""
    repo = Repository()
    repo.categories[0] = replace(repo.categories[0], capacity=2)
    leader = _leader(repo)  # user_sub="leader-account"
    repo.users = [{"sub": "leader-account", "display_name": "Hans Müller"}]
    service = EventDutiesService(repo)
    account = {"linked_user_sub": "leader-account"}
    as_leader = {"leader_id": leader.id}
    one, other = (account, as_leader) if first == "account" else (as_leader, account)

    await service.assign(repo.district, repo.slot_id, repo.categories[0].id, **one)
    with pytest.raises(DutyConflictError):
        await service.assign(repo.district, repo.slot_id, repo.categories[0].id, **other)
    assert len(repo.assignments) == 1


@pytest.mark.asyncio
async def test_different_people_may_share_a_duty_with_capacity_for_two():
    repo = Repository()
    repo.categories[0] = replace(repo.categories[0], capacity=2)
    leader = _leader(repo)
    repo.users = [{"sub": "someone-else", "display_name": "Anna"}]
    service = EventDutiesService(repo)
    await service.assign(repo.district, repo.slot_id, repo.categories[0].id, leader_id=leader.id)
    await service.assign(
        repo.district, repo.slot_id, repo.categories[0].id, linked_user_sub="someone-else"
    )
    assert len(repo.assignments) == 2

