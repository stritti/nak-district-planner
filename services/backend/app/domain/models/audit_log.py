"""Audit Log domain model.

Represents audit log entries for tracking security-relevant operations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, NamedTuple


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
    """Status of the audited action."""

    SUCCESS = "success"
    FAILED = "failed"


class AuditLog(NamedTuple):
    """Audit log entry.
    
    Represents a single audit log entry with all relevant information
    about a security-relevant operation.
    """

    id: uuid.UUID
    timestamp: datetime
    
    # Who: User information
    user_sub: str | None
    user_email: str | None
    user_roles: list[str] | None
    
    # What: Action details
    action: AuditAction
    resource_type: str
    resource_id: uuid.UUID | None
    
    # Where: Tenant context
    district_id: uuid.UUID | None
    congregation_id: uuid.UUID | None
    
    # Details: Change information
    changes: dict[str, Any] | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    
    # Context: Request information
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    
    # Status
    status: AuditStatus
    error_message: str | None
    
    # Metadata
    metadata: dict[str, Any] | None
    
    # Timestamps
    created_at: datetime


class AuditLogCreate(NamedTuple):
    """Data for creating a new audit log entry."""

    # Timestamp (defaults to now if not provided)
    timestamp: datetime | None = None
    
    # Who: User information
    user_sub: str | None = None
    user_email: str | None = None
    user_roles: list[str] | None = None
    
    # What: Action details
    action: AuditAction
    resource_type: str
    resource_id: uuid.UUID | None = None
    
    # Where: Tenant context
    district_id: uuid.UUID | None = None
    congregation_id: uuid.UUID | None = None
    
    # Details: Change information
    changes: dict[str, Any] | None = None
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    
    # Context: Request information
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    
    # Status
    status: AuditStatus | None = None
    error_message: str | None = None
    
    # Metadata
    metadata: dict[str, Any] | None = None
