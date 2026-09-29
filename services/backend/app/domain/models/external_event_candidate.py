"""External events awaiting an explicit governance decision."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.models.raw_calendar_event import RawCalendarEvent


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
    def event_date(self):
        return self.start_at.astimezone(UTC).date()

    @property
    def event_time(self):
        return self.start_at.astimezone(UTC).time()

    @classmethod
    def create(cls, *, integration, raw: RawCalendarEvent, content_hash: str):
        now = datetime.now(UTC)
        return cls(
            id=uuid4(), district_id=integration.district_id,
            calendar_integration_id=integration.id, external_event_id=raw.uid,
            source=integration.type.value, congregation_id=integration.congregation_id,
            title=raw.title, category=integration.default_category,
            start_at=raw.start_at, end_at=raw.end_at, description=raw.description,
            content_hash=content_hash, status=CandidateStatus.PENDING,
            created_at=now, updated_at=now,
        )

    def refresh(self, raw: RawCalendarEvent, content_hash: str, category: str | None):
        if self.status != CandidateStatus.PENDING:
            return
        self.title, self.description = raw.title, raw.description
        self.start_at, self.end_at = raw.start_at, raw.end_at
        self.content_hash, self.category = content_hash, category
        self.updated_at = datetime.now(UTC)
        if raw.is_cancelled:
            self.review(CandidateStatus.DISMISSED, None)

    def review(self, status: CandidateStatus, user_sub: str | None, slot_id: UUID | None = None):
        if self.status != CandidateStatus.PENDING:
            raise ValueError("Kandidat wurde bereits geprüft")
        self.status, self.reviewed_by, self.matched_slot_id = status, user_sub, slot_id
        self.reviewed_at = self.updated_at = datetime.now(UTC)
