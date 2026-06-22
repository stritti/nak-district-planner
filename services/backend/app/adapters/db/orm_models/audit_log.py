"""Audit Log ORM model — SQLAlchemy representation of AuditLog in the database.

Stores immutable audit logs for all write operations and security-relevant events.
Each audit log entry records who performed what action on which resource and when.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class AuditAction(str, Enum):
    """Types of actions that can be audited."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    BULK_OPERATION = "BULK_OPERATION"


class AuditStatus(str, Enum):
    """Status of the audited action — values match the PostgreSQL ENUM."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AuditLogORM(Base):
    """Audit Log ORM model.
    
    This table stores an immutable record of all security-relevant operations.
    Once created, audit log entries cannot be modified or deleted.
    """

    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), index=True
    )

    # Who: User information
    user_sub: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_roles: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # What: Action details
    action: Mapped[AuditAction] = mapped_column(
        SQLEnum(AuditAction), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Where: Tenant context
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Details: Change information
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Context: Request information
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv4/IPv6
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Status
    status: Mapped[AuditStatus] = mapped_column(
        SQLEnum(AuditStatus), default=AuditStatus.SUCCESS, index=True
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Metadata: Additional context
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC)
    )
