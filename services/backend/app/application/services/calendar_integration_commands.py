# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Application commands independent from FastAPI and Pydantic schemas."""

from dataclasses import dataclass, field
from typing import Any
import uuid

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
    """Explicitly supplied fields; omission differs from clearing a value."""

    changes: dict[str, Any] = field(default_factory=dict)
