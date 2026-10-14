# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.adapters.api.deps import (
    get_congregation_group_repository,
    get_congregation_repository,
    get_district_repository,
    get_event_instance_repository,
    get_invitation_repository,
    get_leader_repository,
    get_planning_slot_repository,
    get_service_assignment_repository,
)
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.event_instance import EventInstance
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
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
    congregation: Congregation | list[Congregation],
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

    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="Bezirk")

    cong_repo = AsyncMock()
    cong_repo.list_by_district.return_value = (
        congregation if isinstance(congregation, list) else [congregation]
    )
    cong_repo.list_by_ids.return_value = []

    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = slots

    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = instances

    assignment_repo = AsyncMock()
    assignment_repo.list_by_planning_slots.return_value = assignments

    leader_repo = AsyncMock()
    leader_repo.list_by_district.return_value = []

    group_repo = AsyncMock()
    group_repo.list_by_district.return_value = []

    invitation_repo = AsyncMock()
    invitation_repo.list_by_source_planning_slots.return_value = []

    app.dependency_overrides[get_district_repository] = lambda: district_repo
    app.dependency_overrides[get_congregation_repository] = lambda: cong_repo
    app.dependency_overrides[get_planning_slot_repository] = lambda: slot_repo
    app.dependency_overrides[get_event_instance_repository] = lambda: instance_repo
    app.dependency_overrides[get_service_assignment_repository] = lambda: assignment_repo
    app.dependency_overrides[get_leader_repository] = lambda: leader_repo
    app.dependency_overrides[get_congregation_group_repository] = lambda: group_repo
    app.dependency_overrides[get_invitation_repository] = lambda: invitation_repo

    with (
        patch("app.adapters.api.deps.SqlUserRepository") as MockUserRepo,
        patch("app.adapters.api.deps.SqlMembershipRepository") as MockMembershipRepo,
    ):
        user_repo = AsyncMock()
        user_repo.get_by_sub.return_value = None
        user_repo.save = AsyncMock()
        MockUserRepo.return_value = user_repo

        membership_repo = AsyncMock()
        membership_repo.get_all_by_user.return_value = [membership]
        MockMembershipRepo.return_value = membership_repo

        yield TestClient(app)

    for dep in (
        get_district_repository,
        get_congregation_repository,
        get_planning_slot_repository,
        get_event_instance_repository,
        get_service_assignment_repository,
        get_leader_repository,
        get_congregation_group_repository,
        get_invitation_repository,
    ):
        app.dependency_overrides.pop(dep, None)
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


# ── Issue #466: shared slot visibility in the matrix ─────────────────────────

_SUNDAY = date(2026, 4, 5)
_MATRIX_PARAMS = {"from_dt": "2026-04-05T00:00:00Z", "to_dt": "2026-04-05T23:59:59Z"}


def _sunday_congregation(district_id: uuid.UUID, name: str = "Gemeinde A") -> Congregation:
    return Congregation.create(
        name=name, district_id=district_id, service_times=[{"weekday": 6, "time": "09:30"}]
    )


def _service_slot(
    district_id: uuid.UUID,
    *,
    congregation_id: uuid.UUID | None,
    planning_time: time = time(9, 30),
    status: PlanningSlotStatus = PlanningSlotStatus.ACTIVE,
    applicability: list[str] | None = None,
) -> PlanningSlot:
    return PlanningSlot.create(
        district_id=district_id,
        congregation_id=congregation_id,
        planning_date=_SUNDAY,
        planning_time=planning_time,
        category="Gottesdienst",
        status=status,
        applicability=applicability,
    )


def _matrix_rows(mock_oidc_adapter, district_id, congregations, slots, assignments=()):
    for client in _make_client_for(district_id, congregations, slots, [], list(assignments)):
        response = client.get(
            f"/api/v1/districts/{district_id}/matrix",
            headers={"Authorization": "Bearer valid_token"},
            params=_MATRIX_PARAMS,
        )
    # Exhaust the generator (no early return) so dependency overrides are cleaned up.
    assert response.status_code == 200
    return {row["congregation_id"]: row["cells"] for row in response.json()["rows"]}


def test_matrix_ignores_cancelled_slot_instead_of_showing_gap(mock_oidc_adapter) -> None:
    district_id = uuid.uuid4()
    congregation = _sunday_congregation(district_id)
    cancelled = _service_slot(
        district_id, congregation_id=congregation.id, status=PlanningSlotStatus.CANCELLED
    )

    rows = _matrix_rows(mock_oidc_adapter, district_id, [congregation], [cancelled])

    cell = rows[str(congregation.id)][_SUNDAY.isoformat()]
    assert cell["event_id"] is None
    assert cell["is_gap"] is False


def test_matrix_cancelled_earlier_slot_does_not_hide_active_slot(mock_oidc_adapter) -> None:
    district_id = uuid.uuid4()
    congregation = _sunday_congregation(district_id)
    cancelled = _service_slot(
        district_id, congregation_id=congregation.id, status=PlanningSlotStatus.CANCELLED
    )
    active = _service_slot(district_id, congregation_id=congregation.id, planning_time=time(10))
    assignment = ServiceAssignment.create(
        event_id=active.id, planning_slot_id=active.id, leader_name="Pr. Beispiel"
    )

    rows = _matrix_rows(
        mock_oidc_adapter, district_id, [congregation], [cancelled, active], [assignment]
    )

    cell = rows[str(congregation.id)][_SUNDAY.isoformat()]
    assert cell["event_id"] == str(active.id)
    assert cell["leader_name"] == "Pr. Beispiel"
    assert cell["is_gap"] is False


def test_matrix_district_slot_only_in_applicable_congregation_rows(mock_oidc_adapter) -> None:
    district_id = uuid.uuid4()
    applicable = _sunday_congregation(district_id, "Gemeinde A")
    other = _sunday_congregation(district_id, "Gemeinde B")
    district_slot = _service_slot(
        district_id, congregation_id=None, applicability=[str(applicable.id)]
    )

    rows = _matrix_rows(mock_oidc_adapter, district_id, [applicable, other], [district_slot])

    assert rows[str(applicable.id)][_SUNDAY.isoformat()]["event_id"] == str(district_slot.id)
    assert rows[str(other.id)][_SUNDAY.isoformat()]["event_id"] is None
