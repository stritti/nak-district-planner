from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.event_instance import EventInstance
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.planning_slot import PlanningSlot
from app.domain.models.role import Role
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment
from app.main import app


@pytest.fixture
def mock_oidc_adapter():
    """Mock OIDC adapter for integration tests."""
    adapter = AsyncMock(spec=deps.OIDCAdapter)
    adapter.validate_token.return_value = {
        "sub": "u1",
        "email": "u1@example.com",
        "preferred_username": "u1",
        "name": "Test User",
    }
    adapter.extract_user_info.return_value = {
        "sub": "u1",
        "email": "u1@example.com",
        "username": "u1",
        "name": "Test User",
        "given_name": None,
        "family_name": None,
    }
    deps.set_oidc_adapter(adapter)
    return adapter


def _make_client_for(
    district_id: uuid.UUID,
    congregation: Congregation,
    slots: list[PlanningSlot],
    instances: list[EventInstance],
    assignments: list[ServiceAssignment],
):
    """Authenticated VIEWER client with fully mocked matrix repositories.

    Yields the client and cleans up the session override afterwards.
    """

    membership = Membership.create(
        user_sub="u1",
        role=Role.VIEWER,
        scope_type=ScopeType.DISTRICT,
        scope_id=district_id,
    )

    async def override_db_session() -> AsyncMock:
        session = AsyncMock()
        result = MagicMock()
        result.mappings.return_value.one_or_none.return_value = None
        result.scalar_one_or_none.return_value = False
        session.execute.return_value = result
        return session

    app.dependency_overrides[deps.get_db_session] = override_db_session

    with (
        patch("app.adapters.api.deps.SqlUserRepository") as MockUserRepo,
        patch("app.adapters.api.deps.SqlMembershipRepository") as MockMembershipRepo,
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls,
        patch("app.adapters.api.routers.districts.SqlCongregationRepository") as cong_repo_cls,
        patch("app.adapters.api.routers.districts.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.districts.SqlEventInstanceRepository") as instance_repo_cls,
        patch(
            "app.adapters.api.routers.districts.SqlServiceAssignmentRepository"
        ) as assignment_repo_cls,
        patch("app.adapters.api.routers.districts.SqlLeaderRepository") as leader_repo_cls,
        patch(
            "app.adapters.api.routers.districts.SqlCongregationGroupRepository"
        ) as group_repo_cls,
        patch("app.adapters.api.routers.districts.SqlInvitationRepository") as invitation_repo_cls,
    ):
        user_repo = AsyncMock()
        user_repo.get_by_sub.return_value = None
        user_repo.save = AsyncMock()
        MockUserRepo.return_value = user_repo

        membership_repo = AsyncMock()
        membership_repo.get_all_by_user.return_value = [membership]
        MockMembershipRepo.return_value = membership_repo

        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="Bezirk")
        district_repo_cls.return_value = district_repo

        cong_repo = AsyncMock()
        cong_repo.list_by_district.return_value = [congregation]
        cong_repo.list_by_ids.return_value = []
        cong_repo_cls.return_value = cong_repo

        slot_repo = AsyncMock()
        slot_repo.list_for_date_range.return_value = slots
        slot_repo_cls.return_value = slot_repo

        instance_repo = AsyncMock()
        instance_repo.list_by_planning_slots.return_value = instances
        instance_repo_cls.return_value = instance_repo

        assignment_repo = AsyncMock()
        assignment_repo.list_by_planning_slots.return_value = assignments
        assignment_repo_cls.return_value = assignment_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = []
        leader_repo_cls.return_value = leader_repo

        group_repo = AsyncMock()
        group_repo.list_by_district.return_value = []
        group_repo_cls.return_value = group_repo

        invitation_repo = AsyncMock()
        invitation_repo.list_by_source_planning_slots.return_value = []
        invitation_repo_cls.return_value = invitation_repo

        yield TestClient(app)

    app.dependency_overrides.pop(deps.get_db_session, None)


