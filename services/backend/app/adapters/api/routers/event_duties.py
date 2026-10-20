# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Scoped organisational duty administration and planner assignment APIs."""

from dataclasses import asdict, replace
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError

from app.adapters.api.conflict_http import raise_for_conflicts
from app.adapters.api.deps import (
    CurrentUserWithMemberships,
    DbSession,
    get_event_duties_repository,
)
from app.adapters.api.revisions import content_revision, require_current_revision
from app.adapters.api.schemas.event_duty import (
    AssignmentWrite,
    CategoryCreate,
    CategoryUpdate,
    ConfigurationWrite,
    SuggestionUpdate,
    SuggestionWrite,
)
from app.adapters.api.tenant_references import ensure_congregation_in_district
from app.adapters.auth.permissions import has_role_in_district, require_role_in_district
from app.application.event_duties import (
    DutyConflictError,
    DutyIdentityConflictError,
    DutyNotFoundError,
    EventDutiesService,
)
from app.domain.models.event_duty import EventDutyCategory, EventTypeDutyConfiguration
from app.domain.models.membership import ScopeType
from app.domain.models.role import Role
from app.domain.ports.event_duties import EventDutiesRepository

router = APIRouter(prefix="/api/v1/districts/{district_id}/duties", tags=["event-duties"])

IfMatch = Annotated[str | None, Header(alias="If-Match")]


def with_revision(entity) -> dict:
    return {**asdict(entity), "revision": content_revision(entity)}


def guard(auth, district_id, congregation_id, role):
    require_role_in_district(
        auth, role, district_id, {congregation_id} if congregation_id else None
    )


async def scope(db, auth, district_id, congregation_id, role):
    await ensure_congregation_in_district(db, district_id, congregation_id)
    guard(auth, district_id, congregation_id, role)


async def slot_for(repository, auth, district_id, slot_id, role):
    slot = await repository.get_slot(slot_id, district_id)
    if not slot:
        raise HTTPException(404, "Reference not found")
    guard(auth, district_id, slot.congregation_id, role)
    return slot


async def assignment_result(operation):
    try:
        return with_revision(await operation)
    except DutyNotFoundError as exc:
        raise HTTPException(404, "Reference not found") from exc
    except DutyIdentityConflictError as exc:
        # Same 409 contract as service assignments: BLOCK conflicts and unconfirmed WARNs.
        raise_for_conflicts(exc.conflicts, confirm_warnings=False)
        raise  # unreachable: the helper always raises for the conflicts it is given
    except DutyConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Duty assignment conflicts with an existing entry") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def planner_congregation_ids(auth, district_id):
    return frozenset(
        membership.scope_id
        for membership in auth.memberships
        if membership.scope_type == ScopeType.CONGREGATION
        and has_role_in_district(auth, Role.PLANNER, district_id, {membership.scope_id})
    )


