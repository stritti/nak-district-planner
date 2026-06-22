"""Unit tests for Audit Middleware.

Tests cover the AuditMiddleware class and its methods.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from app.adapters.api.middleware.audit import AuditMiddleware
from app.application.audit_service import AuditAction, AuditContext, AuditStatus


@pytest.fixture
def mock_app():
    """Create a mock ASGI app."""
    return MagicMock()


@pytest.fixture
def middleware(mock_app):
    """Create an AuditMiddleware instance with mock app."""
    return AuditMiddleware(
        app=mock_app,
        exempt_paths={"/api/health"},
        exempt_methods={"GET", "HEAD", "OPTIONS"},
    )


class TestGetClientIP:
    """Tests for _get_client_ip method."""

    def test_x_forwarded_for(self, middleware):
        """Test extraction from x-forwarded-for header."""
        request = MagicMock(spec=Request)
        request.headers.get.side_effect = lambda key, default=None: {
            "x-forwarded-for": "203.0.113.1, 198.51.100.2",
        }.get(key.lower(), default)

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_x_real_ip(self, middleware):
        """Test extraction from x-real-ip header."""
        request = MagicMock(spec=Request)
        request.headers.get.side_effect = lambda key, default=None: {
            "x-real-ip": "10.0.0.1",
        }.get(key.lower(), default)

        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_client_host_fallback(self, middleware):
        """Test fallback to request.client.host."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        request.client.host = "192.168.1.1"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_no_ip_available(self, middleware):
        """Test None when no IP source is available."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip is None


class TestShouldLogAudit:
    """Tests for _should_log_audit method."""

    def test_exempt_path_returns_false(self, middleware):
        """Test that exempt paths are not logged."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/health"
        request.method = "POST"

        assert middleware._should_log_audit(request) is False

    def test_exempt_method_returns_false(self, middleware):
        """Test that exempt methods are not logged."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/events"
        request.method = "GET"

        assert middleware._should_log_audit(request) is False

    def test_non_exempt_returns_true(self, middleware):
        """Test that non-exempt paths/methods are logged."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/events"
        request.method = "POST"

        assert middleware._should_log_audit(request) is True


class TestGetActionFromMethod:
    """Tests for _get_action_from_method method."""

    def test_post_resource_creates(self, middleware):
        """Test POST on resource path returns CREATE."""
        action = middleware._get_action_from_method("POST", "/api/v1/events")
        assert action == AuditAction.CREATE

    def test_post_command_updates(self, middleware):
        """Test POST on command-style path returns UPDATE."""
        action = middleware._get_action_from_method("POST", "/api/v1/events/bulk-approve")
        assert action == AuditAction.UPDATE

    def test_put_updates(self, middleware):
        """Test PUT returns UPDATE."""
        action = middleware._get_action_from_method("PUT", "/api/v1/events/123")
        assert action == AuditAction.UPDATE

    def test_patch_updates(self, middleware):
        """Test PATCH returns UPDATE."""
        action = middleware._get_action_from_method("PATCH", "/api/v1/events/123")
        assert action == AuditAction.UPDATE

    def test_delete_deletes(self, middleware):
        """Test DELETE returns DELETE."""
        action = middleware._get_action_from_method("DELETE", "/api/v1/events/123")
        assert action == AuditAction.DELETE

    def test_unknown_method(self, middleware):
        """Test unknown HTTP method defaults to UPDATE."""
        action = middleware._get_action_from_method("OPTIONS", "/api/v1/events")
        assert action == AuditAction.UPDATE


class TestIsCommandAction:
    """Tests for _is_command_action static method."""

    def test_uuid_segment_not_command(self):
        """Test UUID segment is not a command."""
        path = f"/api/v1/events/{uuid.uuid4()}"
        assert AuditMiddleware._is_command_action(path) is False

    def test_resource_name_not_command(self):
        """Test known resource name is not a command."""
        path = "/api/v1/events"
        assert AuditMiddleware._is_command_action(path) is False

    def test_multi_word_is_command(self):
        """Test multi-word/hyphenated segment is a command."""
        path = "/api/v1/events/bulk-approve"
        assert AuditMiddleware._is_command_action(path) is True


class TestGetResourceType:
    """Tests for _get_resource_type method."""

    def test_simple_path(self, middleware):
        """Test simple path returns the first resource segment."""
        assert middleware._get_resource_type("/api/v1/events") == "events"

    def test_nested_path_with_uuid(self, middleware):
        """Test nested path returns segment before last UUID."""
        eid = uuid.uuid4()
        aid = uuid.uuid4()
        path = f"/api/v1/events/{eid}/assignments/{aid}"
        assert middleware._get_resource_type(path) == "assignments"

    def test_path_without_uuid(self, middleware):
        """Test path without UUID returns first segment."""
        assert middleware._get_resource_type("/api/v1/events/summary") == "events"

    def test_empty_path(self, middleware):
        """Test empty path returns empty string."""
        assert middleware._get_resource_type("") == ""


