"""app/adapters/api/routers/planning_series.py: API endpoints for PlanningSeries management."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.api.schemas.planning_series import (
    PlanningSeriesCreate,
    PlanningSeriesResponse,
    PlanningSeriesUpdate,
)
from app.adapters.auth.permissions import (
    PermissionError,
    assert_has_role_in_district,
)
from app.adapters.db.repositories.planning_series import SqlPlanningSeriesRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.application.planning_series_service import PlanningSeriesSlotGenerationService
from app.domain.models.planning_series import PlanningSeries
from app.domain.models.role import Role
from app.domain.ports.repositories import (
    PlanningSeriesRepository,
    PlanningSlotRepository,
)

router = APIRouter(prefix="/api/v1/planning-series", tags=["planning-series"])


class SlotGenerationRequest(BaseModel):
    """Request body for slot generation."""

    from_date: date | None = Field(
        default=None,
        description="Start date for generation (defaults to today)",
    )
    to_date: date | None = Field(
        default=None,
        description="End date for generation (defaults to from_date + horizon_months)",
    )
    horizon_months: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Number of months to generate ahead",
    )


class SlotGenerationResponse(BaseModel):
    """Response for slot generation."""

    generated: int = Field(description="Number of new slots created")
    skipped: int = Field(description="Number of existing slots skipped")
    updated: int = Field(description="Number of slots updated")
    series_processed: int | None = Field(
        default=None,
        description="Number of series processed (for district/all endpoints)",
    )
    districts_processed: int | None = Field(
        default=None,
        description="Number of districts processed (for all endpoint)",
    )
    error: str | None = Field(default=None, description="Error message if any")


@router.post(
    "",
    response_model=PlanningSeriesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_planning_series(
    body: PlanningSeriesCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> PlanningSeriesResponse:
    """Create a new PlanningSeries.

    **RBAC:** Requires DISTRICT_ADMIN role in the district.
    """
    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, body.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    series = PlanningSeries.create(
        district_id=body.district_id,
        congregation_id=body.congregation_id,
        category=body.category,
        default_planning_time=body.default_planning_time,
        recurrence_pattern=body.recurrence_pattern or {},
        active_from=body.active_from,
        active_until=body.active_until,
        is_active=body.is_active if body.is_active is not None else True,
    )

    repo = SqlPlanningSeriesRepository(db)
    await repo.save(series)
    await db.commit()

    return PlanningSeriesResponse.from_orm(series)


@router.get("/{series_id}", response_model=PlanningSeriesResponse)
async def get_planning_series(
    series_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> PlanningSeriesResponse:
    """Get a PlanningSeries by ID.

    **RBAC:** Requires VIEWER role in the series' district.
    """
    repo = SqlPlanningSeriesRepository(db)
    series = await repo.get(series_id)

    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PlanningSeries nicht gefunden",
        )

    try:
        assert_has_role_in_district(auth, Role.VIEWER, series.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return PlanningSeriesResponse.from_orm(series)


@router.patch("/{series_id}", response_model=PlanningSeriesResponse)
async def update_planning_series(
    series_id: uuid.UUID,
    body: PlanningSeriesUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> PlanningSeriesResponse:
    """Update a PlanningSeries.

    **RBAC:** Requires DISTRICT_ADMIN role in the series' district.
    """
    repo = SqlPlanningSeriesRepository(db)
    series = await repo.get(series_id)

    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PlanningSeries nicht gefunden",
        )

    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, series.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # Apply updates
    fields = body.model_fields_set
    if "congregation_id" in fields and body.congregation_id is not None:
        series.congregation_id = body.congregation_id
    if "category" in fields and body.category is not None:
        series.category = body.category
    if "default_planning_time" in fields and body.default_planning_time is not None:
        series.default_planning_time = body.default_planning_time
    if "recurrence_pattern" in fields and body.recurrence_pattern is not None:
        series.recurrence_pattern = body.recurrence_pattern
    if "active_from" in fields and body.active_from is not None:
        series.active_from = body.active_from
    if "active_until" in fields and body.active_until is not None:
        series.active_until = body.active_until
    if "is_active" in fields and body.is_active is not None:
        series.is_active = body.is_active

    series.updated_at = datetime.now()
    await repo.save(series)
    await db.commit()

    return PlanningSeriesResponse.from_orm(series)


@router.post(
    "/{series_id}/generate-slots",
    response_model=SlotGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_slots_for_series(
    series_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    body: SlotGenerationRequest = SlotGenerationRequest(),
) -> SlotGenerationResponse:
    """Generate PlanningSlots for a specific PlanningSeries.

    **RBAC:** Requires DISTRICT_ADMIN role in the series' district.
    """
    repo = SqlPlanningSeriesRepository(db)
    series = await repo.get(series_id)

    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PlanningSeries nicht gefunden",
        )

    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, series.district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    service = PlanningSeriesSlotGenerationService(
        series_repo=SqlPlanningSeriesRepository(db),
        slot_repo=SqlPlanningSlotRepository(db),
    )

    result = await service.generate_slots_for_series(
        series_id=series_id,
        from_date=body.from_date,
        to_date=body.to_date,
        horizon_months=body.horizon_months,
    )

    await db.commit()

    return SlotGenerationResponse(**result)


@router.post(
    "/districts/{district_id}/generate-slots",
    response_model=SlotGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_slots_for_district(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    body: SlotGenerationRequest = SlotGenerationRequest(),
) -> SlotGenerationResponse:
    """Generate PlanningSlots for all active PlanningSeries in a district.

    **RBAC:** Requires DISTRICT_ADMIN role in the district.
    """
    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    service = PlanningSeriesSlotGenerationService(
        series_repo=SqlPlanningSeriesRepository(db),
        slot_repo=SqlPlanningSlotRepository(db),
    )

    result = await service.generate_slots_for_district(
        district_id=district_id,
        from_date=body.from_date,
        to_date=body.to_date,
        horizon_months=body.horizon_months,
    )

    await db.commit()

    return SlotGenerationResponse(**result)


@router.post(
    "/generate-all-slots",
    response_model=SlotGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_all_slots(
    auth: CurrentUserWithMemberships,
    db: DbSession,
    body: SlotGenerationRequest = SlotGenerationRequest(),
) -> SlotGenerationResponse:
    """Generate PlanningSlots for all active PlanningSeries across all districts.

    **RBAC:** Requires SUPERADMIN role.
    """
    if not getattr(auth.user, "is_superadmin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Superadmin darf Slots für alle Bezirke generieren",
        )

    service = PlanningSeriesSlotGenerationService(
        series_repo=SqlPlanningSeriesRepository(db),
        slot_repo=SqlPlanningSlotRepository(db),
    )

    result = await service.generate_all_slots(
        from_date=body.from_date,
        to_date=body.to_date,
        horizon_months=body.horizon_months,
    )

    await db.commit()

    return SlotGenerationResponse(**result)
