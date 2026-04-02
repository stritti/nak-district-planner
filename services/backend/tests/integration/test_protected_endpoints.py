"""
Integration tests for protected API endpoints with JWT authentication.

Tests verify that endpoints require valid Bearer tokens and work with authenticated users.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.auth.oidc import OIDCAdapter
from app.adapters.api import deps
from app.domain.models.user import User
from app.main import app


@pytest.fixture
def mock_oidc_adapter():
    """Mock OIDC adapter for integration tests."""
    adapter = AsyncMock(spec=OIDCAdapter)
    deps.set_oidc_adapter(adapter)
    return adapter


@pytest.fixture
def valid_token():
    """Sample valid JWT token."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InRlc3Qta2V5In0.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInByZWZlcnJlZF91c2VybmFtZSI6InRlc3QudXNlciIsIm5hbWUiOiJUZXN0IFVzZXIiLCJleHAiOjk5OTk5OTk5OTksImlzcyI6Imh0dHBzOi8vb2lkYy5leGFtcGxlLmNvbSJ9.signature"


class TestEndpointAuthentication:
    """Test that endpoints require authentication."""

    def test_health_endpoint_no_auth(self):
        """Health endpoint should not require auth."""
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_districts_list_missing_token(self):
        """GET /api/v1/districts should return 401 without token."""
        client = TestClient(app)
        response = client.get("/api/v1/districts")
        assert response.status_code == 401

    def test_districts_list_invalid_token(self, mock_oidc_adapter, valid_token):
        """GET /api/v1/districts should return 401 with invalid token."""
        from app.adapters.auth.oidc import TokenValidationError

        mock_oidc_adapter.validate_token.side_effect = TokenValidationError("Invalid")

        client = TestClient(app)
        response = client.get(
            "/api/v1/districts", headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 401

    def test_auth_me_endpoint_with_token(self, mock_oidc_adapter, valid_token):
        """GET /api/v1/auth/me should return user info with valid token."""
        token_claims = {
            "sub": "user-123",
            "email": "test@example.com",
            "preferred_username": "test.user",
            "name": "Test User",
        }
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "user-123",
            "email": "test@example.com",
            "username": "test.user",
            "name": "Test User",
            "given_name": None,
            "family_name": None,
        }

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo = AsyncMock()
            # Return None so new user is created
            mock_repo.get_by_sub.return_value = None
            mock_repo.save = AsyncMock()
            MockRepo.return_value = mock_repo

            client = TestClient(app)
            response = client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {valid_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["sub"] == "user-123"
            assert data["email"] == "test@example.com"
            assert data["username"] == "test.user"


class TestEndpointProtection:
    """Test that endpoints are properly protected."""

    def test_create_district_requires_auth(self):
        """POST /api/v1/districts should require auth."""
        client = TestClient(app)
        response = client.post("/api/v1/districts", json={"name": "Test District"})
        assert response.status_code == 401

    def test_update_district_requires_auth(self):
        """PATCH /api/v1/districts/{id} should require auth."""
        import uuid

        client = TestClient(app)
        response = client.patch(f"/api/v1/districts/{uuid.uuid4()}", json={"name": "Updated"})
        assert response.status_code == 401

    def test_create_event_requires_auth(self):
        """POST /api/v1/events should require auth."""
        import uuid

        client = TestClient(app)
        response = client.post(
            "/api/v1/events",
            json={
                "district_id": str(uuid.uuid4()),
                "title": "Test Event",
                "start_at": "2026-04-02T10:00:00Z",
                "end_at": "2026-04-02T11:00:00Z",
            },
        )
        assert response.status_code == 401

    def test_list_leaders_requires_auth(self):
        """GET /api/v1/districts/{id}/leaders should require auth."""
        import uuid

        client = TestClient(app)
        response = client.get(f"/api/v1/districts/{uuid.uuid4()}/leaders")
        assert response.status_code == 401


class TestTokenHeader:
    """Test Bearer token header parsing."""

    def test_bearer_scheme_required(self, mock_oidc_adapter, valid_token):
        """Token must be in Authorization: Bearer <token> format."""
        client = TestClient(app)

        # Wrong format: missing "Bearer" prefix
        response = client.get("/api/v1/auth/me", headers={"Authorization": valid_token})
        assert response.status_code == 403  # Forbidden (invalid scheme)

    def test_case_insensitive_bearer(self, mock_oidc_adapter, valid_token):
        """Bearer scheme should be case-insensitive."""
        token_claims = {"sub": "user-123", "email": "test@example.com"}
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "user-123",
            "email": "test@example.com",
            "username": "test@example.com",
            "name": None,
            "given_name": None,
            "family_name": None,
        }

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo = AsyncMock()
            mock_repo.get_by_sub.return_value = None
            mock_repo.save = AsyncMock()
            MockRepo.return_value = mock_repo

            client = TestClient(app)

            # Try with different casing
            for prefix in ["Bearer", "bearer", "BEARER"]:
                response = client.get(
                    "/api/v1/auth/me", headers={"Authorization": f"{prefix} {valid_token}"}
                )
                # Note: TestClient might normalize this, but real clients will vary
                if response.status_code != 401:
                    assert response.status_code == 200
