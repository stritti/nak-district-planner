"""Integration tests for version check and update API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.main import app


def _csrf_token(client, token="x"):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    csrf = resp.cookies.get("csrf_token")
    assert csrf is not None
    return csrf


@pytest.fixture
def mock_oidc_adapter():
    """Mock OIDC adapter for integration tests."""
    adapter = AsyncMock(spec=object)  # Use spec to avoid implicit async behavior
    adapter.validate_token = AsyncMock(
        return_value={
            "sub": "admin-123",
            "email": "admin@example.com",
            "preferred_username": "admin.user",
            "name": "Admin User",
            "roles": ["superadmin"],
        }
    )
    adapter.extract_user_info = MagicMock(
        return_value={
            "sub": "admin-123",
            "email": "admin@example.com",
            "preferred_username": "admin.user",
            "username": "admin.user",
            "name": "Admin User",
            "given_name": None,
            "family_name": None,
        }
    )
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
        with patch("importlib.metadata.version", return_value="0.4.5"), patch(
            "app.adapters.version_check.ghcr.GhcrTagFetcher.fetch_tags", return_value=["0.4.6"]
        ), patch(
            "app.adapters.version_check.ghcr.latest_semver", return_value="0.4.6"
        ), patch(
            "app.adapters.api.deps.SqlUserRepository"
        ) as MockUserRepo, patch("app.adapters.api.deps.SqlMembershipRepository") as MockMembershipRepo, patch(
            "app.adapters.api.deps.SqlLeaderRegistrationRepository"
        ) as MockRegRepo:
            user_repo = AsyncMock()
            user_repo.get_by_sub.return_value = None
            user_repo.has_any_user.return_value = False
            user_repo.save = AsyncMock()
            MockUserRepo.return_value = user_repo

            membership_repo = AsyncMock()
            membership_repo.get_all_by_user.return_value = []
            MockMembershipRepo.return_value = membership_repo

            reg_repo = AsyncMock()
            reg_repo.list_approved_unlinked_by_email.return_value = []
            MockRegRepo.return_value = reg_repo

            client = TestClient(app)
            resp = client.get(
                "/api/v1/system/version",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["current_version"] == "0.4.5"
        assert "latest_version" in data
        assert data["latest_version"] == "0.4.6"

    def test_version_requires_auth(self):
        client = TestClient(app)
        resp = client.get("/api/v1/system/version")
        assert resp.status_code == 401


class TestSystemUpdateEndpoint:
    """Tests for POST /api/v1/system/update."""

    def test_update_manual_mode(self, mock_oidc_adapter, valid_token):
        with patch("app.adapters.api.deps.SqlUserRepository") as MockUserRepo, patch(
            "app.adapters.api.deps.SqlMembershipRepository"
        ) as MockMembershipRepo, patch("app.adapters.api.deps.SqlLeaderRegistrationRepository") as MockRegRepo:
            user_repo = AsyncMock()
            user_repo.get_by_sub.return_value = None
            user_repo.has_any_user.return_value = False
            user_repo.save = AsyncMock()
            MockUserRepo.return_value = user_repo

            membership_repo = AsyncMock()
            membership_repo.get_all_by_user.return_value = []
            MockMembershipRepo.return_value = membership_repo

            reg_repo = AsyncMock()
            reg_repo.list_approved_unlinked_by_email.return_value = []
            MockRegRepo.return_value = reg_repo

            client = TestClient(app)
            csrf = _csrf_token(client, valid_token)
            resp = client.post(
                "/api/v1/system/update",
                headers={"Authorization": f"Bearer {valid_token}", "X-CSRF-Token": csrf},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "manual"
        assert "instructions" in data
        assert data["mode"] == "manual"

    def test_update_requires_auth(self):
        client = TestClient(app)
        csrf = _csrf_token(client)
        resp = client.post("/api/v1/system/update", headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 401
