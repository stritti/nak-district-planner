# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""External calendar events waiting for an explicit district review."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.domain.errors import CandidateAlreadyReviewedError
from app.domain.models.raw_calendar_event import RawCalendarEvent

if TYPE_CHECKING:
    from app.domain.models.calendar_integration import CalendarIntegration


class CandidateStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"


@dataclass
class ExternalEventCandidate:
    id: UUID
    district_id: UUID
    calendar_integration_id: UUID
    external_event_id: str
    source: str
    congregation_id: UUID | None
    title: str
    category: str | None
    start_at: datetime
    end_at: datetime
    description: str | None
    content_hash: str
    status: CandidateStatus
    created_at: datetime
    updated_at: datetime
    revision_marker: str | None = None
    provider_resource_id: str | None = None
    matched_slot_id: UUID | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None

    @property
    def event_date(self) -> date:
        return self.start_at.astimezone(UTC).date()

    @property
    def event_time(self) -> time:
        return self.start_at.astimezone(UTC).time().replace(tzinfo=None)

    @classmethod
    def create(cls, *, integration: CalendarIntegration, raw: RawCalendarEvent, content_hash: str) -> ExternalEventCandidate:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(), district_id=integration.district_id,
            calendar_integration_id=integration.id, external_event_id=raw.uid,
            source=integration.type.value, congregation_id=integration.congregation_id,
            title=raw.title, category=integration.default_category,
            start_at=raw.start_at, end_at=raw.end_at, description=raw.description,
            content_hash=content_hash, status=CandidateStatus.PENDING,
            created_at=now, updated_at=now,
            revision_marker=raw.revision_marker, provider_resource_id=raw.resource_id,
        )

    def refresh(self, raw: RawCalendarEvent, content_hash: str, category: str | None) -> None:
        if self.status != CandidateStatus.PENDING:
            return
        self.title = raw.title
        self.description = raw.description
        self.start_at = raw.start_at
        self.end_at = raw.end_at
        self.content_hash = content_hash
        self.category = category
        self.revision_marker = raw.revision_marker
        self.provider_resource_id = raw.resource_id
        self.updated_at = datetime.now(UTC)

    def review(self, status: CandidateStatus, user_sub: str | None, slot_id: UUID | None = None) -> None:
        if self.status != CandidateStatus.PENDING:
            raise CandidateAlreadyReviewedError("Kandidat wurde bereits geprüft")
        if status == CandidateStatus.PENDING:
            raise ValueError("Pending is not a review decision")
        self.status = status
        self.reviewed_by = user_sub
        self.matched_slot_id = slot_id
        self.reviewed_at = self.updated_at = datetime.now(UTC)
