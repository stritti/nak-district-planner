"""app/adapters/db/orm_models/calendar_integration.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base
from app.domain.models.calendar_integration import CalendarType


class CalendarIntegrationORM(Base):
    """ORM model for calendarintegrationorm."""

    __tablename__ = "calendar_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregations.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[CalendarType] = mapped_column(
        SAEnum(CalendarType, name="calendar_type", create_type=False), nullable=False
    )
    credentials_enc: Mapped[str] = mapped_column(String, nullable=False)  # Fernet token
    sync_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    # capabilities stored as a VARCHAR[] of enum string values
    capabilities: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    default_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
