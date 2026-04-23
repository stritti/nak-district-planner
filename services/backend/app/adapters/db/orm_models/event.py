"""app/adapters/db/orm_models/event.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base
from app.domain.models.event import EventSource, EventStatus, EventVisibility


class EventORM(Base):
    """ORM model for eventorm."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregations.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[EventSource] = mapped_column(
        SAEnum(EventSource, name="event_source", create_type=False), nullable=False
    )
    status: Mapped[EventStatus] = mapped_column(
        SAEnum(EventStatus, name="event_status", create_type=False), nullable=False
    )
    visibility: Mapped[EventVisibility] = mapped_column(
        SAEnum(EventVisibility, name="event_visibility", create_type=False), nullable=False
    )
    audiences: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    applicability: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    # External sync fields (NULL for source=INTERNAL events)
    external_uid: Mapped[str | None] = mapped_column(String(500), nullable=True)
    calendar_integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calendar_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generation_slot_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invitation_source_congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregations.id", ondelete="SET NULL"), nullable=True
    )
    invitation_source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
