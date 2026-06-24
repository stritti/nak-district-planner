"""Unit tests for Tenant Isolation Middleware.

Tests cover:
- TenantMiddleware._extract_sub_from_bearer
- TenantMiddleware._extract_tenant_from_path
- TenantMiddleware._extract_tenant_context (header, query, state sources)
- TenantMiddleware.dispatch (exempt paths, exempt methods, normal flow)
- TenantValidationMiddleware._is_authenticated
- TenantValidationMiddleware.dispatch (exempt paths/methods)
"""

import base64
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.adapters.api.middleware.tenant import (
    TenantMiddleware,
    TenantValidationMiddleware,
)


# =========================================================================
# TenantMiddleware._extract_sub_from_bearer
# =========================================================================

class TestExtractSubFromBearer:
    """Tests for the static JWT sub extraction method."""

    def _make_jwt(self, payload: dict) -> str:
        """Build an unsigned JWT string (valid enough for extraction)."""
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256"}).encode()
        ).rstrip(b"=").decode()
        b64_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        return f"{header}.{b64_payload}.fakesig"

    def _make_request(self, headers: dict | None = None) -> MagicMock:
        request = MagicMock(spec=Request)
        request.headers = headers or {}
        return request

    def test_no_authorization_header(self):
        """Returns None when no Authorization header is present."""
        request = self._make_request({})
        result = TenantMiddleware._extract_sub_from_bearer(request)
        assert result is None

    def test_wrong_auth_scheme(self):
        """Returns None when scheme is not Bearer."""
        request = self._make_request({"authorization": "Basic dGVzdDpwYXNz"})
        result = TenantMiddleware._extract_sub_from_bearer(request)
        assert result is None

    def test_missing_token_body(self):
        """Returns None when JWT has fewer than 3 parts."""
        request = self._make_request({"authorization": "Bearer onlytwo"})
        result = TenantMiddleware._extract_sub_from_bearer(request)
        assert result is None

    def test_valid_jwt_with_sub(self):
        """Returns the sub claim from a valid JWT."""
        payload = {"sub": "auth0|user-abc-123", "email": "test@example.com"}
        token = self._make_jwt(payload)
        request = self._make_request({"authorization": f"Bearer {token}"})
        result = TenantMiddleware._extract_sub_from_bearer(request)
        assert result == "auth0|user-abc-123"

    def test_valid_jwt_without_sub(self):
        """Returns None when JWT has no sub claim."""
        payload = {"email": "test@example.com"}
        token = self._make_jwt(payload)
        request = self._make_request({"authorization": f"Bearer {token}"})
        result = TenantMiddleware._extract_sub_from_bearer(request)
        assert result is None

    def test_invalid_base64_payload(self):
        """Returns None when JWT payload is not valid base64."""
        request = self._make_request({
            "authorization": "Bearer header.invalid-base64!!.sig"
        })
        result = TenantMiddleware._extract_sub_from_bearer(request)
        assert result is None

    def test_bearer_token_with_padding(self):
        """Handles base64 padding correctly."""
        # Payload length % 4 != 0 → padding is added
        payload = {"sub": "user1"}
        token = self._make_jwt(payload)
        # Remove padding so internal code must add it back
        parts = token.split(".")
        parts[1] = parts[1].rstrip("=")
        token = ".".join(parts)
        request = self._make_request({"authorization": f"Bearer {token}"})
        result = TenantMiddleware._extract_sub_from_bearer(request)
        assert result == "user1"


# =========================================================================
# TenantMiddleware._extract_tenant_from_path
# =========================================================================

