"""Membership ORM model — SQLAlchemy representation of Membership in the database.

Stores role assignments for users within specific scopes (District or Congregation).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class MembershipORM(Base):
    """Membership ORM model."""

    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Foreign key to users.sub (OIDC subject)
    user_sub: Mapped[str] = mapped_column(
        String(512), ForeignKey("users.sub"), nullable=False, index=True
    )
    # Role assigned (DISTRICT_ADMIN, CONGREGATION_ADMIN, PLANNER, VIEWER)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Scope type (DISTRICT or CONGREGATION)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # ID of the scope (district_id or congregation_id)
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