@pytest.fixture
def matrix_client(mock_oidc_adapter, request):
    """Client with one gap slot (2026-04-05) and one assigned slot (2026-04-12).

    Both dates are Sundays, so the congregation schedule (weekday=6) expects
    them and the matrix renders both cells from the PlanningSlots. 2026-04-05
    has no assignment (gap), 2026-04-12 has one (assigned).
    """
    district_id = uuid.uuid4()
    congregation = Congregation.create(
        name="Gemeinde A",
        district_id=district_id,
        service_times=[{"weekday": 6, "time": "09:30"}],
    )
    gap_slot = PlanningSlot.create(
        district_id=district_id,
        congregation_id=congregation.id,
        planning_date=date(2026, 4, 5),
        planning_time=time(9, 30),
        category="Gottesdienst",
    )
    assigned_slot = PlanningSlot.create(
        district_id=district_id,
        congregation_id=congregation.id,
        planning_date=date(2026, 4, 12),
        planning_time=time(9, 30),
        category="Gottesdienst",
    )
    assigned_instance = EventInstance.create(
        planning_slot_id=assigned_slot.id,
        title="Gottesdienst Sonntag",
        actual_start_at=datetime(2026, 4, 12, 9, 30, tzinfo=UTC),
        actual_end_at=datetime(2026, 4, 12, 10, 30, tzinfo=UTC),
        source="INTERNAL",
        visibility="INTERNAL",
    )
    assignment = ServiceAssignment.create(
        event_id=assigned_slot.id,
        planning_slot_id=assigned_slot.id,
        leader_name="Pr. Beispiel",
        status=AssignmentStatus.ASSIGNED,
    )
    client_gen = _make_client_for(
        district_id,
        congregation,
        [gap_slot, assigned_slot],
        [assigned_instance],
        [assignment],
    )
    client = next(client_gen)
    request.addfinalizer(lambda: next(client_gen, None))
    return {
        "client": client,
        "district_id": district_id,
        "gap_slot": gap_slot,
        "assigned_slot": assigned_slot,
    }


def test_matrix_endpoint_returns_gap_assigned_and_empty_cells(matrix_client) -> None:
    client = matrix_client["client"]
    district_id = matrix_client["district_id"]
    gap_slot = matrix_client["gap_slot"]
    assigned_slot = matrix_client["assigned_slot"]

    response = client.get(
        f"/api/v1/districts/{district_id}/matrix",
        headers={"Authorization": "Bearer valid_token"},
        params={
            "from_dt": "2026-04-05T00:00:00Z",
            "to_dt": "2026-04-12T23:59:59Z",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    row = payload["rows"][0]
    gap_cell = row["cells"]["2026-04-05"]
    assigned_cell = row["cells"]["2026-04-12"]

    assert gap_cell["event_id"] == str(gap_slot.id)
    assert gap_cell["is_gap"] is True
    assert gap_cell["assignment_id"] is None

    assert assigned_cell["event_id"] == str(assigned_slot.id)
    assert assigned_cell["is_gap"] is False
    assert assigned_cell["leader_name"] == "Pr. Beispiel"
    assert assigned_cell["event_title"] == "Gottesdienst Sonntag"

    # Dates without a schedule expectation and without a slot never become
    # matrix columns; only schedule-expected dates without a slot would render
    # an empty cell, and both Sundays here are covered by the slots above.
    assert "2026-04-06" not in row["cells"]


def test_matrix_endpoint_requires_viewer_role(mock_oidc_adapter) -> None:
    """A user without any membership is rejected with 403, not 200."""
    district_id = uuid.uuid4()
    congregation = Congregation.create(
        name="Gemeinde A",
        district_id=district_id,
        service_times=[{"weekday": 6, "time": "09:30"}],
    )
    for client in _make_client_for(
        district_id,
        congregation,
        slots=[],
        instances=[],
        assignments=[],
    ):
        with patch("app.adapters.api.deps.SqlMembershipRepository") as MockMembershipRepo:
            membership_repo = AsyncMock()
            membership_repo.get_all_by_user.return_value = []
            MockMembershipRepo.return_value = membership_repo
            response = client.get(
                f"/api/v1/districts/{district_id}/matrix",
                headers={"Authorization": "Bearer valid_token"},
                params={
                    "from_dt": "2026-04-06T00:00:00Z",
                    "to_dt": "2026-04-12T23:59:59Z",
                },
            )
        assert response.status_code == 403
