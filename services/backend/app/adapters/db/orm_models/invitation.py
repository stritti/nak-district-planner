"""app/adapters/db/orm_models/invitation.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base
from app.domain.models.invitation import InvitationTargetType


class CongregationInvitationORM(Base):
    """ORM model for congregationinvitationorm."""

    __tablename__ = "congregation_invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    source_congregation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregations.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[InvitationTargetType] = mapped_column(
        SAEnum(InvitationTargetType, name="invitation_target_type", create_type=False),
        nullable=False,
    )
    target_congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregations.id", ondelete="SET NULL"), nullable=True
    )
    external_target_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linked_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
