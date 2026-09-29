"""External events awaiting an explicit governance decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.domain.errors import CandidateAlreadyReviewed
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
    matched_slot_id: UUID | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None

    @property
    def event_date(self) -> date:
        return self.start_at.astimezone(UTC).date()

    @property
    def event_time(self) -> time:
        return self.start_at.astimezone(UTC).time()

    @classmethod
    def create(
        cls,
        *,
        integration: CalendarIntegration,
        raw: RawCalendarEvent,
        content_hash: str,
    ) -> ExternalEventCandidate:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            district_id=integration.district_id,
            calendar_integration_id=integration.id,
            external_event_id=raw.uid,
            source=integration.type.value,
            congregation_id=integration.congregation_id,
            title=raw.title,
            category=integration.default_category,
            start_at=raw.start_at,
            end_at=raw.end_at,
            description=raw.description,
            content_hash=content_hash,
            status=CandidateStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

    def refresh(
        self,
        raw: RawCalendarEvent,
        content_hash: str,
        category: str | None,
    ) -> None:
        if self.status != CandidateStatus.PENDING:
            return
        self.title = raw.title
        self.description = raw.description
        self.start_at = raw.start_at
        self.end_at = raw.end_at
        self.content_hash = content_hash
        self.category = category
        self.updated_at = datetime.now(UTC)

    def review(
        self,
        status: CandidateStatus,
        user_sub: str | None,
        slot_id: UUID | None = None,
    ) -> None:
        if self.status != CandidateStatus.PENDING:
            raise CandidateAlreadyReviewed("Kandidat wurde bereits geprüft")
        self.status = status
        self.reviewed_by = user_sub
        self.matched_slot_id = slot_id
        self.reviewed_at = self.updated_at = datetime.now(UTC)
