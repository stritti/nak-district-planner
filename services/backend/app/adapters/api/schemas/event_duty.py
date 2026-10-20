# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Validated REST inputs for optional scoped duties."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.models.event_duty import display_name


class CategoryCreate(BaseModel):
    congregation_id: UUID | None = None
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,99}$")
    label: str = Field(min_length=1, max_length=255)
    event_categories: list[Annotated[str, Field(max_length=255)]] = Field(
        default_factory=list, max_length=100
    )
    enabled: bool = True
    capacity: int = Field(default=1, ge=1, le=1000)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return display_name(value)


class CategoryUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    event_categories: list[Annotated[str, Field(max_length=255)]] | None = None
    enabled: bool | None = None
    capacity: int | None = Field(default=None, ge=1, le=1000)

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, value):
        if isinstance(value, dict) and any(
            key in value and value[key] is None
            for key in ("label", "event_categories", "enabled", "capacity")
        ):
            raise ValueError("Null is not permitted")
        return value

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str | None) -> str | None:
        return display_name(value) if value is not None else None


class ConfigurationWrite(BaseModel):
    congregation_id: UUID
    duty_category_id: UUID
    event_categories: list[Annotated[str, Field(max_length=255)]] = Field(default_factory=list)
    enabled: bool = True
    capacity: int = Field(default=1, ge=1, le=1000)


class AssignmentWrite(BaseModel):
    duty_category_id: UUID
    name: str | None = Field(default=None, min_length=1, max_length=255)
    linked_user_sub: str | None = Field(default=None, min_length=1, max_length=512)
    leader_id: UUID | None = None
    suggestion_id: UUID | None = None
    # Acknowledges name-only (WARN) matches with an overlapping duty of the same name.
    confirm_warnings: bool = False

    @model_validator(mode="after")
    def identity(self):
        if sum(bool(value) for value in (self.name, self.linked_user_sub, self.leader_id)) != 1:
            raise ValueError("Exactly one identity required")
        if self.name:
            self.name = display_name(self.name)
        if (self.linked_user_sub or self.leader_id) and self.suggestion_id:
            raise ValueError("Linked identity cannot use a name suggestion")
        return self


class SuggestionWrite(BaseModel):
    congregation_id: UUID | None = None
    duty_category_id: UUID
    name: str = Field(min_length=1, max_length=255)


class SuggestionUpdate(BaseModel):
    hidden: bool
