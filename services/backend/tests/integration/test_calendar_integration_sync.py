"""Integration tests for calendar integration sync endpoint."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.adapters.api.deps import get_calendar_integration_repository, get_db_session
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role
from app.domain.ports.calendar import CalendarConnectorError
from app.main import app


@contextmanager
def _mock_auth_context(district_id: uuid.UUID, calendar_repo: AsyncMock):
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
        session = AsyncMock()
        result = MagicMock()
        result.mappings.return_value.one_or_none.return_value = None
        # Keep the fixture user non-superadmin: the bootstrap grant read
        # must return false so district-admin authorization is exercised.
        result.scalar_one_or_none.return_value = False
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_calendar_integration_repository] = lambda: calendar_repo
    try:
        with patch("app.adapters.api.deps.SqlUserRepository") as MockUserRepo, patch("app.adapters.api.deps.SqlMembershipRepository") as MockMembershipRepo:
            user_repo = AsyncMock()
            user_repo.get_by_sub.return_value = None
            user_repo.has_any_user.return_value = True
            user_repo.save = AsyncMock()
            MockUserRepo.return_value = user_repo

            membership_repo = AsyncMock()
            membership_repo.get_all_by_user.return_value = [
                Membership.create(
                    user_sub="sync-admin",
                    role=Role.DISTRICT_ADMIN,
                    scope_type=ScopeType.DISTRICT,
                    scope_id=district_id,
                )
            ]
            MockMembershipRepo.return_value = membership_repo

            client = TestClient(app, raise_server_exceptions=False)
            client.get("/api/v1/auth/me", headers={"Authorization": "Bearer t"})
            csrf = client.cookies.get("csrf_token")
            yield client, {"Authorization": "Bearer t", "X-CSRF-Token": csrf}
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_calendar_integration_repository, None)
        deps.set_oidc_adapter(None)


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


def _raw_event(uid: str = "uid-1"):
    return SimpleNamespace(
        uid=uid,
        start_at=datetime(2026, 1, 1, tzinfo=UTC),
        end_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
        title="Title",
        description="Desc",
        location=None,
        is_cancelled=False,
        content_hash=f"hash-{uid}",
        series_uid=None,
        recurrence_id=None,
        outside_window=False,
    )


def _connector(*, events=(), error: Exception | None = None) -> AsyncMock:
    connector = AsyncMock()
    connector.authoritative_snapshot = False
    if error is not None:
        connector.fetch_events.side_effect = error
    else:
        connector.fetch_events.return_value = list(events)
    return connector


@contextmanager
def _sync_pipeline(repo: AsyncMock, connector: AsyncMock, *, matched: bool = True):
    """Run the real sync service with a mocked connector and repository adapters."""
    with (
        patch("app.application.sync_service.SqlCalendarIntegrationRepository", return_value=repo),
        patch("app.application.sync_service._get_connector", return_value=connector),
        patch("app.application.sync_service.decrypt_credentials", return_value={}),
        patch(
            "app.application.sync_service.SqlExternalEventLinkRepository",
            return_value=AsyncMock(get_by_external_event=AsyncMock(return_value=None)),
        ),
        patch("app.application.sync_service.SqlEventInstanceRepository"),
        patch("app.application.sync_service.SqlPlanningSlotRepository"),
        patch(
            "app.application.sync_service.import_candidate_or_match",
            new=AsyncMock(return_value=matched),
        ) as ingest,
    ):
        yield ingest


def _sync_url(integration) -> str:
    return f"/api/v1/calendar-integrations/{integration.id}/sync"


def _repo_returning(integration) -> AsyncMock:
    repo = AsyncMock()
    repo.get.return_value = integration
    return repo


def test_trigger_sync_returns_sync_result_and_persists_success():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    integration.last_sync_error = "previous failure"
    repo = _repo_returning(integration)
    connector = _connector(events=[_raw_event("a"), _raw_event("b")])

    with (
        _mock_auth_context(district_id, repo) as (client, headers),
        _sync_pipeline(repo, connector) as ingest,
    ):
        response = client.post(_sync_url(integration), headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "integration_id": str(integration.id),
        "created": 0,
        "updated": 0,
        "cancelled": 0,
        "auto_matched": 2,
        "skipped": 0,
        "failed": 0,
    }
    assert ingest.await_count == 2
    assert integration.last_sync_error is None
    assert integration.last_synced_at is not None


def test_trigger_sync_counts_unmatched_events_as_skipped():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = _repo_returning(integration)

    with (
        _mock_auth_context(district_id, repo) as (client, headers),
        _sync_pipeline(repo, _connector(events=[_raw_event()]), matched=False),
    ):
        response = client.post(_sync_url(integration), headers=headers)

    assert response.status_code == 200
    assert response.json()["skipped"] == 1
    assert response.json()["auto_matched"] == 0


def test_trigger_sync_with_empty_feed_succeeds():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = _repo_returning(integration)

    with (
        _mock_auth_context(district_id, repo) as (client, headers),
        _sync_pipeline(repo, _connector()) as ingest,
    ):
        response = client.post(_sync_url(integration), headers=headers)

    assert response.status_code == 200
    assert ingest.await_count == 0
    assert integration.last_synced_at is not None


def test_trigger_sync_connector_error_returns_400_and_persists_error():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = _repo_returning(integration)
    connector = _connector(error=CalendarConnectorError("provider unavailable"))

    with (
        _mock_auth_context(district_id, repo) as (client, headers),
        _sync_pipeline(repo, connector),
    ):
        response = client.post(_sync_url(integration), headers=headers)

    assert response.status_code == 400
    assert integration.last_sync_error == "provider unavailable"


def test_trigger_sync_unexpected_failure_returns_500_and_persists_error():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = _repo_returning(integration)
    connector = _connector(error=RuntimeError("boom sync failed"))

    with (
        _mock_auth_context(district_id, repo) as (client, headers),
        _sync_pipeline(repo, connector),
    ):
        response = client.post(_sync_url(integration), headers=headers)

    assert response.status_code == 500
    # Unexpected exception text may embed URLs/credentials (#463): store a generic message.
    assert integration.last_sync_error is not None
    assert "boom" not in integration.last_sync_error


def test_trigger_sync_unknown_integration_returns_404():
    district_id = uuid.uuid4()
    repo = _repo_returning(None)

    with (
        _mock_auth_context(district_id, repo) as (client, headers),
        patch("app.adapters.api.routers.calendar_integrations.run_sync") as run_sync,
    ):
        response = client.post(f"/api/v1/calendar-integrations/{uuid.uuid4()}/sync", headers=headers)

    assert response.status_code == 404
    run_sync.assert_not_called()


def test_trigger_sync_in_foreign_district_is_forbidden():
    foreign_integration = _integration(uuid.uuid4())
    repo = _repo_returning(foreign_integration)

    with (
        _mock_auth_context(uuid.uuid4(), repo) as (client, headers),
        patch("app.adapters.api.routers.calendar_integrations.run_sync") as run_sync,
    ):
        response = client.post(_sync_url(foreign_integration), headers=headers)

    assert response.status_code == 403
    run_sync.assert_not_called()


def test_trigger_sync_requires_csrf_token():
    district_id = uuid.uuid4()
    integration = _integration(district_id)
    repo = _repo_returning(integration)

    with (
        _mock_auth_context(district_id, repo) as (client, headers),
        patch("app.adapters.api.routers.calendar_integrations.run_sync") as run_sync,
    ):
        response = client.post(
            _sync_url(integration), headers={"Authorization": headers["Authorization"]}
        )

    assert response.status_code == 403
    run_sync.assert_not_called()