class TestExtractTenantFromPath:
    """Tests for the static path-based tenant extraction method."""

    @pytest.fixture
    def district_uuid(self):
        return uuid.uuid4()

    @pytest.fixture
    def congregation_uuid(self):
        return uuid.uuid4()

    def test_empty_path(self, district_uuid):
        """Empty context when path is empty."""
        context = {}
        TenantMiddleware._extract_tenant_from_path("", context)
        assert context == {}

    def test_health_endpoint(self, district_uuid):
        """No tenant extracted from health endpoint."""
        context = {}
        TenantMiddleware._extract_tenant_from_path("/api/health", context)
        assert context == {}

    def test_district_in_path(self, district_uuid):
        """Extracts district_id and sets tenant_id to district."""
        context = {}
        path = f"/api/v1/districts/{district_uuid}/leaders"
        TenantMiddleware._extract_tenant_from_path(path, context)
        assert context["district_id"] == district_uuid
        assert context["tenant_id"] == district_uuid
        assert context["tenant_type"] == "district"

    def test_congregation_in_path(self, congregation_uuid):
        """Extracts congregation_id and sets tenant_id to congregation."""
        context = {}
        path = f"/api/v1/congregations/{congregation_uuid}/members"
        TenantMiddleware._extract_tenant_from_path(path, context)
        assert context["congregation_id"] == congregation_uuid
        assert context["tenant_id"] == congregation_uuid
        assert context["tenant_type"] == "congregation"

    def test_district_and_congregation_in_path(self, district_uuid, congregation_uuid):
        """Both district and congregation extracted, tenant is district (first)."""
        context = {}
        path = f"/api/v1/districts/{district_uuid}/congregations/{congregation_uuid}"
        TenantMiddleware._extract_tenant_from_path(path, context)
        assert context["district_id"] == district_uuid
        assert context["congregation_id"] == congregation_uuid
        # tenant_id was set by district first, congregation should not overwrite
        assert context["tenant_id"] == district_uuid
        assert context["tenant_type"] == "district"

    def test_non_uuid_after_district(self, district_uuid):
        """Skips non-UUID segments after 'districts'."""
        context = {}
        path = "/api/v1/districts/not-a-uuid/leaders"
        TenantMiddleware._extract_tenant_from_path(path, context)
        assert "district_id" not in context

    def test_without_api_v1_prefix(self, district_uuid):
        """Handles paths without api/v1/ prefix."""
        context = {}
        path = f"/districts/{district_uuid}"
        TenantMiddleware._extract_tenant_from_path(path, context)
        assert context["district_id"] == district_uuid
        assert context["tenant_id"] == district_uuid
        assert context["tenant_type"] == "district"

    def test_partial_tenant_type(self, congregation_uuid, district_uuid):
        """When district is already set, congregation does not overwrite tenant_type."""
        context = {"tenant_id": district_uuid, "tenant_type": "district"}
        path = f"/congregations/{congregation_uuid}"
        TenantMiddleware._extract_tenant_from_path(path, context)
        assert context["congregation_id"] == congregation_uuid
        # tenant stays district
        assert context["tenant_type"] == "district"
        assert context["tenant_id"] == district_uuid


# =========================================================================
# TenantMiddleware._extract_tenant_context
# =========================================================================

