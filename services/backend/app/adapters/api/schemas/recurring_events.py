# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Typed input and output contracts for recurring-event monthly planning."""

from __future__ import annotations

import uuid
from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models.recurring_event_template import (
    ChecklistStatus,
    DecisionStatus,
    RecurrenceKind,
    RecurrenceRule,
)


class RecurrenceRulePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    kind: RecurrenceKind
    anchor_date: date
    interval: int = Field(default=1, ge=1, strict=True)
    weekdays: tuple[int, ...] = ()
    day_of_month: int | None = None
    weekday: int | None = None
    ordinal: int | None = None
    version: int = Field(default=1, strict=True)

    @model_validator(mode="after")
    def validate_rule(self) -> RecurrenceRulePayload:
        self.to_domain()
        return self

    def to_domain(self) -> RecurrenceRule:
        return RecurrenceRule(**self.model_dump())


class RecurringTemplateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category: str = Field(min_length=1, max_length=255)
    congregation_id: uuid.UUID | None = None
    start_time: time
    duration_minutes: int = Field(gt=0, le=525600, strict=True)
    recurrence: RecurrenceRulePayload
    applicability: list[str] = Field(default_factory=list, max_length=500)
    excluded_dates: list[date] = Field(default_factory=list, max_length=2000)
    active_from: date | None = None
    active_until: date | None = None
    is_active: bool = True


class RecurringTemplatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, strict=True)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=255)
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=525600, strict=True)
    recurrence: RecurrenceRulePayload | None = None
    applicability: list[str] | None = Field(default=None, max_length=500)
    excluded_dates: list[date] | None = Field(default=None, max_length=2000)
    active_from: date | None = None
    active_until: date | None = None
    is_active: bool | None = None


class RecurringTemplateResponse(RecurringTemplateCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    district_id: uuid.UUID
    revision: int
    applicability: list[str]
    excluded_dates: list[date]
    timezone: str


class TemplateListResponse(BaseModel):
    items: list[RecurringTemplateResponse]
    total: int
    limit: int = 50
    offset: int = 0


class ChecklistItemResponse(BaseModel):
    template_id: uuid.UUID
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    title: str
    description: str | None
    category: str
    occurrence_local_date: date
    start_time: time
    duration_minutes: int
    template_revision: int
    status: ChecklistStatus
    decision_status: DecisionStatus | None
    planning_slot_id: uuid.UUID | None
    reason: str | None


class ChecklistResponse(BaseModel):
    items: list[ChecklistItemResponse]
    total: int
    limit: int
    offset: int
    counts: dict[str, int]


class OccurrenceActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: uuid.UUID
    occurrence_local_date: date
    template_revision: int = Field(ge=1, strict=True)


class OccurrenceAcceptRequest(OccurrenceActionRequest):
    local_date_override: date | None = None
    local_time_override: time | None = None
    title_override: str | None = Field(default=None, min_length=1, max_length=500)
    description_override: str | None = None
    duration_minutes_override: int | None = Field(default=None, gt=0, le=525600, strict=True)
    fold: Literal[0, 1] | None = None


class BulkOccurrenceAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OccurrenceAcceptRequest] = Field(min_length=1, max_length=100)


class OccurrenceResolveRequest(OccurrenceActionRequest):
    action: Literal["LINK_EXISTING", "MARK_SKIPPED", "REOPEN"]
    planning_slot_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_link(self) -> OccurrenceResolveRequest:
        if self.action == "LINK_EXISTING" and self.planning_slot_id is None:
            raise ValueError("LINK_EXISTING requires planning_slot_id")
        if self.action != "LINK_EXISTING" and self.planning_slot_id is not None:
            raise ValueError("planning_slot_id is only valid for LINK_EXISTING")
        return self


class OccurrenceActionResult(BaseModel):
    template_id: uuid.UUID
    occurrence_local_date: date
    status: ChecklistStatus
    planning_slot_id: uuid.UUID | None = None


class BulkOccurrenceResult(BaseModel):
    template_id: uuid.UUID
    occurrence_local_date: date
    status: ChecklistStatus | None
    planning_slot_id: uuid.UUID | None = None
    error: str | None = None


class BulkOccurrenceResponse(BaseModel):
    results: list[BulkOccurrenceResult]
