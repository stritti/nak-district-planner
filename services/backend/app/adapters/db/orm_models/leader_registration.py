from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class LeaderRegistrationORM(Base):
    __tablename__ = "leader_registrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("districts.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    email: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    rank: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("congregations.id", ondelete="SET NULL"),
        nullable=True,
    )
    special_role: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # PENDING | APPROVED | REJECTED
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="PENDING", server_default="PENDING"
    )
    rejection_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Linked OIDC subject, if the user was authenticated at the time of registration
    user_sub: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
