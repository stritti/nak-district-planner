"""Unit tests for Audit Service."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.audit_service import (
    AuditAction,
    AuditContext,
    AuditEvent,
    AuditStatus,
    AuditService,
)


class TestAuditContext:
    """Tests for AuditContext dataclass."""

    def test_default_values(self):
        """Test that AuditContext has default None values."""
        ctx = AuditContext()
        
        assert ctx.user_sub is None
        assert ctx.user_email is None
        assert ctx.user_roles is None
        assert ctx.district_id is None
        assert ctx.congregation_id is None
        assert ctx.ip_address is None
        assert ctx.user_agent is None
        assert ctx.request_id is None

    def test_with_values(self):
        """Test AuditContext with values."""
        import uuid
        
        ctx = AuditContext(
            user_sub="user-123",
            user_email="user@example.com",
            user_roles=["admin", "user"],
            district_id=uuid.uuid4(),
            congregation_id=uuid.uuid4(),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
        )
        
        assert ctx.user_sub == "user-123"
        assert ctx.user_email == "user@example.com"
        assert ctx.user_roles == ["admin", "user"]
        assert ctx.district_id is not None
        assert ctx.congregation_id is not None
        assert ctx.ip_address == "192.168.1.1"
        assert ctx.user_agent == "Mozilla/5.0"
        assert ctx.request_id == "req-123"


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""

    def test_default_values(self):
        """Test that AuditEvent has default values."""
        event = AuditEvent(
            action=AuditAction.CREATE,
            resource_type="user",
        )
        
        assert event.action == AuditAction.CREATE
        assert event.resource_type == "user"
        assert event.resource_id is None
        assert event.changes is None
        assert event.old_values is None
        assert event.new_values is None
        assert event.status == AuditStatus.SUCCESS
        assert event.error_message is None
        assert event.extra_metadata is None
        assert event.timestamp is None

    def test_with_all_values(self):
        """Test AuditEvent with all values."""
        import uuid
        
        timestamp = datetime.now(UTC)
        event = AuditEvent(
            action=AuditAction.DELETE,
            resource_type="event",
            resource_id=uuid.uuid4(),
            changes={"field": "value"},
            old_values={"old": "data"},
            new_values=None,
            status=AuditStatus.FAILED,
            error_message="Test error",
            extra_metadata={"key": "value"},
            timestamp=timestamp,
        )
        
        assert event.action == AuditAction.DELETE
        assert event.resource_type == "event"
        assert event.resource_id is not None
        assert event.changes == {"field": "value"}
        assert event.old_values == {"old": "data"}
        assert event.new_values is None
        assert event.status == AuditStatus.FAILED
        assert event.error_message == "Test error"
        assert event.extra_metadata == {"key": "value"}
        assert event.timestamp == timestamp


class TestAuditService:
    """Tests for AuditService class."""

    def test_init(self):
        """Test AuditService initialization."""
        service = AuditService()
        
        assert service._running is False
        assert service._writer_task is None
        assert service._queue is not None

    @pytest.mark.asyncio
    async def test_start(self):
        """Test starting the audit service."""
        service = AuditService()
        await service.start()
        
        assert service._running is True
        assert service._writer_task is not None

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping the audit service."""
        service = AuditService()
        await service.start()
        await service.stop()
        
        assert service._running is False
        assert service._writer_task is None

    @pytest.mark.asyncio
    async def test_log_queues_entry(self):
        """Test that log method queues entries."""
        service = AuditService()
        await service.start()
        
        # Mock the queue put method
        original_put = service._queue.put
        put_calls = []
        
        async def mock_put(item):
            put_calls.append(item)
            await original_put(item)
        
        service._queue.put = mock_put
        
        # Log an event
        await service.log(
            action=AuditAction.CREATE,
            resource_type="user",
        )
        
        # Check that entry was queued
        assert len(put_calls) == 1
        entry = put_calls[0]
        assert entry.action == AuditAction.CREATE
        assert entry.resource_type == "user"
        
        await service.stop()

    @pytest.mark.asyncio
    async def test_log_with_context(self):
        """Test logging with context."""
        import uuid
        
        service = AuditService()
        await service.start()
        
        context = AuditContext(
            user_sub="user-123",
            user_email="user@example.com",
            district_id=uuid.uuid4(),
        )
        
        put_calls = []
        original_put = service._queue.put
        
        async def mock_put(item):
            put_calls.append(item)
            await original_put(item)
        
        service._queue.put = mock_put
        
        await service.log(
            action=AuditAction.UPDATE,
            resource_type="event",
            resource_id=uuid.uuid4(),
            context=context,
            changes={"title": "new title"},
        )
        
        assert len(put_calls) == 1
        entry = put_calls[0]
        assert entry.user_sub == "user-123"
        assert entry.user_email == "user@example.com"
        assert entry.district_id == context.district_id
        assert entry.changes == {"title": "new title"}
        
        await service.stop()

    @pytest.mark.asyncio
    async def test_log_event(self):
        """Test logging with AuditEvent object."""
        service = AuditService()
        await service.start()
        
        event = AuditEvent(
            action=AuditAction.DELETE,
            resource_type="user",
            resource_id=None,
            status=AuditStatus.FAILED,
            error_message="Test error",
        )
        
        put_calls = []
        original_put = service._queue.put
        
        async def mock_put(item):
            put_calls.append(item)
            await original_put(item)
        
        service._queue.put = mock_put
        
        await service.log_event(event)
        
        assert len(put_calls) == 1
        entry = put_calls[0]
        assert entry.action == AuditAction.DELETE
        assert entry.status == AuditStatus.FAILED
        assert entry.error_message == "Test error"
        
        await service.stop()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test audit context manager."""
        service = AuditService()
        
        async with service.context(
            user_sub="user-123",
            user_email="user@example.com",
        ) as ctx:
            assert ctx.user_sub == "user-123"
            assert ctx.user_email == "user@example.com"

    @pytest.mark.asyncio
    async def test_double_start(self):
        """Test that starting twice doesn't cause issues."""
        service = AuditService()
        await service.start()
        await service.start()  # Should not raise
        
        assert service._running is True
        
        await service.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        """Test that stopping without starting doesn't cause issues."""
        service = AuditService()
        await service.stop()  # Should not raise
        
        assert service._running is False


class TestAuditAction:
    """Tests for AuditAction enum."""

    def test_action_values(self):
        """Test that all action values are strings."""
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DELETE.value == "DELETE"
        assert AuditAction.LOGIN.value == "LOGIN"
        assert AuditAction.LOGOUT.value == "LOGOUT"
        assert AuditAction.EXPORT.value == "EXPORT"
        assert AuditAction.IMPORT.value == "IMPORT"
        assert AuditAction.BULK_OPERATION.value == "BULK_OPERATION"


class TestAuditStatus:
    """Tests for AuditStatus enum."""

    def test_status_values(self):
        """Test that all status values are strings."""
        assert AuditStatus.SUCCESS.value == "success"
        assert AuditStatus.FAILED.value == "failed"