class TestExtractResourceId:
    """Tests for _extract_resource_id method."""

    def test_path_with_uuid(self, middleware):
        """Test path with UUID returns UUID object."""
        eid = uuid.uuid4()
        path = f"/api/v1/events/{eid}"
        result = middleware._extract_resource_id(path)
        assert result == eid

    def test_nested_uuid_returns_last(self, middleware):
        """Test nested UUIDs returns the last one."""
        did = uuid.uuid4()
        eid = uuid.uuid4()
        path = f"/api/v1/districts/{did}/events/{eid}"
        result = middleware._extract_resource_id(path)
        assert result == eid

    def test_path_without_uuid(self, middleware):
        """Test path without UUID returns None."""
        result = middleware._extract_resource_id("/api/v1/events")
        assert result is None

    def test_invalid_uuid_returns_none(self, middleware):
        """Test path with invalid UUID returns None."""
        result = middleware._extract_resource_id("/api/v1/events/not-a-uuid")
        assert result is None


class TestExtractContext:
    """Tests for _extract_context method."""

    def test_with_user(self, middleware):
        """Test context extraction with user in request.state."""
        request = MagicMock(spec=Request)
        request.state.user = MagicMock()
        request.state.user.sub = "user-123"
        request.state.user.email = "user@example.com"
        request.state.user_roles = ["admin"]
        request.state.district_id = uuid.uuid4()
        request.state.congregation_id = uuid.uuid4()
        request.path_params = {}

        ctx = middleware._extract_context(
            request,
            request_id="req-1",
            ip_address="10.0.0.1",
            user_agent="test-agent",
        )

        assert ctx.user_sub == "user-123"
        assert ctx.user_email == "user@example.com"
        assert ctx.user_roles == ["admin"]
        assert ctx.district_id == request.state.district_id
        assert ctx.congregation_id == request.state.congregation_id
        assert ctx.ip_address == "10.0.0.1"
        assert ctx.user_agent == "test-agent"
        assert ctx.request_id == "req-1"

    def test_without_user(self, middleware):
        """Test context extraction without user."""
        request = MagicMock(spec=Request)
        request.state.user = None
        request.path_params = {}

        ctx = middleware._extract_context(request, request_id="req-2")

        assert ctx.user_sub is None
        assert ctx.user_email is None

    def test_no_state_attrs(self, middleware):
        """Test context extraction when state has no attrs."""
        request = MagicMock(spec=Request)
        # Simulate request.state having no user attribute
        del request.state.user
        del request.state.user_roles
        del request.state.district_id
        del request.state.congregation_id
        request.path_params = {}

        ctx = middleware._extract_context(request, request_id="req-3")

        assert ctx.user_sub is None
        assert ctx.user_roles is None

    def test_with_path_params_tenant(self, middleware):
        """Test tenant context from path params."""
        did = uuid.uuid4()
        cid = uuid.uuid4()
        request = MagicMock(spec=Request)
        request.state.user = None
        request.path_params = {"district_id": str(did), "congregation_id": str(cid)}

        ctx = middleware._extract_context(request, request_id="req-4")

        assert ctx.district_id == str(did)
        assert ctx.congregation_id == str(cid)

    def test_user_roles_from_state(self, middleware):
        """Test user_roles extraction from request.state."""
        request = MagicMock(spec=Request)
        request.state.user = MagicMock()
        request.state.user.sub = "user-456"
        request.state.user_roles = ["planner", "viewer"]
        request.path_params = {}

        ctx = middleware._extract_context(request, request_id="req-5")

        assert ctx.user_roles == ["planner", "viewer"]


