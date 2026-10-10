# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import ARRAY, Boolean, Date, DateTime, ForeignKey, Index, String, Time, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlotStatus


class PlanningSlotORM(Base):
    __tablename__ = "planning_slots"
    __table_args__ = (
        Index("ix_planning_slots_district_date", "district_id", "planning_date"),
        Index("ix_planning_slots_congregation_date", "congregation_id", "planning_date"),
        # A congregation cannot hold two active slots at the same date and time.
        Index(
            "no_overlapping_planning_slots",
            "congregation_id",
            "planning_date",
            "planning_time",
            unique=True,
            postgresql_where=text("congregation_id IS NOT NULL AND status = 'ACTIVE'"),
        ),
        # One slot per generator occurrence, whatever its status, so a re-run
        # (or a concurrent run) cannot re-create a moved or cancelled draft.
        Index(
            "uq_planning_slots_generation_key",
            "district_id",
            "generation_key",
            unique=True,
            postgresql_where=text("generation_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planning_series.id", ondelete="SET NULL"), nullable=True
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregations.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Title for the slot (used when no EventInstance exists or as fallback)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Approval status for planning workflow (migrated from Event.approval_status)
    approval_status: Mapped[EventApprovalStatus | None] = mapped_column(
        SAEnum(EventApprovalStatus, name="event_approval_status", create_type=False), nullable=True
    )
    # Invitation tracking fields (migrated from Event)
    invitation_source_congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregations.id", ondelete="SET NULL"), nullable=True
    )
    invitation_source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # List of congregation IDs (as strings) that this slot applies to (for district-wide holidays)
    # Supports "all" sentinel string for district-wide applicability
    applicability: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=[])
    generation_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generation_key_detached: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planning_date: Mapped[date] = mapped_column(Date, nullable=False)
    planning_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    status: Mapped[PlanningSlotStatus] = mapped_column(
        SAEnum(PlanningSlotStatus, name="planning_slot_status", create_type=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
