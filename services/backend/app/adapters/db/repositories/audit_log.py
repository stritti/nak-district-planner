"""Audit Log Repository — Database operations for audit logs.

Provides async CRUD operations for audit log entries.
Audit logs are append-only and cannot be modified or deleted.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.audit_log import AuditAction, AuditLogORM, AuditStatus
from app.domain.models.audit_log import AuditLog, AuditLogCreate


class SqlAuditLogRepository:
    """SQLAlchemy repository for audit log operations."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.
        
        Args:
            session: Async SQLAlchemy session.
        """
        self.session = session

    async def create(self, audit_log: AuditLogCreate) -> AuditLog:
        """Create a new audit log entry.
        
        Args:
            audit_log: Audit log data to create.
            
        Returns:
            Created audit log with ID.
        """
        orm_audit_log = AuditLogORM(
            id=uuid.uuid4(),
            timestamp=audit_log.timestamp or datetime.now(UTC),
            user_sub=audit_log.user_sub,
            user_email=audit_log.user_email,
            user_roles=audit_log.user_roles,
            action=audit_log.action,
            resource_type=audit_log.resource_type,
            resource_id=audit_log.resource_id,
            district_id=audit_log.district_id,
            congregation_id=audit_log.congregation_id,
            changes=audit_log.changes,
            old_values=audit_log.old_values,
            new_values=audit_log.new_values,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            request_id=audit_log.request_id,
            status=audit_log.status or AuditStatus.SUCCESS,
            error_message=audit_log.error_message,
            extra_metadata=audit_log.extra_metadata,
            created_at=datetime.now(UTC),
        )
        
        self.session.add(orm_audit_log)
        await self.session.flush()
        
        return AuditLog(
            id=orm_audit_log.id,
            timestamp=orm_audit_log.timestamp,
            user_sub=orm_audit_log.user_sub,
            user_email=orm_audit_log.user_email,
            user_roles=orm_audit_log.user_roles,
            action=orm_audit_log.action,
            resource_type=orm_audit_log.resource_type,
            resource_id=orm_audit_log.resource_id,
            district_id=orm_audit_log.district_id,
            congregation_id=orm_audit_log.congregation_id,
            changes=orm_audit_log.changes,
            old_values=orm_audit_log.old_values,
            new_values=orm_audit_log.new_values,
            ip_address=orm_audit_log.ip_address,
            user_agent=orm_audit_log.user_agent,
            request_id=orm_audit_log.request_id,
            status=orm_audit_log.status,
            error_message=orm_audit_log.error_message,
            extra_metadata=orm_audit_log.extra_metadata,
            created_at=orm_audit_log.created_at,
        )

    async def get_by_id(self, audit_log_id: uuid.UUID) -> AuditLog | None:
        """Get an audit log entry by ID.
        
        Args:
            audit_log_id: ID of the audit log to retrieve.
            
        Returns:
            Audit log entry, or None if not found.
        """
        result = await self.session.execute(
            select(AuditLogORM).where(AuditLogORM.id == audit_log_id)
        )
        orm_audit_log = result.scalar_one_or_none()
        
        if orm_audit_log is None:
            return None
        
        return AuditLog(
            id=orm_audit_log.id,
            timestamp=orm_audit_log.timestamp,
            user_sub=orm_audit_log.user_sub,
            user_email=orm_audit_log.user_email,
            user_roles=orm_audit_log.user_roles,
            action=orm_audit_log.action,
            resource_type=orm_audit_log.resource_type,
            resource_id=orm_audit_log.resource_id,
            district_id=orm_audit_log.district_id,
            congregation_id=orm_audit_log.congregation_id,
            changes=orm_audit_log.changes,
            old_values=orm_audit_log.old_values,
            new_values=orm_audit_log.new_values,
            ip_address=orm_audit_log.ip_address,
            user_agent=orm_audit_log.user_agent,
            request_id=orm_audit_log.request_id,
            status=orm_audit_log.status,
            error_message=orm_audit_log.error_message,
            extra_metadata=orm_audit_log.extra_metadata,
            created_at=orm_audit_log.created_at,
        )

    async def list_by_user(
        self,
        user_sub: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs for a specific user.
        
        Args:
            user_sub: User subject (OIDC sub claim).
            limit: Maximum number of results.
            offset: Number of results to skip.
            
        Returns:
            List of audit log entries.
        """
        result = await self.session.execute(
            select(AuditLogORM)
            .where(AuditLogORM.user_sub == user_sub)
            .order_by(AuditLogORM.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        orm_audit_logs = result.scalars().all()
        
        return [
            AuditLog(
                id=orm.id,
                timestamp=orm.timestamp,
                user_sub=orm.user_sub,
                user_email=orm.user_email,
                user_roles=orm.user_roles,
                action=orm.action,
                resource_type=orm.resource_type,
                resource_id=orm.resource_id,
                district_id=orm.district_id,
                congregation_id=orm.congregation_id,
                changes=orm.changes,
                old_values=orm.old_values,
                new_values=orm.new_values,
                ip_address=orm.ip_address,
                user_agent=orm.user_agent,
                request_id=orm.request_id,
                status=orm.status,
                error_message=orm.error_message,
                extra_metadata=orm.extra_metadata,
                created_at=orm.created_at,
            )
            for orm in orm_audit_logs
        ]

    async def list_by_resource(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs for a specific resource.
        
        Args:
            resource_type: Type of resource (e.g., 'event', 'user').
            resource_id: ID of the resource.
            limit: Maximum number of results.
            offset: Number of results to skip.
            
        Returns:
            List of audit log entries.
        """
        result = await self.session.execute(
            select(AuditLogORM)
            .where(
                and_(
                    AuditLogORM.resource_type == resource_type,
                    AuditLogORM.resource_id == resource_id,
                )
            )
            .order_by(AuditLogORM.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        orm_audit_logs = result.scalars().all()
        
        return [
            AuditLog(
                id=orm.id,
                timestamp=orm.timestamp,
                user_sub=orm.user_sub,
                user_email=orm.user_email,
                user_roles=orm.user_roles,
                action=orm.action,
                resource_type=orm.resource_type,
                resource_id=orm.resource_id,
                district_id=orm.district_id,
                congregation_id=orm.congregation_id,
                changes=orm.changes,
                old_values=orm.old_values,
                new_values=orm.new_values,
                ip_address=orm.ip_address,
                user_agent=orm.user_agent,
                request_id=orm.request_id,
                status=orm.status,
                error_message=orm.error_message,
                extra_metadata=orm.extra_metadata,
                created_at=orm.created_at,
            )
            for orm in orm_audit_logs
        ]

    async def list_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs within a time range.
        
        Args:
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum number of results.
            offset: Number of results to skip.
            
        Returns:
            List of audit log entries.
        """
        result = await self.session.execute(
            select(AuditLogORM)
            .where(
                and_(
                    AuditLogORM.timestamp >= start_time,
                    AuditLogORM.timestamp <= end_time,
                )
            )
            .order_by(AuditLogORM.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        orm_audit_logs = result.scalars().all()
        
        return [
            AuditLog(
                id=orm.id,
                timestamp=orm.timestamp,
                user_sub=orm.user_sub,
                user_email=orm.user_email,
                user_roles=orm.user_roles,
                action=orm.action,
                resource_type=orm.resource_type,
                resource_id=orm.resource_id,
                district_id=orm.district_id,
                congregation_id=orm.congregation_id,
                changes=orm.changes,
                old_values=orm.old_values,
                new_values=orm.new_values,
                ip_address=orm.ip_address,
                user_agent=orm.user_agent,
                request_id=orm.request_id,
                status=orm.status,
                error_message=orm.error_message,
                extra_metadata=orm.extra_metadata,
                created_at=orm.created_at,
            )
            for orm in orm_audit_logs
        ]

    async def list_by_action(
        self,
        action: AuditAction,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs by action type.
        
        Args:
            action: Type of action to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.
            
        Returns:
            List of audit log entries.
        """
        result = await self.session.execute(
            select(AuditLogORM)
            .where(AuditLogORM.action == action)
            .order_by(AuditLogORM.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        orm_audit_logs = result.scalars().all()
        
        return [
            AuditLog(
                id=orm.id,
                timestamp=orm.timestamp,
                user_sub=orm.user_sub,
                user_email=orm.user_email,
                user_roles=orm.user_roles,
                action=orm.action,
                resource_type=orm.resource_type,
                resource_id=orm.resource_id,
                district_id=orm.district_id,
                congregation_id=orm.congregation_id,
                changes=orm.changes,
                old_values=orm.old_values,
                new_values=orm.new_values,
                ip_address=orm.ip_address,
                user_agent=orm.user_agent,
                request_id=orm.request_id,
                status=orm.status,
                error_message=orm.error_message,
                extra_metadata=orm.extra_metadata,
                created_at=orm.created_at,
            )
            for orm in orm_audit_logs
        ]
