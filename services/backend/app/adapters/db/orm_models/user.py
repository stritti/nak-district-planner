"""
User ORM model — SQLAlchemy representation of User in the database.

Stores user information extracted from OIDC tokens.
Each user is uniquely identified by `sub` (OIDC subject/user ID).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Unique
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class UserORM(Base):
    """User ORM model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # OIDC subject (user ID from identity provider) — globally unique
    sub: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    # Email address (extracted from OIDC token)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Username (preferred_username or email)
    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Full name (optional)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # First name (optional)
    given_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Last name (optional)
    family_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
