# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Scoped organisational duty administration and planner assignment APIs."""

from dataclasses import asdict
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
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
from app.adapters.db.orm_models.event_duty import (
    DutyNameSuggestionORM,
    EventDutyAssignmentORM,
    EventDutyCategoryORM,
    EventTypeDutyConfigurationORM,
)
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.repositories.event_duties import SqlEventDutiesRepository, domain
from app.application.event_duties import DutyConflictError, DutyNotFoundError, EventDutiesService
from app.domain.models.event_duty import (
    DutyNameSuggestion,
    EventDutyCategory,
    EventTypeDutyConfiguration,
    effective_categories,
)
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/districts/{district_id}/duties", tags=["event-duties"])


def guard(auth, district_id, congregation_id, role):
    require_role_in_district(
        auth, role, district_id, {congregation_id} if congregation_id else None
    )


async def scope(db, auth, district_id, congregation_id, role):
    await ensure_congregation_in_district(db, district_id, congregation_id)
    guard(auth, district_id, congregation_id, role)


async def slot_for(db, auth, district_id, slot_id, role):
    slot = await db.scalar(
        select(PlanningSlotORM).where(
            PlanningSlotORM.id == slot_id, PlanningSlotORM.district_id == district_id
        )
    )
    if not slot:
        raise HTTPException(404, "Reference not found")
    guard(auth, district_id, slot.congregation_id, role)
    return slot


async def run_assignment(
    db, auth, district_id, slot_id, body, replacing=None, revalidate=False
):
    try:
        return asdict(
            await EventDutiesService(SqlEventDutiesRepository(db)).assign(
                district_id,
                slot_id,
                category_id=body.duty_category_id,
                **body.model_dump(exclude={"duty_category_id"}),
                replacing=replacing,
                revalidate=revalidate,
                authorize_slot=lambda slot: guard(
                    auth, district_id, slot.congregation_id, Role.PLANNER
                ),
            )
        )
    except DutyNotFoundError as exc:
        raise HTTPException(404, "Reference not found") from exc
    except DutyConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Duty assignment conflicts with an existing entry") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/categories")
async def categories(
    district_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    congregation_id: UUID | None = None,
):
    await scope(db, auth, district_id, congregation_id, Role.VIEWER)
    cats, overrides = await SqlEventDutiesRepository(db).catalog(district_id, congregation_id)
    return {"categories": [asdict(x) for x in cats], "overrides": [asdict(x) for x in overrides]}


@router.post("/categories", status_code=201)
async def create_category(
    district_id: UUID, body: CategoryCreate, auth: CurrentUserWithMemberships, db: DbSession
):
    await scope(
        db,
        auth,
        district_id,
        body.congregation_id,
        Role.CONGREGATION_ADMIN if body.congregation_id else Role.DISTRICT_ADMIN,
    )
    row = EventDutyCategoryORM(id=uuid4(), district_id=district_id, **body.model_dump())
    db.add(row)
    await db.flush()
    return asdict(domain(EventDutyCategory, row))


@router.patch("/categories/{category_id}")
async def edit_category(
    district_id: UUID,
    category_id: UUID,
    body: CategoryUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
):
    row = await SqlEventDutiesRepository(db).lock_category(category_id, district_id)
    if not row:
        raise HTTPException(404, "Reference not found")
    await scope(
        db,
        auth,
        district_id,
        row.congregation_id,
        Role.CONGREGATION_ADMIN if row.congregation_id else Role.DISTRICT_ADMIN,
    )
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is None:
            raise HTTPException(422, "Null is not permitted")
        setattr(row, key, value)
    await db.flush()
    return asdict(domain(EventDutyCategory, row))


@router.put("/configuration")
async def configure(
    district_id: UUID, body: ConfigurationWrite, auth: CurrentUserWithMemberships, db: DbSession
):
    await scope(db, auth, district_id, body.congregation_id, Role.CONGREGATION_ADMIN)
    category = await SqlEventDutiesRepository(db).lock_category(body.duty_category_id, district_id)
    if not category or category.congregation_id is not None:
        raise HTTPException(404, "Reference not found")
    row = await db.scalar(
        select(EventTypeDutyConfigurationORM).where(
            EventTypeDutyConfigurationORM.duty_category_id == body.duty_category_id,
            EventTypeDutyConfigurationORM.congregation_id == body.congregation_id,
        )
    )
    if not row:
        row = EventTypeDutyConfigurationORM(
            id=uuid4(), district_id=district_id, **body.model_dump()
        )
        db.add(row)
    else:
        for key, value in body.model_dump().items():
            setattr(row, key, value)
    await db.flush()
    return asdict(domain(EventTypeDutyConfiguration, row))


@router.delete("/configuration/{category_id}", status_code=204)
async def clear_configuration(
    district_id: UUID,
    category_id: UUID,
    congregation_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
):
    await scope(db, auth, district_id, congregation_id, Role.CONGREGATION_ADMIN)
    await SqlEventDutiesRepository(db).lock_category(category_id, district_id)
    await db.execute(
        delete(EventTypeDutyConfigurationORM).where(
            EventTypeDutyConfigurationORM.district_id == district_id,
            EventTypeDutyConfigurationORM.congregation_id == congregation_id,
            EventTypeDutyConfigurationORM.duty_category_id == category_id,
        )
    )


