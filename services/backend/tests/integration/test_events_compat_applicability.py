"""Integration tests for applicability-based event distribution (UC-04).

District-level planning slots (congregation_id=None) with a matching
`applicability` entry must appear in the congregation's event view, but only
when ACTIVE (PUBLISHED). Empty applicability or CANCELLED status excludes them.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.adapters.api.deps import get_db_session
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.main import app


@contextmanager
def _auth_client(district_id: uuid.UUID):
    adapter = AsyncMock(spec=deps.OIDCAdapter)
    deps.set_oidc_adapter(adapter)
    claims = {
        "sub": "viewer",
        "email": "viewer@example.com",
        "preferred_username": "viewer",
        "name": "Viewer",
        "memberships": [{"role": "VIEWER", "scope_type": "DISTRICT", "scope_id": str(district_id)}],
    }
    adapter.validate_token.return_value = claims
    adapter.extract_user_info.return_value = {
        "sub": "viewer",
        "email": "viewer@example.com",
        "username": "viewer",
        "name": "Viewer",
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


def _slot(
    district_id: uuid.UUID,
    *,
    congregation_id: uuid.UUID | None,
    applicability: list[str] | None = None,
    status: PlanningSlotStatus = PlanningSlotStatus.ACTIVE,
    title: str = "Gottesdienst",
) -> PlanningSlot:
    return PlanningSlot.create(
        district_id=district_id,
        planning_date=date(2026, 8, 16),
        planning_time=time(10, 0),
        congregation_id=congregation_id,
        category="Gottesdienst",
        title=title,
        applicability=applicability,
        status=status,
    )


def _mock_repos(slots: list[PlanningSlot]):
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = slots
    inst_repo = AsyncMock()
    inst_repo.list_by_planning_slots.return_value = []
    return slot_repo, inst_repo


def _list_events(client, headers, district_id: uuid.UUID, congregation_id: uuid.UUID):
    return client.get(
        "/api/v1/events",
        params={"district_id": str(district_id), "congregation_id": str(congregation_id)},
        headers=headers,
    )


def test_district_slot_with_matching_applicability_appears_in_congregation_view():
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    district_slot = _slot(district_id, congregation_id=None, applicability=[str(congregation_id)])
    own_slot = _slot(district_id, congregation_id=congregation_id)
    slot_repo, inst_repo = _mock_repos([district_slot, own_slot])

    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.events_compat.SqlPlanningSlotRepository", return_value=slot_repo
    ), patch(
        "app.adapters.api.routers.events_compat.SqlEventInstanceRepository", return_value=inst_repo
    ):
        response = _list_events(client, headers, district_id, congregation_id)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    ids = {item["id"] for item in items}
    assert str(district_slot.id) in ids
    assert str(own_slot.id) in ids


def test_district_slot_with_other_congregation_applicability_excluded():
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    other_congregation = uuid.uuid4()
    district_slot = _slot(district_id, congregation_id=None, applicability=[str(other_congregation)])
    slot_repo, inst_repo = _mock_repos([district_slot])

    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.events_compat.SqlPlanningSlotRepository", return_value=slot_repo
    ), patch(
        "app.adapters.api.routers.events_compat.SqlEventInstanceRepository", return_value=inst_repo
    ):
        response = _list_events(client, headers, district_id, congregation_id)

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_district_slot_with_empty_applicability_excluded():
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    district_slot = _slot(district_id, congregation_id=None, applicability=[])
    slot_repo, inst_repo = _mock_repos([district_slot])

    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.events_compat.SqlPlanningSlotRepository", return_value=slot_repo
    ), patch(
        "app.adapters.api.routers.events_compat.SqlEventInstanceRepository", return_value=inst_repo
    ):
        response = _list_events(client, headers, district_id, congregation_id)

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_cancelled_district_slot_excluded_even_with_matching_applicability():
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    district_slot = _slot(
        district_id,
        congregation_id=None,
        applicability=[str(congregation_id)],
        status=PlanningSlotStatus.CANCELLED,
    )
    slot_repo, inst_repo = _mock_repos([district_slot])

    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.events_compat.SqlPlanningSlotRepository", return_value=slot_repo
    ), patch(
        "app.adapters.api.routers.events_compat.SqlEventInstanceRepository", return_value=inst_repo
    ):
        response = _list_events(client, headers, district_id, congregation_id)

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_district_view_still_returns_district_slots():
    """Without a congregation filter, distribution filtering must not apply."""
    district_id = uuid.uuid4()
    district_slot = _slot(district_id, congregation_id=None, applicability=[])
    slot_repo, inst_repo = _mock_repos([district_slot])

    with _auth_client(district_id) as (client, headers), patch(
        "app.adapters.api.routers.events_compat.SqlPlanningSlotRepository", return_value=slot_repo
    ), patch(
        "app.adapters.api.routers.events_compat.SqlEventInstanceRepository", return_value=inst_repo
    ):
        response = client.get(
            "/api/v1/events",
            params={"district_id": str(district_id)},
            headers=headers,
        )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(district_slot.id)
