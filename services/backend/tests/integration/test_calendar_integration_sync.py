"""Integration tests for calendar integration sync endpoint."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.adapters.api.deps import get_db_session
from app.main import app


@contextmanager
def _mock_auth_context(district_id: uuid.UUID):
    adapter = AsyncMock(spec=deps.OIDCAdapter)
    deps.set_oidc_adapter(adapter)
    claims = {
        "sub": "sync-admin",
        "email": "admin@example.com",
        "preferred_username": "admin",
        "name": "Admin",
        "memberships": [
            {"role": "DISTRICT_ADMIN", "scope_type": "DISTRICT", "scope_id": str(district_id)},
        ],
    }
    adapter.validate_token.return_value = claims
    adapter.extract_user_info.return_value = {
        "sub": "sync-admin",
        "email": "admin@example.com",
        "username": "admin",
        "name": "Admin",
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
            user_repo = AsyncMock()
            user_repo.get_by_sub.return_value = None
            user_repo.has_any_user.return_value = True
            user_repo.save = AsyncMock()
            MockUserRepo.return_value = user_repo

            reg_repo = AsyncMock()
            reg_repo.list_approved_unlinked_by_email.return_value = []
            MockRegRepo.return_value = reg_repo

            membership_repo = AsyncMock()
            membership_repo.get_all_by_user.return_value = []
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
        type=SimpleNamespace(value="GOOGLE"),
        credentials_enc="enc",
        default_category=None,
        last_synced_at=None,
        last_sync_error=None,
    )


def test_trigger_sync_success_persists_last_synced_and_clears_error():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = AsyncMock()
    repo.get.return_value = integration

    raw_event = SimpleNamespace(
        uid="uid-1",
        start_at=datetime(2026, 1, 1, tzinfo=UTC),
        end_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
        title="Title",
        description="Desc",
        is_cancelled=False,
        content_hash="hash-1",
    )
    connector = AsyncMock()
    connector.fetch_events.return_value = [raw_event]

    with _mock_auth_context(district_id) as (client, headers), patch(
        "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
    ) as MockRepoRouter, patch("app.application.sync_service.SqlCalendarIntegrationRepository") as MockRepoSync, patch(
        "app.application.sync_service._get_connector"
    ) as mock_get_connector, patch(
        "app.application.sync_service.decrypt_credentials", return_value={}
    ), patch(
        "app.application.sync_service.SqlExternalEventLinkRepository"
    ) as MockLinkRepo, patch(
        "app.application.sync_service.SqlEventInstanceRepository"
    ) as MockInstRepo, patch(
        "app.application.sync_service.SqlPlanningSlotRepository"
    ) as MockSlotRepo:
        MockRepoRouter.return_value = repo
        MockRepoSync.return_value = repo
        mock_get_connector.return_value = connector
        MockLinkRepo.return_value = AsyncMock(get_by_external_event=AsyncMock(return_value=None), save=AsyncMock())
        MockInstRepo.return_value = AsyncMock(save=AsyncMock(), get_by_planning_slot=AsyncMock(return_value=None), get=AsyncMock(return_value=None))
        MockSlotRepo.return_value = AsyncMock(save=AsyncMock(), list_for_date_range=AsyncMock(return_value=[]))

        response = client.post(f"/api/v1/calendar-integrations/{integration.id}/sync", headers=headers)

    assert response.status_code == 200
    assert response.json()["integration_id"] == str(integration.id)
    assert integration.last_sync_error is None
    assert integration.last_synced_at is not None


def test_trigger_sync_failure_persists_last_sync_error():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = AsyncMock()
    repo.get.return_value = integration
    connector = AsyncMock()
    connector.fetch_events.side_effect = RuntimeError("boom sync failed")

    with _mock_auth_context(district_id) as (client, headers), patch(
        "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
    ) as MockRepoRouter, patch("app.application.sync_service.SqlCalendarIntegrationRepository") as MockRepoSync, patch(
        "app.application.sync_service._get_connector"
    ) as mock_get_connector, patch(
        "app.application.sync_service.decrypt_credentials", return_value={}
    ):
        MockRepoRouter.return_value = repo
        MockRepoSync.return_value = repo
        mock_get_connector.return_value = connector

        response = client.post(f"/api/v1/calendar-integrations/{integration.id}/sync", headers=headers)

    assert response.status_code == 500
    assert integration.last_sync_error == "boom sync failed"