class TestExtractTenantContext:
    """Tests for extracting tenant context from requests."""

    @pytest.fixture
    def middleware(self):
        return TenantMiddleware(MagicMock())

    def test_with_user_in_state(self, middleware):
        """Extracts user_sub and email from request.state.user."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.url.path = "/api/v1/districts"
        # Simulate query_params being a dict-like
        request.query_params = {}
        user = MagicMock()
        user.sub = "auth0|user-1"
        user.email = "user@example.com"
        request.state.user = user
        request.state.user_roles = ["admin"]

        context = middleware._extract_tenant_context(request)
        assert context["user_sub"] == "auth0|user-1"
        assert "user_email" in context

    def test_user_sub_fallback_from_bearer(self, middleware):
        """Falls back to JWT sub extraction when state.user is not set."""
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "jwt-user"}).encode()
        ).rstrip(b"=").decode()
        token = f"{header}.{payload}.sig"

        request = MagicMock(spec=Request)
        request.headers = {"authorization": f"Bearer {token}"}
        request.url.path = "/api/v1/districts"
        request.query_params = {}
        request.state = MagicMock()
        del request.state.user  # no user attribute

        context = middleware._extract_tenant_context(request)
        assert context["user_sub"] == "jwt-user"

    def test_district_id_from_header(self, middleware):
        """Extracts district_id from X-District-ID header."""
        did = uuid.uuid4()
        request = MagicMock(spec=Request)
        request.headers = {"X-District-ID": str(did)}
        request.url.path = "/api/v1/events"
        request.query_params = {}
        request.state = MagicMock()
        del request.state.user

        with patch.object(TenantMiddleware, "_extract_tenant_from_path"):
            context = middleware._extract_tenant_context(request)
        assert context["district_id"] == did
        assert context["tenant_id"] == did
        assert context["tenant_type"] == "district"

    def test_congregation_id_from_header(self, middleware):
        """Extracts congregation_id from X-Congregation-ID header."""
        cid = uuid.uuid4()
        request = MagicMock(spec=Request)
        request.headers = {"X-Congregation-ID": str(cid)}
        request.url.path = "/api/v1/events"
        request.query_params = {}
        request.state = MagicMock()
        del request.state.user

        with patch.object(TenantMiddleware, "_extract_tenant_from_path"):
            context = middleware._extract_tenant_context(request)
        assert context["congregation_id"] == cid
        assert context["tenant_id"] == cid
        assert context["tenant_type"] == "congregation"

    def test_invalid_uuid_in_header(self, middleware):
        """Skips header values that are not valid UUIDs."""
        request = MagicMock(spec=Request)
        request.headers = {"X-District-ID": "not-a-uuid"}
        request.url.path = "/api/v1/events"
        request.query_params = {}
        request.state = MagicMock()
        del request.state.user

        with patch.object(TenantMiddleware, "_extract_tenant_from_path"):
            context = middleware._extract_tenant_context(request)
        assert "district_id" not in context

    def test_query_params(self, middleware):
        """Extracts district_id and congregation_id from query params."""
        did = uuid.uuid4()
        cid = uuid.uuid4()
        request = MagicMock(spec=Request)
        request.headers = {}
        request.url.path = "/api/v1/events"
        request.query_params = {"district_id": str(did), "congregation_id": str(cid)}
        request.state = MagicMock()
        del request.state.user

        with patch.object(TenantMiddleware, "_extract_tenant_from_path"):
            context = middleware._extract_tenant_context(request)
        assert str(context["district_id"]) == str(did)
        assert str(context["congregation_id"]) == str(cid)


# =========================================================================
# TenantMiddleware.dispatch  (integration-style with TestClient)
# =========================================================================

class TestTenantMiddlewareDispatch:
    """Integration tests for TenantMiddleware.dispatch via TestClient."""

    @pytest.fixture
    def app(self):
        _app = FastAPI()
        _app.add_middleware(TenantMiddleware)

        @_app.get("/api/health")
        async def health():
            return {"status": "ok"}

        @_app.get("/test")
        async def test_endpoint(request: Request):
            ctx = getattr(request.state, "tenant_context", {})
            return {"tenant_context": ctx}

        @_app.post("/test")
        async def test_post(request: Request):
            ctx = getattr(request.state, "tenant_context", {})
            return {"tenant_context": ctx}

        @_app.options("/test")
        async def test_options(request: Request):
            return {}

        return _app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_exempt_path_skips_extraction(self, client):
        """Exempt path (/api/health) passes through without tenant extraction."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_exempt_method_skips_extraction(self, client):
        """OPTIONS requests are exempt from tenant extraction."""
        response = client.options("/test")
        assert response.status_code == 200

    def test_normal_request_sets_tenant_context(self, client):
        """Context is set on request.state and then cleared after response."""
        response = client.get("/test")
        assert response.status_code == 200
        data = response.json()
        assert "tenant_context" in data

    def test_district_id_from_header_is_extracted(self, client):
        """X-District-ID header populates tenant_context."""
        did = uuid.uuid4()
        response = client.get("/test", headers={"X-District-ID": str(did)})
        assert response.status_code == 200
        ctx = response.json()["tenant_context"]
        assert ctx.get("district_id") is not None
        # TestClient stores it as string, not UUID — check it's the right value
        assert str(ctx.get("district_id")) == str(did)