class TestLogAuditEvent:
    """Tests for _log_audit_event method."""

    @pytest.mark.asyncio
    async def test_successful_request(self, middleware):
        """Test logging a successful request."""
        middleware.audit_service = AsyncMock()

        request = MagicMock(spec=Request)
        request.method = "POST"
        url_mock = MagicMock()
        url_mock.path = "/api/v1/events"
        request.url = url_mock
        response = MagicMock()
        response.status_code = 201
        response.headers = {}
        context = AuditContext(request_id="req-1")

        await middleware._log_audit_event(
            request=request,
            response=response,
            error=None,
            context=context,
            request_id="req-1",
            duration=0.1,
        )

        middleware.audit_service.log.assert_called_once()
        call_kwargs = middleware.audit_service.log.call_args.kwargs
        assert call_kwargs["status"] == AuditStatus.SUCCESS
        assert call_kwargs["action"] == AuditAction.CREATE

    @pytest.mark.asyncio
    async def test_error_request(self, middleware):
        """Test logging a request that raised an exception."""
        middleware.audit_service = AsyncMock()

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/events"
        context = AuditContext(request_id="req-2")
        error = ValueError("Something went wrong")

        await middleware._log_audit_event(
            request=request,
            response=None,
            error=error,
            context=context,
            request_id="req-2",
            duration=0.1,
        )

        middleware.audit_service.log.assert_called_once()
        call_kwargs = middleware.audit_service.log.call_args.kwargs
        assert call_kwargs["status"] == AuditStatus.FAILED
        assert "Something went wrong" in call_kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_http_error_response(self, middleware):
        """Test logging a 400+ response."""
        middleware.audit_service = AsyncMock()

        request = MagicMock(spec=Request)
        request.method = "POST"
        url_mock = MagicMock()
        url_mock.path = "/api/v1/events"
        request.url = url_mock
        response = MagicMock()
        response.status_code = 404
        response.headers = {}
        context = AuditContext(request_id="req-3")

        await middleware._log_audit_event(
            request=request,
            response=response,
            error=None,
            context=context,
            request_id="req-3",
            duration=0.1,
        )

        middleware.audit_service.log.assert_called_once()
        call_kwargs = middleware.audit_service.log.call_args.kwargs
        assert call_kwargs["status"] == AuditStatus.FAILED
        assert "HTTP 404" in call_kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_create_with_location_header(self, middleware):
        """Test CREATE response with Location header extracts resource_id."""
        middleware.audit_service = AsyncMock()

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/events"
        response = MagicMock()
        response.status_code = 201
        eid = uuid.uuid4()
        response.headers = {"Location": f"/api/v1/events/{eid}"}
        context = AuditContext(request_id="req-4")

        await middleware._log_audit_event(
            request=request,
            response=response,
            error=None,
            context=context,
            request_id="req-4",
            duration=0.1,
        )

        middleware.audit_service.log.assert_called_once()
        call_kwargs = middleware.audit_service.log.call_args.kwargs
        assert call_kwargs["resource_id"] == eid

    @pytest.mark.asyncio
    async def test_audit_service_exception_caught(self, middleware):
        """Test that exceptions from audit_service.log are caught."""
        middleware.audit_service = AsyncMock()
        middleware.audit_service.log.side_effect = RuntimeError("Audit service down")

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/events"
        response = MagicMock()
        response.status_code = 201
        context = AuditContext(request_id="req-5")

        # Should not raise
        await middleware._log_audit_event(
            request=request,
            response=response,
            error=None,
            context=context,
            request_id="req-5",
            duration=0.1,
        )


class TestDispatch:
    """Tests for dispatch method."""

    @pytest.mark.asyncio
    async def test_successful_request(self, middleware):
        """Test dispatch returns response and logs audit."""
        middleware._should_log_audit = MagicMock(return_value=True)
        middleware._extract_context = MagicMock(return_value=AuditContext(request_id="req-1"))
        middleware._log_audit_event = AsyncMock()

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/events"
        request.headers.get.return_value = None
        request.client = None

        expected_response = MagicMock()
        call_next = AsyncMock(return_value=expected_response)

        response = await middleware.dispatch(request, call_next)

        assert response == expected_response
        middleware._log_audit_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_in_request(self, middleware):
        """Test exception in request is re-raised after audit log."""
        middleware._should_log_audit = MagicMock(return_value=True)
        middleware._extract_context = MagicMock(return_value=AuditContext(request_id="req-2"))
        middleware._log_audit_event = AsyncMock()

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/events"
        request.headers.get.return_value = None
        request.client = None

        call_next = AsyncMock(side_effect=ValueError("Request failed"))

        with pytest.raises(ValueError, match="Request failed"):
            await middleware.dispatch(request, call_next)

        middleware._log_audit_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_exempt_path_no_audit(self, middleware):
        """Test exempt path does not log audit."""
        middleware._should_log_audit = MagicMock(return_value=False)

        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/health"

        call_next = AsyncMock(return_value=MagicMock())

        response = await middleware.dispatch(request, call_next)

        assert response is not None


class TestInitialization:
    """Tests for AuditMiddleware initialization."""

    def test_default_exemptions(self):
        """Test default exempt paths and methods."""
        middleware = AuditMiddleware(app=MagicMock())
        assert "/api/health" in middleware.exempt_paths
        assert "GET" in middleware.exempt_methods
        assert "HEAD" in middleware.exempt_methods
        assert "OPTIONS" in middleware.exempt_methods

    def test_custom_exemptions(self):
        """Test custom exempt paths and methods."""
        middleware = AuditMiddleware(
            app=MagicMock(),
            exempt_paths={"/api/custom"},
            exempt_methods={"PUT"},
        )
        assert "/api/custom" in middleware.exempt_paths
        assert "/api/health" not in middleware.exempt_paths
        assert "PUT" in middleware.exempt_methods
        assert "GET" not in middleware.exempt_methods
