"""Integration tests for calendar integration CRUD endpoints."""

from __future__ import annotations

import dataclasses
import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.adapters.api.deps import (
    get_calendar_integration_repository,
    get_calendar_integration_service,
    get_db_session,
)
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role
from app.main import app


@contextmanager
def _auth_client(
    district_id: uuid.UUID,
    calendar_repo: AsyncMock | None = None,
    calendar_service: AsyncMock | None = None,
):
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
        session = AsyncMock()
        result = MagicMock()
        result.mappings.return_value.one_or_none.return_value = None
        # Keep the fixture user non-superadmin: the bootstrap grant read
        # must return false so district-admin authorization is exercised.
        result.scalar_one_or_none.return_value = False
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_db_session] = _override_db_session
    if calendar_repo is not None:
        app.dependency_overrides[get_calendar_integration_repository] = lambda: calendar_repo
    if calendar_service is not None:
        app.dependency_overrides[get_calendar_integration_service] = lambda: calendar_service
    try:
        with patch("app.adapters.api.deps.SqlUserRepository") as MockUserRepo, patch("app.adapters.api.deps.SqlMembershipRepository") as MockMembershipRepo:
            user_repo = AsyncMock(get_by_sub=AsyncMock(return_value=None), has_any_user=AsyncMock(return_value=True), save=AsyncMock())
            MockUserRepo.return_value = user_repo
            membership_repo = AsyncMock(
                get_all_by_user=AsyncMock(
                    return_value=[
                        Membership.create(
                            user_sub="crud-admin",
                            role=Role.DISTRICT_ADMIN,
                            scope_type=ScopeType.DISTRICT,
                            scope_id=district_id,
                        )
                    ]
                )
            )
            MockMembershipRepo.return_value = membership_repo

            client = TestClient(app, raise_server_exceptions=False)
            client.get("/api/v1/auth/me", headers={"Authorization": "Bearer t"})
            csrf = client.cookies.get("csrf_token")
            yield client, {"Authorization": "Bearer t", "X-CSRF-Token": csrf}
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_calendar_integration_repository, None)
        app.dependency_overrides.pop(get_calendar_integration_service, None)
        deps.set_oidc_adapter(None)


def _integration(district_id: uuid.UUID) -> CalendarIntegration:
    # The real entity, so new domain fields cannot silently break the response mapping.
    return CalendarIntegration.create(
        district_id=district_id,
        name="Old",
        type=CalendarType.GOOGLE,
        credentials_enc="encrypted",
        sync_interval=15,
        capabilities=[CalendarCapability.READ],
    )


