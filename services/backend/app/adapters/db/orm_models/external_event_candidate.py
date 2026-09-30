"""Persistence model for external events requiring district review."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class ExternalEventCandidateORM(Base):
    __tablename__ = "external_event_candidates"
    __table_args__ = (
        UniqueConstraint("calendar_integration_id", "external_event_id"),
        CheckConstraint("end_at > start_at", name="ck_external_candidates_positive_duration"),
        Index("ix_external_candidates_district_status", "district_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    calendar_integration_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_integrations.id", ondelete="CASCADE"), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    congregation_id: Mapped[UUID | None] = mapped_column(ForeignKey("congregations.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(255))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_marker: Mapped[str | None] = mapped_column(String(500))
    provider_resource_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    matched_slot_id: Mapped[UUID | None] = mapped_column(ForeignKey("planning_slots.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
