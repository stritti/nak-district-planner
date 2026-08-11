"""Integration tests for calendar integration CRUD endpoints."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.adapters.api.deps import get_db_session
from app.main import app


@contextmanager
def _auth_client(district_id: uuid.UUID):
    adapter = AsyncMock(spec=deps.OIDCAdapter)
    deps.set_oidc_adapter(adapter)
    claims = {
        "sub": "crud-admin",
        "email": "crud@example.com",
        "preferred_username": "crud",
        "name": "Crud Admin",
        "memberships": [{"role": "DISTRICT_ADMIN", "scope_type": "DISTRICT", "scope_id": str(district_id)}],
    }
    adapter.validate_token.return_value = claims
    adapter.extract_user_info.return_value = {
        "sub": "crud-admin",
        "email": "crud@example.com",
        "username": "crud",
        "name": "Crud Admin",
        "given_name": None,
        "family_name": None,
    }

    async def _override_db_session():
        return AsyncMock()

    app.dependency_overrides[get_db_session] = _override_db_session
    try:
        with patch("app.adapters.api.deps.SqlUserRepository") as MockUserRepo, patch(
            "app.adapters.api.deps.SqlLeaderRegistrationRepository"
        ) as MockRegRepo, patch("app.adapters.api.deps.SqlMembershipRepository") as MockMembershipRepo:
            user_repo = AsyncMock(get_by_sub=AsyncMock(return_value=None), has_any_user=AsyncMock(return_value=True), save=AsyncMock())
            MockUserRepo.return_value = user_repo
            reg_repo = AsyncMock(list_approved_unlinked_by_email=AsyncMock(return_value=[]))
            MockRegRepo.return_value = reg_repo
            membership_repo = AsyncMock(get_all_by_user=AsyncMock(return_value=[]))
            MockMembershipRepo.return_value = membership_repo

            client = TestClient(app, raise_server_exceptions=False)
            client.get("/api/v1/auth/me", headers={"Authorization": "Bearer t"})
            csrf = client.cookies.get("csrf_token")
            yield client, {"Authorization": "Bearer t", "X-CSRF-Token": csrf}
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        deps.set_oidc_adapter(None)
        deps._token_claims_context.clear()


def _integration(district_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        district_id=district_id,
        congregation_id=None,
        name="Old",
        type="GOOGLE",
        sync_interval=15,
        capabilities=["READ"],
        is_active=True,
        last_synced_at=None,
        last_sync_error=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        default_category=None,
    )


def test_create_calendar_integration_happy_path():
    district_id = uuid.uuid4()
    created = _integration(district_id)
    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.calendar_integrations.CalendarIntegrationService"
    ) as MockService:
        service = AsyncMock()
        service.create_integration.return_value = created
        MockService.return_value = service
        response = client.post(
            "/api/v1/calendar-integrations",
            json={
                "district_id": str(district_id),
                "name": "Old",
                "type": "GOOGLE",
                "credentials": {"access_token": "secret"},
                "sync_interval": 15,
                "capabilities": ["READ"],
            },
            headers=headers,
        )
    assert response.status_code == 201
    assert response.json()["id"] == str(created.id)
    assert "credentials_enc" not in response.json()


def test_list_calendar_integrations_happy_path():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = AsyncMock()
    repo.list_by_district.return_value = [integration]
    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
    ) as MockRepo:
        MockRepo.return_value = repo
        response = client.get(
            "/api/v1/calendar-integrations",
            params={"district_id": str(district_id)},
            headers=headers,
        )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(integration.id)


def test_update_calendar_integration_happy_path():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    updated = integration
    updated.name = "New"
    repo = AsyncMock()
    repo.get.return_value = integration
    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
    ) as MockRepo, patch("app.adapters.api.routers.calendar_integrations.CalendarIntegrationService") as MockService:
        MockRepo.return_value = repo
        service = AsyncMock()
        service.update_integration.return_value = updated
        MockService.return_value = service
        response = client.patch(
            f"/api/v1/calendar-integrations/{integration.id}",
            json={"name": "New"},
            headers=headers,
        )
    assert response.status_code == 200
    assert response.json()["name"] == "New"


def test_delete_calendar_integration_happy_path():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = AsyncMock()
    repo.get.return_value = integration
    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
    ) as MockRepo:
        MockRepo.return_value = repo
        response = client.delete(f"/api/v1/calendar-integrations/{integration.id}", headers=headers)
    assert response.status_code == 204
