"""app/adapters/db/orm_models/invitation_overwrite_request.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base
from app.domain.models.invitation import OverwriteDecisionStatus


class InvitationOverwriteRequestORM(Base):
    """ORM model for invitationoverwriterequestorm."""

    __tablename__ = "invitation_overwrite_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invitation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("congregation_invitations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    target_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    proposed_title: Mapped[str] = mapped_column(String(500), nullable=False)
    proposed_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposed_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposed_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[OverwriteDecisionStatus] = mapped_column(
        SAEnum(OverwriteDecisionStatus, name="overwrite_decision_status", create_type=False),
        nullable=False,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