@router.get("/categories")
async def categories(
    district_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    congregation_id: UUID | None = None,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    await scope(db, auth, district_id, congregation_id, Role.VIEWER)
    category_rows, overrides = await repository.catalog(district_id, congregation_id)
    return {
        "categories": [asdict(category) for category in category_rows],
        "overrides": [asdict(override) for override in overrides],
    }


@router.post("/categories", status_code=201)
async def create_category(
    district_id: UUID,
    body: CategoryCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    await scope(
        db,
        auth,
        district_id,
        body.congregation_id,
        Role.CONGREGATION_ADMIN if body.congregation_id else Role.DISTRICT_ADMIN,
    )
    category = EventDutyCategory(
        id=uuid4(),
        district_id=district_id,
        congregation_id=body.congregation_id,
        code=body.code,
        label=body.label,
        event_categories=tuple(body.event_categories),
        enabled=body.enabled,
        capacity=body.capacity,
    )
    try:
        return asdict(await repository.save_category(category))
    except IntegrityError as exc:
        raise HTTPException(409, "Duty category code already exists in this scope") from exc


@router.patch("/categories/{category_id}")
async def edit_category(
    district_id: UUID,
    category_id: UUID,
    body: CategoryUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    category = await repository.lock_category(category_id, district_id)
    if not category:
        raise HTTPException(404, "Reference not found")
    await scope(
        db,
        auth,
        district_id,
        category.congregation_id,
        Role.CONGREGATION_ADMIN if category.congregation_id else Role.DISTRICT_ADMIN,
    )
    changes = body.model_dump(exclude_unset=True)
    if "event_categories" in changes:
        changes["event_categories"] = tuple(changes["event_categories"])
    return asdict(await repository.save_category(replace(category, **changes)))


@router.put("/configuration")
async def configure(
    district_id: UUID,
    body: ConfigurationWrite,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    await scope(db, auth, district_id, body.congregation_id, Role.CONGREGATION_ADMIN)
    category = await repository.lock_category(body.duty_category_id, district_id)
    if not category or category.congregation_id is not None:
        raise HTTPException(404, "Reference not found")
    configuration = EventTypeDutyConfiguration(
        id=uuid4(),
        district_id=district_id,
        congregation_id=body.congregation_id,
        duty_category_id=body.duty_category_id,
        event_categories=tuple(body.event_categories),
        enabled=body.enabled,
        capacity=body.capacity,
    )
    return asdict(await repository.save_configuration(configuration))


@router.delete("/configuration/{category_id}", status_code=204)
async def clear_configuration(
    district_id: UUID,
    category_id: UUID,
    congregation_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    await scope(db, auth, district_id, congregation_id, Role.CONGREGATION_ADMIN)
    if not await repository.lock_category(category_id, district_id):
        raise HTTPException(404, "Reference not found")
    await repository.delete_configuration(district_id, congregation_id, category_id)


@router.get("/slots/{planning_slot_id}")
async def assignments(
    district_id: UUID,
    planning_slot_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    include_quarantined: bool = False,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    slot = await slot_for(repository, auth, district_id, planning_slot_id, Role.VIEWER)
    view = await EventDutiesService(repository).list_slot_duties(
        district_id,
        slot,
        include_quarantined=include_quarantined,
        district_wide_planner=has_role_in_district(auth, Role.PLANNER, district_id),
        planner_congregation_ids=planner_congregation_ids(auth, district_id),
    )
    return {
        "categories": [asdict(category) for category in view.categories],
        "assignments": [
            dict(
                with_revision(item.assignment),
                needs_review=item.needs_review,
                over_capacity=item.over_capacity,
                quarantined=item.quarantined,
            )
            for item in view.assignments
        ],
    }


@router.post("/slots/{planning_slot_id}", status_code=201)
async def assign(
    district_id: UUID,
    planning_slot_id: UUID,
    body: AssignmentWrite,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    slot = await slot_for(repository, auth, district_id, planning_slot_id, Role.PLANNER)
    return await assignment_result(
        EventDutiesService(repository).assign(
            district_id,
            planning_slot_id,
            body.duty_category_id,
            **body.model_dump(exclude={"duty_category_id"}),
            expected_congregation_id=slot.congregation_id,
        )
    )


@router.get("/slots/{planning_slot_id}/leaders")
async def leader_choices(
    district_id: UUID,
    planning_slot_id: UUID,
    auth: CurrentUserWithMemberships,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    """Leaders a duty of this slot may reference, authorized like the duty write itself.

    Congregation planners cannot read the district leader list, so they get this reduced
    view; it offers only leaders eligible on the slot date, as the write enforces.
    """
    slot = await slot_for(repository, auth, district_id, planning_slot_id, Role.PLANNER)
    return [
        {"id": leader.id, "name": leader.name, "rank": leader.rank.value if leader.rank else None}
        for leader in await repository.list_leaders(district_id)
        if leader.is_eligible_on(slot.planning_date)
    ]


async def assignment_for(repository, auth, district_id, assignment_id):
    assignment = await repository.get_assignment(assignment_id)
    if not assignment or assignment.district_id != district_id:
        raise HTTPException(404, "Reference not found")
    guard(auth, assignment.district_id, assignment.congregation_id, Role.PLANNER)
    return assignment


@router.patch("/assignments/{assignment_id}")
async def replace_assignment(
    district_id: UUID,
    assignment_id: UUID,
    body: AssignmentWrite,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
    if_match: IfMatch = None,
):
    assignment = await assignment_for(repository, auth, district_id, assignment_id)
    slot = await slot_for(repository, auth, district_id, assignment.planning_slot_id, Role.PLANNER)
    # The service re-reads the row under its lock and rejects any difference (409),
    # so the revision verified here is the state the write starts from.
    require_current_revision(if_match, content_revision(assignment))
    return await assignment_result(
        EventDutiesService(repository).replace(
            district_id,
            assignment.planning_slot_id,
            body.duty_category_id,
            assignment,
            **body.model_dump(exclude={"duty_category_id"}),
            expected_congregation_id=slot.congregation_id,
        )
    )


@router.delete("/assignments/{assignment_id}", status_code=204)
async def remove_assignment(
    district_id: UUID,
    assignment_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
    if_match: IfMatch = None,
):
    assignment = await assignment_for(repository, auth, district_id, assignment_id)
    slot = await repository.lock_slot(assignment.planning_slot_id, district_id)
    if not slot:
        raise HTTPException(404, "Reference not found")
    guard(auth, district_id, slot.congregation_id, Role.PLANNER)
    locked_assignment = await repository.lock_assignment(assignment_id)
    if (
        not locked_assignment
        or locked_assignment.district_id != district_id
        or locked_assignment.planning_slot_id != assignment.planning_slot_id
    ):
        raise HTTPException(404, "Reference not found")
    if locked_assignment != assignment:
        raise HTTPException(409, "Duty assignment changed concurrently")
    guard(
        auth,
        locked_assignment.district_id,
        locked_assignment.congregation_id,
        Role.PLANNER,
    )
    require_current_revision(if_match, content_revision(locked_assignment))
    await repository.delete_assignment(assignment_id)


@router.post("/assignments/{assignment_id}/revalidate")
async def revalidate_assignment(
    district_id: UUID,
    assignment_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
    if_match: IfMatch = None,
):
    assignment = await assignment_for(repository, auth, district_id, assignment_id)
    slot = await slot_for(repository, auth, district_id, assignment.planning_slot_id, Role.PLANNER)
    require_current_revision(if_match, content_revision(assignment))
    return await assignment_result(
        EventDutiesService(repository).revalidate(
            district_id,
            assignment.planning_slot_id,
            assignment,
            expected_congregation_id=slot.congregation_id,
        )
    )


@router.get("/suggestions")
async def suggestions(
    district_id: UUID,
    duty_category_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    congregation_id: UUID | None = None,
    include_hidden: bool = False,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    await scope(db, auth, district_id, congregation_id, Role.PLANNER)
    rows = await repository.list_suggestions(district_id, congregation_id, duty_category_id)
    return [with_revision(row) for row in rows if include_hidden or not row.hidden]


@router.post("/suggestions", status_code=201)
async def remember(
    district_id: UUID,
    body: SuggestionWrite,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    await scope(db, auth, district_id, body.congregation_id, Role.PLANNER)
    category_rows, _ = await repository.catalog(district_id, body.congregation_id)
    if not any(category.id == body.duty_category_id for category in category_rows):
        raise HTTPException(404, "Reference not found")
    try:
        return with_revision(
            await repository.remember(
                district_id,
                body.congregation_id,
                body.duty_category_id,
                body.name,
                activate=True,
            )
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.patch("/suggestions/{suggestion_id}")
async def suppress(
    district_id: UUID,
    suggestion_id: UUID,
    body: SuggestionUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
    if_match: IfMatch = None,
):
    suggestion = await repository.lock_suggestion(suggestion_id)
    if not suggestion or suggestion.district_id != district_id:
        raise HTTPException(404, "Reference not found")
    await scope(db, auth, district_id, suggestion.congregation_id, Role.PLANNER)
    require_current_revision(if_match, content_revision(suggestion))
    return with_revision(await repository.save_suggestion(replace(suggestion, hidden=body.hidden)))


@router.get("/eligible-users")
async def eligible_users(
    district_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    congregation_id: UUID | None = None,
    repository: EventDutiesRepository = Depends(get_event_duties_repository),
):
    await scope(db, auth, district_id, congregation_id, Role.PLANNER)
    return await repository.eligible_users(district_id, congregation_id)