def test_create_calendar_integration_happy_path():
    district_id = uuid.uuid4()
    created = _integration(district_id)
    service = AsyncMock()
    service.create_integration.return_value = created
    with _auth_client(district_id, calendar_service=service) as (client, headers):
        response = client.post(
            "/api/v1/calendar-integrations",
            json={
                "district_id": str(district_id),
                "name": "Old",
                "type": "ICS",
                "credentials": {"url": "https://calendar.example.com/feed.ics"},
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
    with _auth_client(district_id, calendar_repo=repo) as (client, headers):
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
    updated = dataclasses.replace(integration, name="New")
    repo = AsyncMock()
    repo.get.return_value = integration
    service = AsyncMock()
    service.update_integration.return_value = updated
    with _auth_client(district_id, calendar_repo=repo, calendar_service=service) as (client, headers):
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
    with _auth_client(district_id, calendar_repo=repo) as (client, headers):
        response = client.delete(f"/api/v1/calendar-integrations/{integration.id}", headers=headers)
    assert response.status_code == 204


# ── SSRF hardening (#463): URL validated at create/update ────────────────────


import pytest  # noqa: E402

UNSAFE_URLS = [
    "http://calendar.example.com/feed.ics",
    "https://127.0.0.1/feed.ics",
    "https://169.254.169.254/latest/meta-data",
    "https://192.168.0.10/feed.ics",
    "https://[::1]/feed.ics",
    "https://[fd00::1]/feed.ics",
    "https://[::ffff:10.0.0.1]/feed.ics",
    "https://localhost/feed.ics",
    "https://user:pw@calendar.example.com/feed.ics",  # ggignore - fake test credentials
    "file:///etc/passwd",
]


def _create_body(district_id: uuid.UUID, cal_type: str, credentials: dict) -> dict:
    return {
        "district_id": str(district_id),
        "name": "Feed",
        "type": cal_type,
        "credentials": credentials,
        "sync_interval": 15,
        "capabilities": ["READ"],
    }


@pytest.mark.parametrize("cal_type", ["ICS", "CALDAV"])
@pytest.mark.parametrize("url", UNSAFE_URLS)
def test_create_rejects_unsafe_calendar_url_with_422(cal_type, url):
    district_id = uuid.uuid4()
    service = AsyncMock()
    with _auth_client(district_id, calendar_service=service) as (client, headers):
        response = client.post(
            "/api/v1/calendar-integrations",
            json=_create_body(district_id, cal_type, {"url": url}),
            headers=headers,
        )
    assert response.status_code == 422
    assert "user:pw" not in response.text
    service.create_integration.assert_not_called()


@pytest.mark.parametrize("cal_type", ["ICS", "CALDAV"])
def test_create_requires_url_for_url_based_types(cal_type):
    district_id = uuid.uuid4()
    service = AsyncMock()
    with _auth_client(district_id, calendar_service=service) as (client, headers):
        response = client.post(
            "/api/v1/calendar-integrations",
            json=_create_body(district_id, cal_type, {}),
            headers=headers,
        )
    assert response.status_code == 422
    service.create_integration.assert_not_called()


def test_create_accepts_public_https_calendar_url():
    district_id = uuid.uuid4()
    service = AsyncMock()
    service.create_integration.return_value = _integration(district_id)
    with _auth_client(district_id, calendar_service=service) as (client, headers):
        response = client.post(
            "/api/v1/calendar-integrations",
            json=_create_body(district_id, "ICS", {"url": "https://calendar.example.com/f.ics"}),
            headers=headers,
        )
    assert response.status_code == 201


@pytest.mark.parametrize("url", UNSAFE_URLS)
def test_update_rejects_unsafe_calendar_url_with_422(url):
    district_id = uuid.uuid4()
    integration = dataclasses.replace(_integration(district_id), type=CalendarType.ICS)
    repo = AsyncMock()
    repo.get.return_value = integration
    service = AsyncMock()
    with _auth_client(district_id, calendar_repo=repo, calendar_service=service) as (
        client,
        headers,
    ):
        response = client.patch(
            f"/api/v1/calendar-integrations/{integration.id}",
            json={"credentials": {"url": url}},
            headers=headers,
        )
    assert response.status_code == 422
    service.update_integration.assert_not_called()


# ── v1.0 provider scope (#467): only ICS and CalDAV ──────────────────────────


@pytest.mark.parametrize("cal_type", ["GOOGLE", "MICROSOFT"])
def test_create_rejects_unsupported_provider_with_422(cal_type):
    district_id = uuid.uuid4()
    service = AsyncMock()
    with _auth_client(district_id, calendar_service=service) as (client, headers):
        response = client.post(
            "/api/v1/calendar-integrations",
            json=_create_body(district_id, cal_type, {"access_token": "t"}),
            headers=headers,
        )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "ICS" in detail and "CalDAV" in detail
    service.create_integration.assert_not_called()


@pytest.mark.parametrize("cal_type", ["GOOGLE", "MICROSOFT"])
def test_update_cannot_change_type_to_unsupported_provider(cal_type):
    district_id = uuid.uuid4()
    integration = dataclasses.replace(_integration(district_id), type=CalendarType.ICS)
    repo = AsyncMock()
    repo.get.return_value = integration
    service = AsyncMock()
    with _auth_client(district_id, calendar_repo=repo, calendar_service=service) as (
        client,
        headers,
    ):
        response = client.patch(
            f"/api/v1/calendar-integrations/{integration.id}",
            json={"type": cal_type},
            headers=headers,
        )
    assert response.status_code == 422
    service.update_integration.assert_not_called()


def test_existing_google_integration_stays_readable():
    district_id = uuid.uuid4()
    repo = AsyncMock()
    repo.list_by_district.return_value = [_integration(district_id)]  # type GOOGLE
    with _auth_client(district_id, calendar_repo=repo) as (client, headers):
        response = client.get(
            "/api/v1/calendar-integrations",
            params={"district_id": str(district_id)},
            headers=headers,
        )
    assert response.status_code == 200
    assert response.json()["items"][0]["type"] == "GOOGLE"