@router.get("/slots/{planning_slot_id}")
async def assignments(
    district_id: UUID,
    planning_slot_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    include_quarantined: bool = False,
):
    slot = await slot_for(db, auth, district_id, planning_slot_id, Role.VIEWER)
    repo = SqlEventDutiesRepository(db)
    cats, overrides = await repo.catalog(district_id, slot.congregation_id)
    effective = effective_categories(cats, overrides, slot.category, slot.congregation_id)
    all_rows = await repo.list_assignments([planning_slot_id])
    rows = []
    for row in all_rows:
        visible = row.visible_in(district_id, slot.congregation_id)
        if not visible:
            if not include_quarantined:
                continue
            try:
                guard(auth, district_id, slot.congregation_id, Role.PLANNER)
                guard(auth, row.district_id, row.congregation_id, Role.PLANNER)
            except HTTPException as exc:
                if exc.status_code == 403:
                    continue
                raise
        category = next((c for c in effective if c.id == row.duty_category_id), None)
        count = sum(x.duty_category_id == row.duty_category_id for x in all_rows)
        rows.append(
            dict(
                asdict(row),
                needs_review=not visible or category is None,
                over_capacity=bool(category and count > category.capacity),
                quarantined=not visible,
            )
        )
    return {"categories": [asdict(x) for x in effective], "assignments": rows}


@router.post("/slots/{planning_slot_id}", status_code=201)
async def assign(
    district_id: UUID,
    planning_slot_id: UUID,
    body: AssignmentWrite,
    auth: CurrentUserWithMemberships,
    db: DbSession,
):
    return await run_assignment(db, auth, district_id, planning_slot_id, body)


async def assignment_for(db, auth, district_id, assignment_id):
    row = await db.get(EventDutyAssignmentORM, assignment_id)
    if not row or row.district_id != district_id:
        raise HTTPException(404, "Reference not found")
    guard(auth, row.district_id, row.congregation_id, Role.PLANNER)
    return next(
        x
        for x in await SqlEventDutiesRepository(db).list_assignments([row.planning_slot_id])
        if x.id == assignment_id
    )


@router.patch("/assignments/{assignment_id}")
async def replace_assignment(
    district_id: UUID,
    assignment_id: UUID,
    body: AssignmentWrite,
    auth: CurrentUserWithMemberships,
    db: DbSession,
):
    row = await assignment_for(db, auth, district_id, assignment_id)
    return await run_assignment(
        db, auth, district_id, row.planning_slot_id, body, replacing=row
    )


@router.delete("/assignments/{assignment_id}", status_code=204)
async def remove_assignment(
    district_id: UUID, assignment_id: UUID, auth: CurrentUserWithMemberships, db: DbSession
):
    row = await assignment_for(db, auth, district_id, assignment_id)
    repo = SqlEventDutiesRepository(db)
    slot = await repo.lock_slot(row.planning_slot_id, district_id)
    if not slot:
        raise HTTPException(404, "Reference not found")
    guard(auth, district_id, slot.congregation_id, Role.PLANNER)
    await repo.delete_assignment(assignment_id)


@router.post("/assignments/{assignment_id}/revalidate")
async def revalidate_assignment(
    district_id: UUID, assignment_id: UUID, auth: CurrentUserWithMemberships, db: DbSession
):
    row = await assignment_for(db, auth, district_id, assignment_id)
    body = AssignmentWrite(
        duty_category_id=row.duty_category_id,
        name=row.display_name if not row.linked_user_sub else None,
        linked_user_sub=row.linked_user_sub,
    )
    return await run_assignment(
        db,
        auth,
        district_id,
        row.planning_slot_id,
        body,
        replacing=row,
        revalidate=True,
    )


@router.get("/suggestions")
async def suggestions(
    district_id: UUID,
    duty_category_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    congregation_id: UUID | None = None,
    include_hidden: bool = False,
):
    await scope(db, auth, district_id, congregation_id, Role.PLANNER)
    rows = (
        await db.scalars(
            select(DutyNameSuggestionORM)
            .where(
                DutyNameSuggestionORM.district_id == district_id,
                DutyNameSuggestionORM.congregation_id == congregation_id,
                DutyNameSuggestionORM.duty_category_id == duty_category_id,
            )
            .order_by(DutyNameSuggestionORM.normalized_name)
        )
    ).all()
    return [asdict(domain(DutyNameSuggestion, x)) for x in rows if include_hidden or not x.hidden]


@router.post("/suggestions", status_code=201)
async def remember(
    district_id: UUID, body: SuggestionWrite, auth: CurrentUserWithMemberships, db: DbSession
):
    await scope(db, auth, district_id, body.congregation_id, Role.PLANNER)
    repo = SqlEventDutiesRepository(db)
    cats, _ = await repo.catalog(district_id, body.congregation_id)
    if not any(c.id == body.duty_category_id for c in cats):
        raise HTTPException(404, "Reference not found")
    try:
        return asdict(
            await repo.remember(
                district_id, body.congregation_id, body.duty_category_id, body.name, activate=True
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
):
    row = await db.get(DutyNameSuggestionORM, suggestion_id)
    if not row or row.district_id != district_id:
        raise HTTPException(404, "Reference not found")
    await scope(db, auth, district_id, row.congregation_id, Role.PLANNER)
    row.hidden = body.hidden
    await db.flush()
    return asdict(domain(DutyNameSuggestion, row))


@router.get("/eligible-users")
async def eligible_users(
    district_id: UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    congregation_id: UUID | None = None,
):
    await scope(db, auth, district_id, congregation_id, Role.PLANNER)
    return await SqlEventDutiesRepository(db).eligible_users(district_id, congregation_id)
