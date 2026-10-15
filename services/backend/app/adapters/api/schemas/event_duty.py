# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Validated REST inputs for optional scoped duties."""

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.models.event_duty import display_name


class CategoryCreate(BaseModel):
    congregation_id: UUID | None = None
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,99}$")
    label: str = Field(min_length=1, max_length=255)
    event_categories: list[str] = Field(default_factory=list, max_length=100)
    enabled: bool = True
    capacity: int = Field(default=1, ge=1, le=1000)


class CategoryUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    event_categories: list[str] | None = None
    enabled: bool | None = None
    capacity: int | None = Field(default=None, ge=1, le=1000)


class ConfigurationWrite(BaseModel):
    congregation_id: UUID
    duty_category_id: UUID
    event_categories: list[str] = Field(default_factory=list)
    enabled: bool = True
    capacity: int = Field(default=1, ge=1, le=1000)


class AssignmentWrite(BaseModel):
    duty_category_id: UUID
    name: str | None = Field(default=None, min_length=1, max_length=255)
    linked_user_sub: str | None = Field(default=None, min_length=1, max_length=512)
    suggestion_id: UUID | None = None

    @model_validator(mode="after")
    def identity(self):
        if bool(self.name) == bool(self.linked_user_sub):
            raise ValueError("Exactly one identity required")
        if self.name:
            self.name = display_name(self.name)
        if self.linked_user_sub and self.suggestion_id:
            raise ValueError("Linked identity cannot use a name suggestion")
        return self


class SuggestionWrite(BaseModel):
    congregation_id: UUID | None = None
    duty_category_id: UUID
    name: str = Field(min_length=1, max_length=255)


class SuggestionUpdate(BaseModel):
    hidden: bool
