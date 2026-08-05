"""Negative integration tests: authenticated non-authorized users get 403.

User fixture: VIEWER in district1, no memberships elsewhere, not superadmin.

Two 403 paths are exercised deliberately:
- Role-based: resource belongs to district1 (user IS a member, but the route
  requires PLANNER or DISTRICT_ADMIN) -> 403 because the role is too low.
- Membership-based: resource belongs to an unrelated district (no membership)
  -> 403 because the user has no access at all.

Positive controls prove the plumbing (Bearer auth + CSRF header) works and
that 403s below are genuinely role/membership denials, not CSRF artifacts.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.adapters.api.deps import get_notification_service
from app.domain.models.role import Role
from app.main import app


@contextmanager
def _notification_service_override(service):
    """Override the NotificationService dependency (Depends captures the
    callable at route registration, so module-attribute patching is useless).
    """
    app.dependency_overrides[get_notification_service] = lambda: service
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_notification_service, None)


@pytest.fixture
def mock_oidc_adapter():
    adapter = AsyncMock(spec=deps.OIDCAdapter)
    deps.set_oidc_adapter(adapter)
    yield adapter
    deps.set_oidc_adapter(None)


@pytest.fixture(autouse=True)
def override_db_session():
    async def _override_db_session():
        return AsyncMock()

    app.dependency_overrides[deps.get_db_session] = _override_db_session
    yield
    app.dependency_overrides.pop(deps.get_db_session, None)


@pytest.fixture
def auth_client(mock_oidc_adapter):
    """Yield client + auth-header factory. User is VIEWER in district1 only."""
    district1 = uuid.uuid4()
    claims = {
        "sub": "user-403",
        "email": "user403@example.com",
        "preferred_username": "user403",
        "name": "User 403",
        "memberships": [
            {"role": "VIEWER", "scope_type": "DISTRICT", "scope_id": str(district1)},
        ],
    }
    mock_oidc_adapter.validate_token.return_value = claims
    mock_oidc_adapter.extract_user_info.return_value = {
        "sub": "user-403",
        "email": "user403@example.com",
        "username": "user403",
        "name": "User 403",
        "given_name": None,
        "family_name": None,
    }

    with (
        patch("app.adapters.api.deps.SqlUserRepository") as MockUserRepo,
        patch("app.adapters.api.deps.SqlLeaderRegistrationRepository") as MockRegRepo,
        patch("app.adapters.api.deps.SqlMembershipRepository") as MockMembershipRepo,
    ):
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

        client = TestClient(app)
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer t"})
        csrf = client.cookies.get("csrf_token")

        def _auth_headers():
            return {"Authorization": "Bearer t", "X-CSRF-Token": csrf}

        yield client, _auth_headers, district1

        # The requests above populated deps._token_claims_context (module-level,
        # never auto-cleared). Reset it so unit tests that call
        # get_current_user_with_memberships directly don't inherit stale claims.
        deps._token_claims_context.clear()


# ── Mock object builders ────────────────────────────────────────────────


def _district_obj(district_id: uuid.UUID):
    return SimpleNamespace(id=uuid.uuid4(), district_id=district_id)


def _slot_obj(district_id: uuid.UUID):
    return SimpleNamespace(id=uuid.uuid4(), district_id=district_id, congregation_id=None)


def _integration_obj(district_id: uuid.UUID):
    return SimpleNamespace(id=uuid.uuid4(), district_id=district_id, congregation_id=None)


def _series_obj(district_id: uuid.UUID):
    return SimpleNamespace(id=uuid.uuid4(), district_id=district_id, congregation_id=None)


def _leader_obj(district_id: uuid.UUID):
    return SimpleNamespace(id=uuid.uuid4(), district_id=district_id, congregation_id=None)


def _notification_obj(district_id: uuid.UUID):
    return SimpleNamespace(id=uuid.uuid4(), district_id=district_id)


# ── Positive controls (prove auth + CSRF plumbing) ─────────────────────


def test_authenticated_me_returns_200(auth_client):
    client, auth_headers, _ = auth_client
    response = client.get("/api/v1/auth/me", headers=auth_headers())
    assert response.status_code == 200


def test_viewer_list_districts_returns_200(auth_client):
    client, auth_headers, _ = auth_client
    with patch(
        "app.adapters.db.repositories.district.SqlDistrictRepository.list_all",
        new_callable=AsyncMock,
        return_value=[],
    ):
        response = client.get("/api/v1/districts", headers=auth_headers())
    assert response.status_code == 200


def test_viewer_state_change_in_own_district_returns_200(auth_client):
    """VIEWER may read-all notifications in district1 -> 200.

    State-changing request with Bearer + CSRF header: proves 403 responses
    elsewhere are role/membership denials, not CSRF middleware artifacts.
    """
    client, auth_headers, district1 = auth_client
    service = AsyncMock()
    service.mark_all_read.return_value = 3
    with _notification_service_override(service):
        response = client.post(
            f"/api/v1/notifications/{district1}/read-all", headers=auth_headers()
        )
    assert response.status_code == 200


def test_viewer_get_events_in_own_district_returns_200(auth_client):
    client, auth_headers, district1 = auth_client
    with (
        patch(
            "app.adapters.api.routers.events_compat.SqlPlanningSlotRepository"
        ) as MockSlotRepo,
        patch(
            "app.adapters.api.routers.events_compat.SqlEventInstanceRepository"
        ) as MockInstRepo,
    ):
        slot_repo = AsyncMock()
        slot_repo.list_for_date_range.return_value = []
        MockSlotRepo.return_value = slot_repo
        inst_repo = AsyncMock()
        inst_repo.list_by_planning_slots.return_value = []
        MockInstRepo.return_value = inst_repo
        response = client.get(
            "/api/v1/events",
            params={"district_id": str(district1)},
            headers=auth_headers(),
        )
    assert response.status_code == 200


# ── Districts ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path_template", "role", "membership"),
    [
        # Role-based: VIEWER is member of district1 but route needs DISTRICT_ADMIN
        ("patch", "/api/v1/districts/{district_id}", Role.VIEWER, True),
        ("post", "/api/v1/districts/{district_id}/congregations", Role.VIEWER, True),
        ("post", "/api/v1/districts/{district_id}/groups", Role.VIEWER, True),
        # Membership-based: no membership in this district
        ("get", "/api/v1/districts/{district_id}/congregations", None, False),
        ("get", "/api/v1/districts/{district_id}/groups", None, False),
        # Superadmin-only
        ("post", "/api/v1/districts", Role.VIEWER, True),
    ],
)
def test_district_routes_return_403(auth_client, method, path_template, role, membership):
    client, auth_headers, district1 = auth_client
    district_id = district1 if membership else uuid.uuid4()
    path = path_template.format(district_id=district_id)
    kwargs = {"json": {"name": "X"}} if method in {"post", "patch"} else {}
    kwargs["headers"] = auth_headers()
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403


# ── Calendar integrations & export tokens (DISTRICT_ADMIN) ─────────────


@pytest.mark.parametrize(
    ("method", "path_template", "body", "query"),
    [
        ("post", "/api/v1/calendar-integrations",
         {"district_id": "{district_id}", "name": "I", "type": "GOOGLE",
          "credentials": {}, "sync_interval": 15, "capabilities": ["READ"]}, None),
        ("get", "/api/v1/calendar-integrations", None, {"district_id": "{district_id}"}),
        ("post", "/api/v1/calendar-integrations/{resource_id}/sync", None, None),
        ("patch", "/api/v1/calendar-integrations/{resource_id}", {"name": "X"}, None),
        ("delete", "/api/v1/calendar-integrations/{resource_id}", None, None),
        ("post", "/api/v1/export-tokens",
         {"district_id": "{district_id}", "label": "L", "token_type": "PUBLIC"}, None),
        ("get", "/api/v1/export-tokens", None, {"district_id": "{district_id}"}),
        ("delete", "/api/v1/export-tokens/{resource_id}", None, None),
    ],
)
def test_calendar_and_export_routes_return_403(auth_client, method, path_template, body, query):
    client, auth_headers, district1 = auth_client
    resource_id = uuid.uuid4()
    integration_repo = AsyncMock()
    integration_repo.get.return_value = _integration_obj(district1)
    token_repo = AsyncMock()
    token_repo.get.return_value = _district_obj(district1)

    with (
        patch(
            "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
        ) as MockIntRepo,
        patch("app.adapters.api.routers.export.SqlExportTokenRepository") as MockTokenRepo,
    ):
        MockIntRepo.return_value = integration_repo
        MockTokenRepo.return_value = token_repo

        path = path_template.format(district_id=district1, resource_id=resource_id)
        kwargs = {}
        if body is not None:
            kwargs["json"] = {
                k: (str(district1) if v == "{district_id}" else v) for k, v in body.items()
            }
        if query is not None:
            kwargs["params"] = {k: str(district1) for k in query}
        kwargs["headers"] = auth_headers()
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403


# ── Events, assignments, invitations ────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path_template", "body", "query", "role_kind"),
    [
        # PLANNER-required routes -> role-based 403 (resource in district1)
        ("patch", "/api/v1/events/{resource_id}", {}, None, "planner"),
        ("post", "/api/v1/events/bulk-approval-status",
         {"year": 2026, "month": 1, "approval_status": "PLANNED"},
         {"district_id": "{district_id}"}, "planner"),
        ("post", "/api/v1/events/{resource_id}/assignments",
         {"leader_name": "X"}, None, "planner"),
        ("put", "/api/v1/events/{resource_id}/assignments/{assignment_id}",
         {"leader_name": "X"}, None, "planner"),
        ("delete", "/api/v1/events/{resource_id}/assignments/{assignment_id}",
         None, None, "planner"),
        ("post", "/api/v1/events/{resource_id}/invitations",
         {"targets": [{"target_type": "EXTERNAL_NOTE", "external_target_note": "note"}]},
         None, "planner"),
        ("delete", "/api/v1/invitations/{assignment_id}", None, None, "planner"),
        ("post", "/api/v1/invitations/overwrite-requests/{assignment_id}/decision",
         {"decision": "ACCEPTED"}, None, "planner"),
        # VIEWER-required routes -> membership-based 403 (no membership)
        ("get", "/api/v1/events", None, {"district_id": "{district_id}"}, "viewer"),
        ("get", "/api/v1/events/{resource_id}/assignments", None, None, "viewer"),
        ("get", "/api/v1/events/{resource_id}/invitations", None, None, "viewer"),
        ("get", "/api/v1/invitations/overwrite-requests",
         None, {"district_id": "{district_id}"}, "viewer"),
    ],
)
def test_events_and_related_routes_return_403(
    auth_client, method, path_template, body, query, role_kind
):
    client, auth_headers, district1 = auth_client
    # PLANNER-required routes: resource in district1 (member, role too low).
    # VIEWER-required routes: resource in an unrelated district (no membership).
    resource_district = district1 if role_kind == "planner" else uuid.uuid4()
    resource_id = uuid.uuid4()
    assignment_id = uuid.uuid4()

    slot_repo = AsyncMock()
    slot_repo.get.return_value = _slot_obj(resource_district)
    slot_repo.list_for_date_range.return_value = []

    assignment_repo = AsyncMock()
    assignment_repo.get.return_value = SimpleNamespace(id=assignment_id, event_id=resource_id)

    invitation_repo = AsyncMock()
    invitation_repo.get.return_value = SimpleNamespace(
        id=assignment_id, source_event_id=resource_id
    )

    overwrite_repo = AsyncMock()
    overwrite_repo.get.return_value = SimpleNamespace(
        id=assignment_id, target_event_id=resource_id
    )

    with (
        patch("app.adapters.api.routers.events_compat.SqlPlanningSlotRepository") as MockCompatSlot,
        patch(
            "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
        ) as MockAssignSlot,
        patch(
            "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
        ) as MockAssignRepo,
        patch("app.adapters.api.routers.invitations.SqlPlanningSlotRepository") as MockInvSlot,
        patch("app.adapters.api.routers.invitations.SqlInvitationRepository") as MockInvRepo,
        patch(
            "app.adapters.api.routers.invitations.SqlInvitationOverwriteRequestRepository"
        ) as MockOverwriteRepo,
    ):
        MockCompatSlot.return_value = slot_repo
        MockAssignSlot.return_value = slot_repo
        MockAssignRepo.return_value = assignment_repo
        MockInvSlot.return_value = slot_repo
        MockInvRepo.return_value = invitation_repo
        MockOverwriteRepo.return_value = overwrite_repo

        path = path_template.format(
            resource_id=resource_id, assignment_id=assignment_id
        )
        kwargs = {}
        if body is not None:
            kwargs["json"] = body
        if query is not None:
            kwargs["params"] = {k: str(resource_district) for k in query}
        kwargs["headers"] = auth_headers()
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403


# ── Leaders ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path_template", "body", "membership", "role_kind"),
    [
        # PLANNER-required routes -> role-based 403
        ("post", "/api/v1/districts/{district_id}/leaders", {"name": "X"}, True, "planner"),
        ("patch", "/api/v1/districts/{district_id}/leaders/{leader_id}",
         {"name": "Y"}, True, "planner"),
        ("delete", "/api/v1/districts/{district_id}/leaders/{leader_id}",
         None, True, "planner"),
        # VIEWER-required routes -> membership-based 403
        ("get", "/api/v1/districts/{district_id}/leaders", None, False, "viewer"),
        ("post", "/api/v1/districts/{district_id}/leaders/link-self",
         {"leader_id": "{leader_id}"}, False, "viewer"),
    ],
)
def test_leader_routes_return_403(
    auth_client, method, path_template, body, membership, role_kind
):
    client, auth_headers, district1 = auth_client
    district_id = district1 if membership else uuid.uuid4()
    leader_id = uuid.uuid4()

    district_repo = AsyncMock()
    district_repo.get.return_value = _district_obj(district_id)
    leader_repo = AsyncMock()
    leader_repo.get.return_value = _leader_obj(district_id)

    with (
        patch("app.adapters.api.routers.leaders.SqlDistrictRepository") as MockDistrictRepo,
        patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as MockLeaderRepo,
    ):
        MockDistrictRepo.return_value = district_repo
        MockLeaderRepo.return_value = leader_repo

        path = path_template.format(district_id=district_id, leader_id=leader_id)
        kwargs = {}
        if body is not None:
            kwargs["json"] = {
                k: (str(leader_id) if v == "{leader_id}" else v) for k, v in body.items()
            }
        kwargs["headers"] = auth_headers()
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403


# ── Notifications (VIEWER-required) ─────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path_template"),
    [
        ("get", "/api/v1/notifications/{district_id}"),
        ("get", "/api/v1/notifications/{district_id}/unread-count"),
        ("post", "/api/v1/notifications/{notification_id}/read"),
        ("post", "/api/v1/notifications/{district_id}/read-all"),
    ],
)
def test_notification_routes_return_403(auth_client, method, path_template):
    client, auth_headers, _ = auth_client
    district_id = uuid.uuid4()
    notification_id = uuid.uuid4()

    service = AsyncMock()
    service.get.return_value = _notification_obj(district_id)
    with _notification_service_override(service):
        path = path_template.format(
            district_id=district_id, notification_id=notification_id
        )
        response = getattr(client, method)(path, headers=auth_headers())
        assert response.status_code == 403


# ── Planning series ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path_template", "body", "membership", "role_kind"),
    [
        # DISTRICT_ADMIN-required routes -> role-based 403
        ("post", "/api/v1/planning-series",
         {"district_id": "{district_id}", "default_planning_time": "09:30:00"},
         True, "admin"),
        ("patch", "/api/v1/planning-series/{series_id}", {}, True, "admin"),
        ("post", "/api/v1/planning-series/{series_id}/generate-slots", {}, True, "admin"),
        ("post", "/api/v1/planning-series/districts/{district_id}/generate-slots",
         {}, True, "admin"),
        # VIEWER-required route -> membership-based 403
        ("get", "/api/v1/planning-series/{series_id}", None, False, "viewer"),
        # Superadmin-only route
        ("post", "/api/v1/planning-series/generate-all-slots", None, True, "superadmin"),
    ],
)
def test_planning_series_routes_return_403(
    auth_client, method, path_template, body, membership, role_kind
):
    client, auth_headers, district1 = auth_client
    district_id = district1 if membership else uuid.uuid4()
    series_id = uuid.uuid4()

    series_repo = AsyncMock()
    series_repo.get.return_value = _series_obj(district_id)

    with patch(
        "app.adapters.api.routers.planning_series.SqlPlanningSeriesRepository"
    ) as MockSeriesRepo:
        MockSeriesRepo.return_value = series_repo

        path = path_template.format(district_id=district_id, series_id=series_id)
        kwargs = {}
        if body is not None:
            kwargs["json"] = {
                k: (str(district_id) if v == "{district_id}" else v)
                for k, v in body.items()
            }
        kwargs["headers"] = auth_headers()
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403


# ── Registrations (DISTRICT_ADMIN-required) ─────────────────────────────


@pytest.mark.parametrize(
    ("method", "path_template", "body"),
    [
        ("get", "/api/v1/districts/{district_id}/registrations", None),
        ("post", "/api/v1/districts/{district_id}/registrations/{registration_id}/approve",
         {"role": "DISTRICT_ADMIN", "scope_type": "DISTRICT",
          "scope_id": "{district_id}"}),
        ("post", "/api/v1/districts/{district_id}/registrations/{registration_id}/reject",
         {"reason": "x"}),
        ("delete", "/api/v1/districts/{district_id}/registrations/{registration_id}", None),
    ],
)
def test_registration_routes_return_403(auth_client, method, path_template, body):
    client, auth_headers, district1 = auth_client
    registration_id = uuid.uuid4()
    path = path_template.format(district_id=district1, registration_id=registration_id)
    kwargs = {}
    if body is not None:
        kwargs["json"] = {
            k: (str(district1) if v == "{district_id}" else v) for k, v in body.items()
        }
    kwargs["headers"] = auth_headers()
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403


# ── System ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/system/version"),  # needs DISTRICT_ADMIN/CONG_ADMIN anywhere
        ("post", "/api/v1/system/update"),  # superadmin only
    ],
)
def test_system_routes_return_403(auth_client, method, path):
    client, auth_headers, _ = auth_client
    response = getattr(client, method)(path, headers=auth_headers())
    assert response.status_code == 403
