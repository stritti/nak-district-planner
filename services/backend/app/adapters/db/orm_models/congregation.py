from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base
from app.domain.models.congregation import DEFAULT_SERVICE_TIMES
from app.domain.models.invitation import InvitationTargetType


class CongregationORM(Base):
    __tablename__ = "congregations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregation_groups.id", ondelete="SET NULL"), nullable=True
    )
    service_times: Mapped[list] = mapped_column(
        JSONB(), nullable=False, default=lambda: list(DEFAULT_SERVICE_TIMES)
    )
    invitation_target_type: Mapped[InvitationTargetType | None] = mapped_column(
        SAEnum(InvitationTargetType, name="invitation_target_type", create_type=False),
        nullable=True,
    )
    invitation_target_congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("congregations.id", ondelete="SET NULL"), nullable=True
    )
    invitation_external_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
