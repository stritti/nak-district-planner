"""app/adapters/db/orm_models/leader.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class LeaderORM(Base):
    """ORM model for leaderorm."""

    __tablename__ = "leaders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("districts.id", ondelete="CASCADE"),
        nullable=False,
    )
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("congregations.id", ondelete="SET NULL"),
        nullable=True,
    )
    rank: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    special_role: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    user_sub: Mapped[str | None] = mapped_column(
        sa.String(512), sa.ForeignKey("users.sub", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
