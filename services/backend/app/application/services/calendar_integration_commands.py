# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Application commands independent from FastAPI and Pydantic schemas."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarType,
    SyncDeleteMode,
)


@dataclass(frozen=True)
class CalendarIntegrationCreateCommand:
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    name: str
    type: CalendarType
    credentials: dict[str, Any]
    sync_interval: int
    capabilities: list[CalendarCapability]
    default_category: str | None
    delete_behavior: SyncDeleteMode


@dataclass(frozen=True)
class CalendarIntegrationUpdateCommand:
    """Typed patch input: provided_fields preserves explicit null semantics.

    Omitted fields are ignored. An explicit null clears only nullable values
    such as default_category; it does not overwrite required integration data.
    """

    name: str | None = None
    credentials: dict[str, Any] | None = None
    sync_interval: int | None = None
    capabilities: list[CalendarCapability] | None = None
    default_category: str | None = None
    delete_behavior: SyncDeleteMode | None = None
    provided_fields: frozenset[str] = field(default_factory=frozenset)
