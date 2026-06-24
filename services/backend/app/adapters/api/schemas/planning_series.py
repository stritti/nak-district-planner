"""app/adapters/api/schemas/planning_series.py: Pydantic schemas for PlanningSeries."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models.planning_series import PlanningSeries


class PlanningSeriesCreate(BaseModel):
    """Request body for creating a PlanningSeries."""

    district_id: uuid.UUID = Field(..., description="District this series belongs to")
    congregation_id: uuid.UUID | None = Field(
        default=None,
        description="Congregation this series applies to (optional)",
    )
    category: str | None = Field(
        default=None,
        max_length=255,
        description="Category of services (e.g., 'Gottesdienst')",
    )
    default_planning_time: time = Field(
        ...,
        description="Default time for generated slots (e.g., 09:30:00)",
    )
    recurrence_pattern: dict[str, Any] | None = Field(
        default=None,
        description="Recurrence pattern for slot generation",
        examples=[
            {"frequency": "weekly", "interval": 1, "by_weekday": [6]},  # Sunday weekly
            {"frequency": "monthly", "interval": 1, "by_month_day": 1},  # 1st of month
        ],
    )
    active_from: date | None = Field(
        default=None,
        description="First date when this series is active",
    )
    active_until: date | None = Field(
        default=None,
        description="Last date when this series is active",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether this series is active (defaults to True)",
    )


class PlanningSeriesUpdate(BaseModel):
    """Partial update for PlanningSeries — only fields present are changed."""

    congregation_id: uuid.UUID | None = Field(
        default=None,
        description="Congregation this series applies to",
    )
    category: str | None = Field(
        default=None,
        max_length=255,
        description="Category of services",
    )
    default_planning_time: time | None = Field(
        default=None,
        description="Default time for generated slots",
    )
    recurrence_pattern: dict[str, Any] | None = Field(
        default=None,
        description="Recurrence pattern for slot generation",
    )
    active_from: date | None = Field(
        default=None,
        description="First date when this series is active",
    )
    active_until: date | None = Field(
        default=None,
        description="Last date when this series is active",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether this series is active",
    )


class PlanningSeriesResponse(BaseModel):
    """Response schema for PlanningSeries."""

    id: uuid.UUID
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    category: str | None
    default_planning_time: time
    recurrence_pattern: dict[str, Any]
    active_from: date | None
    active_until: date | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, series: PlanningSeries) -> PlanningSeriesResponse:
        """Convert domain model to response schema."""
        return cls(
            id=series.id,
            district_id=series.district_id,
            congregation_id=series.congregation_id,
            category=series.category,
            default_planning_time=series.default_planning_time,
            recurrence_pattern=series.recurrence_pattern,
            active_from=series.active_from,
            active_until=series.active_until,
            is_active=series.is_active,
            created_at=series.created_at,
            updated_at=series.updated_at,
        )
