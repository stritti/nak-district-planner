# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Unit tests for Audit Service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.audit_service import (
    AuditAction,
    AuditContext,
    AuditEvent,
    AuditPersistenceError,
    AuditService,
    AuditStatus,
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
    """Entries are written synchronously and durably, or the caller is told (#648)."""

    @staticmethod
    def _session(commit_error: Exception | None = None):
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.add = MagicMock()  # AsyncSession.add is synchronous
        session.commit.side_effect = commit_error
        return session

    @pytest.mark.asyncio
    async def test_record_commits_before_returning(self):
        session = self._session()
        with patch("app.application.audit_service.AsyncSessionLocal", return_value=session):
            await AuditService().log(action=AuditAction.CREATE, resource_type="user")

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_failed_commit_raises_and_rolls_back(self):
        session = self._session(commit_error=RuntimeError("commit rejected"))
        with (
            patch("app.application.audit_service.AsyncSessionLocal", return_value=session),
            pytest.raises(AuditPersistenceError),
        ):
            await AuditService().log(action=AuditAction.CREATE, resource_type="user")

        session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_a_session_that_cannot_be_opened_raises(self):
        with (
            patch(
                "app.application.audit_service.AsyncSessionLocal",
                side_effect=RuntimeError("DB connection failed"),
            ),
            pytest.raises(AuditPersistenceError),
        ):
            await AuditService().log(action=AuditAction.CREATE, resource_type="user")

    @pytest.mark.asyncio
    async def test_a_failure_is_counted_and_logged_without_payload(self, caplog):
        session = self._session(commit_error=RuntimeError("secret-token-123 in message"))
        with (
            patch("app.application.audit_service.AsyncSessionLocal", return_value=session),
            patch("app.application.audit_service.audit_write_failures") as counter,
            pytest.raises(AuditPersistenceError),
        ):
            await AuditService().log(
                action=AuditAction.UPDATE,
                resource_type="user",
                extra_metadata={"path": "/api/v1/export/secret-path-456"},
            )

        counter.add.assert_called_once_with(1, {"stage": "durable"})
        assert "secret-token-123" not in caplog.text
        assert "secret-path-456" not in caplog.text
        assert "RuntimeError" in caplog.text

    @pytest.mark.asyncio
    async def test_the_system_worker_context_is_set_for_the_insert(self):
        session = self._session()
        with patch("app.application.audit_service.AsyncSessionLocal", return_value=session):
            await AuditService().log(action=AuditAction.CREATE, resource_type="user")

        statement = str(session.execute.await_args_list[0].args[0])
        assert "app.is_system_worker" in statement

    @pytest.mark.asyncio
    async def test_log_builds_the_entry_from_context(self):
        import uuid

        service = AuditService()
        service.record = AsyncMock()
        context = AuditContext(user_sub="user-123", user_email="user@example.com", district_id=uuid.uuid4())

        await service.log(
            action=AuditAction.UPDATE,
            resource_type="event",
            resource_id=uuid.uuid4(),
            context=context,
            changes={"title": "new title"},
        )

        entry = service.record.await_args.args[0]
        assert entry.user_sub == "user-123"
        assert entry.user_email == "user@example.com"
        assert entry.district_id == context.district_id
        assert entry.changes == {"title": "new title"}
        assert entry.timestamp is not None

    @pytest.mark.asyncio
    async def test_log_event_and_batch_write_every_event(self):
        service = AuditService()
        service.record = AsyncMock()
        events = [
            AuditEvent(action=AuditAction.CREATE, resource_type="user"),
            AuditEvent(
                action=AuditAction.DELETE,
                resource_type="leader",
                status=AuditStatus.FAILED,
                error_message="Test error",
                extra_metadata={"key": "value"},
            ),
        ]

        await service.log_batch(events)

        entries = [call.args[0] for call in service.record.await_args_list]
        assert [e.action for e in entries] == [AuditAction.CREATE, AuditAction.DELETE]
        assert entries[1].status == AuditStatus.FAILED
        assert entries[1].error_message == "Test error"
        assert entries[1].extra_metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with AuditService().context(user_sub="user-123", user_email="user@example.com") as ctx:
            assert ctx.user_sub == "user-123"
            assert ctx.user_email == "user@example.com"

    def test_there_is_no_in_memory_queue_to_lose_entries_from(self):
        service = AuditService()
        assert not hasattr(service, "_queue")
        assert not hasattr(service, "start")
        assert not hasattr(service, "stop")


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
