from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class ExternalEventCandidateORM(Base):
    __tablename__ = "external_event_candidates"
    __table_args__ = (UniqueConstraint("calendar_integration_id", "external_event_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), index=True)
    calendar_integration_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_integrations.id", ondelete="CASCADE"))
    external_event_id: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(50))
    congregation_id: Mapped[UUID | None] = mapped_column(ForeignKey("congregations.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(255))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), index=True)
    matched_slot_id: Mapped[UUID | None] = mapped_column(ForeignKey("planning_slots.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