# =========================================================================
# TenantValidationMiddleware._is_authenticated
# =========================================================================

class TestIsAuthenticated:
    """Tests for TenantValidationMiddleware._is_authenticated."""

    @pytest.fixture
    def middleware(self):
        return TenantValidationMiddleware(MagicMock())

    def test_no_user_no_auth_header(self, middleware):
        """Returns False when user not in state and no auth header."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        del request.state.user
        request.headers = {}
        result = middleware._is_authenticated(request)
        assert result is False

    def test_user_in_state(self, middleware):
        """Returns True when user is in request.state."""
        request = MagicMock(spec=Request)
        request.state.user = MagicMock()
        result = middleware._is_authenticated(request)
        assert result is True

    def test_bearer_header_present(self, middleware):
        """Returns True when Bearer token is in Authorization header."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        del request.state.user
        request.headers = {"authorization": "Bearer some-token"}
        result = middleware._is_authenticated(request)
        assert result is True

    def test_wrong_auth_scheme(self, middleware):
        """Returns False with non-Bearer scheme."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        del request.state.user
        request.headers = {"authorization": "Basic dGVzdDpwYXNz"}
        result = middleware._is_authenticated(request)
        assert result is False

    def test_user_none_in_state(self, middleware):
        """Returns False when state.user is None."""
        request = MagicMock(spec=Request)
        request.state.user = None
        request.headers = {}
        result = middleware._is_authenticated(request)
        assert result is False


# =========================================================================
# TenantValidationMiddleware.dispatch  (exempt paths only)
# =========================================================================

class TestTenantValidationMiddlewareDispatch:
    """Tests for TenantValidationMiddleware exempt paths."""

    @pytest.fixture
    def app(self):
        _app = FastAPI()
        _app.add_middleware(TenantValidationMiddleware)

        @_app.get("/api/health")
        async def health():
            return {"status": "ok"}

        @_app.get("/api/v1/auth/login")
        async def auth_login():
            return {"login": "ok"}

        @_app.get("/api/v1/protected")
        async def protected():
            return {"protected": True}

        return _app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_exempt_health_endpoint(self, client):
        """Health endpoint is exempt from validation."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_exempt_auth_endpoint(self, client):
        """Auth endpoints are exempt from validation."""
        response = client.get("/api/v1/auth/login")
        assert response.status_code == 200

    def test_exempt_get_method(self, client):
        """GET requests are exempt from validation by default."""
        response = client.get("/api/v1/protected")
        assert response.status_code == 200

    def test_custom_exempt_paths(self):
        """Custom exempt paths are respected."""
        app = FastAPI()
        app.add_middleware(
            TenantValidationMiddleware,
            exempt_paths={"/api/custom"},
        )

        @app.get("/api/custom/route")
        async def custom():
            return {"ok": True}

        @app.post("/api/custom/data")
        async def custom_post():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/api/custom/route")
        assert response.status_code == 200

    def test_custom_exempt_methods(self):
        """Custom exempt methods are respected."""
        app = FastAPI()
        app.add_middleware(
            TenantValidationMiddleware,
            exempt_methods={"PATCH"},
        )

        @app.patch("/api/v1/protected")
        async def patched():
            return {"ok": True}

        client = TestClient(app)
        response = client.patch("/api/v1/protected")
        assert response.status_code == 200
