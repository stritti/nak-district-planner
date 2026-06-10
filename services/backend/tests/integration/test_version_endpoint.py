"""Integration tests for version check and update API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.main import app


@pytest.fixture
def mock_oidc_adapter():
    """Mock OIDC adapter for integration tests."""
    adapter = AsyncMock(spec=object)  # Use spec to avoid implicit async behavior
    adapter.validate_token = AsyncMock(return_value={
        "sub": "admin-123",
        "email": "admin@example.com",
        "preferred_username": "admin.user",
        "name": "Admin User",
        "roles": ["superadmin"],
    })
    adapter.extract_user_info = MagicMock(return_value={
        "sub": "admin-123",
        "email": "admin@example.com",
        "preferred_username": "admin.user",
        "name": "Admin User",
    })
    adapter.get_roles = MagicMock(return_value=["superadmin"])
    deps.set_oidc_adapter(adapter)
    return adapter


@pytest.fixture
def valid_token():
    """Sample valid JWT token."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.valid-token"


class TestSystemVersionEndpoint:
    """Tests for GET /api/v1/system/version."""

    def test_version_success(self, mock_oidc_adapter, valid_token):
        with patch("importlib.metadata.version", return_value="0.4.5"):
            client = TestClient(app)
            resp = client.get(
                "/api/v1/system/version",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["current_version"] == "0.4.5"
        assert "latest_version" in data
        assert "update_available" in data

    def test_version_requires_auth(self):
        client = TestClient(app)
        resp = client.get("/api/v1/system/version")
        assert resp.status_code == 401


class TestSystemUpdateEndpoint:
    """Tests for POST /api/v1/system/update."""

    def test_update_manual_mode(self, mock_oidc_adapter, valid_token):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/system/update",
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "manual"
        assert "instructions" in data
        assert data["mode"] == "manual"

    def test_update_requires_auth(self):
        client = TestClient(app)
        resp = client.post("/api/v1/system/update")
        assert resp.status_code == 401
