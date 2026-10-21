# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Audit Service — Business logic for audit logging.

Provides a high-level interface for creating audit log entries. Entries are
written synchronously so that a failure is visible to the caller (#648).
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from opentelemetry import metrics
from sqlalchemy import text

from app.adapters.db.repositories.audit_log import SqlAuditLogRepository
from app.adapters.db.session import AsyncSessionLocal
from app.domain.models.audit_log import AuditAction, AuditLogCreate, AuditStatus

logger = logging.getLogger(__name__)


@dataclass
class AuditContext:
    """Context for audit logging.

    Contains information that is common across multiple audit log entries
    within the same request or operation.
    """

    user_sub: str | None = None
    user_email: str | None = None
    user_roles: list[str] | None = None
    district_id: uuid.UUID | None = None
    congregation_id: uuid.UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


@dataclass
class AuditEvent:
    """Represents an audit event to be logged."""

    action: AuditAction
    resource_type: str
    resource_id: uuid.UUID | None = None
    changes: dict[str, Any] | None = None
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    status: AuditStatus = AuditStatus.SUCCESS
    error_message: str | None = None
    extra_metadata: dict[str, Any] | None = None
    timestamp: datetime | None = None


class AuditPersistenceError(RuntimeError):
    """An audit entry could not be made durable; the caller must not report an audited result."""


_meter = metrics.get_meter("nak.audit")
audit_write_failures = _meter.create_counter(
    "nak.audit.write_failures",
    unit="{entry}",
    description="Audit entries that could not be persisted (the request is answered with 503)",
)


class AuditService:
    """Service for creating audit log entries.

    Entries are written synchronously and durably: ``record`` returns only after
    the entry is committed, and raises ``AuditPersistenceError`` otherwise. There is
    no queue; an entry that cannot be written is never silently dropped.
    """

    async def record(self, audit_log: AuditLogCreate) -> None:
        """Persist one entry in its own short transaction (system-worker context)."""
        try:
            async with AsyncSessionLocal() as session:
                # The audit writer is a system task: the entry is built by server code.
                await session.execute(
                    text("SELECT set_config('app.is_system_worker', 'true', true)")
                )
                try:
                    await SqlAuditLogRepository(session).create(audit_log)
                    await session.commit()
                except BaseException:
                    await session.rollback()
                    raise
        except Exception as exc:
            audit_write_failures.add(1, {"stage": "durable"})
            # Type only: neither the entry nor the database message may reach the logs.
            logger.error("Audit entry could not be persisted (%s)", type(exc).__name__)
            raise AuditPersistenceError("audit entry not persisted") from exc

    async def log(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        context: AuditContext | None = None,
        changes: dict[str, Any] | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        error_message: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event.

        Args:
            action: Type of action being performed.
            resource_type: Type of resource being affected.
            resource_id: ID of the resource being affected.
            context: Request context for the audit log.
            changes: Dictionary describing the changes made.
            old_values: Previous values of the resource (for DELETE/UPDATE).
            new_values: New values of the resource (for CREATE/UPDATE).
            status: Status of the action (success/failed).
            error_message: Error message if action failed.
            extra_metadata: Additional metadata to store.
        """
        audit_log = AuditLogCreate(
            timestamp=datetime.now(UTC),
            user_sub=context.user_sub if context else None,
            user_email=context.user_email if context else None,
            user_roles=context.user_roles if context else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            district_id=context.district_id if context else None,
            congregation_id=context.congregation_id if context else None,
            changes=changes,
            old_values=old_values,
            new_values=new_values,
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
            request_id=context.request_id if context else None,
            status=status,
            error_message=error_message,
            extra_metadata=extra_metadata,
        )

        await self.record(audit_log)

    async def log_event(
        self,
        event: AuditEvent,
        context: AuditContext | None = None,
    ) -> None:
        """Log an audit event using an AuditEvent object.

        Args:
            event: The audit event to log.
            context: Request context for the audit log.
        """
        await self.log(
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            context=context,
            changes=event.changes,
            old_values=event.old_values,
            new_values=event.new_values,
            status=event.status,
            error_message=event.error_message,
            extra_metadata=event.extra_metadata,
        )

    async def log_batch(
        self,
        events: list[AuditEvent],
        context: AuditContext | None = None,
    ) -> None:
        """Log multiple audit events in a batch.

        Args:
            events: List of audit events to log.
            context: Request context for all audit logs.
        """
        for event in events:
            await self.log_event(event, context)

    @asynccontextmanager
    async def context(
        self,
        user_sub: str | None = None,
        user_email: str | None = None,
        user_roles: list[str] | None = None,
        district_id: uuid.UUID | None = None,
        congregation_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ):
        """Context manager for request-scoped audit context.

        Args:
            user_sub: User subject (OIDC sub claim).
            user_email: User email address.
            user_roles: List of user roles.
            district_id: Current district ID.
            congregation_id: Current congregation ID.
            ip_address: Client IP address.
            user_agent: Client user agent.
            request_id: Unique request ID.

        Yields:
            AuditContext object for use in audit logging.
        """
        ctx = AuditContext(
            user_sub=user_sub,
            user_email=user_email,
            user_roles=user_roles,
            district_id=district_id,
            congregation_id=congregation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        yield ctx


# Global audit service instance
audit_service = AuditService()
