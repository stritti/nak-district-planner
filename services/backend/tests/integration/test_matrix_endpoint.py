from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.adapters.api import deps
from app.main import app
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.event import Event
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment
from app.domain.models.user import User


def test_matrix_endpoint_returns_gap_assigned_and_empty_cells() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(
        name="Gemeinde A",
        district_id=district_id,
        service_times=[{"weekday": 6, "time": "09:30"}],
    )

    gap_start = datetime(2026, 4, 8, 18, 0, tzinfo=timezone.utc)
    assigned_start = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)

    gap_event = Event.create(
        title="Gottesdienst Mittwoch",
        start_at=gap_start,
        end_at=gap_start + timedelta(hours=1),
        district_id=district_id,
        congregation_id=congregation.id,
        category="Gottesdienst",
    )
    assigned_event = Event.create(
        title="Gottesdienst Freitag",
        start_at=assigned_start,
        end_at=assigned_start + timedelta(hours=1),
        district_id=district_id,
        congregation_id=congregation.id,
        category="Gottesdienst",
    )
    assignment = ServiceAssignment.create(
        event_id=assigned_event.id,
        leader_name="Pr. Beispiel",
        status=AssignmentStatus.ASSIGNED,
    )

    async def override_current_user() -> User:
        return User(sub="u1", email="u1@example.com", username="u1")

    async def override_db_session() -> AsyncMock:
        return AsyncMock()

    app.dependency_overrides[deps.get_current_active_user] = override_current_user
    app.dependency_overrides[deps.get_db_session] = override_db_session

    try:
        with (
            patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls,
            patch("app.adapters.api.routers.districts.SqlCongregationRepository") as cong_repo_cls,
            patch("app.adapters.api.routers.districts.SqlEventRepository") as event_repo_cls,
            patch(
                "app.adapters.api.routers.districts.SqlServiceAssignmentRepository"
            ) as assignment_repo_cls,
            patch("app.adapters.api.routers.districts.SqlLeaderRepository") as leader_repo_cls,
            patch(
                "app.adapters.api.routers.districts.SqlCongregationGroupRepository"
            ) as group_repo_cls,
            patch(
                "app.adapters.api.routers.districts.SqlInvitationRepository"
            ) as invitation_repo_cls,
        ):
            district_repo = AsyncMock()
            district_repo.get.return_value = District.create(name="Bezirk")
            district_repo_cls.return_value = district_repo

            cong_repo = AsyncMock()
            cong_repo.list_by_district.return_value = [congregation]
            cong_repo.list_by_ids.return_value = []
            cong_repo_cls.return_value = cong_repo

            event_repo = AsyncMock()
            event_repo.list.return_value = ([gap_event, assigned_event], 2)
            event_repo_cls.return_value = event_repo

            assignment_repo = AsyncMock()
            assignment_repo.list_by_events.return_value = [assignment]
            assignment_repo_cls.return_value = assignment_repo

            leader_repo = AsyncMock()
            leader_repo.list_by_district.return_value = []
            leader_repo_cls.return_value = leader_repo

            group_repo = AsyncMock()
            group_repo.list_by_district.return_value = []
            group_repo_cls.return_value = group_repo

            invitation_repo = AsyncMock()
            invitation_repo.list_by_source_events.return_value = []
            invitation_repo_cls.return_value = invitation_repo

            client = TestClient(app)
            response = client.get(
                f"/api/v1/districts/{district_id}/matrix",
                params={
                    "from_dt": "2026-04-06T00:00:00Z",
                    "to_dt": "2026-04-12T23:59:59Z",
                },
            )

        assert response.status_code == 200
        payload = response.json()

        row = payload["rows"][0]
        gap_cell = row["cells"]["2026-04-08"]
        assigned_cell = row["cells"]["2026-04-10"]
        empty_cell = row["cells"]["2026-04-12"]

        assert gap_cell["event_id"] == str(gap_event.id)
        assert gap_cell["is_gap"] is True
        assert gap_cell["assignment_id"] is None

        assert assigned_cell["event_id"] == str(assigned_event.id)
        assert assigned_cell["is_gap"] is False
        assert assigned_cell["leader_name"] == "Pr. Beispiel"

        assert empty_cell["event_id"] is None
        assert empty_cell["is_gap"] is False
    finally:
        app.dependency_overrides.pop(deps.get_current_active_user, None)
        app.dependency_overrides.pop(deps.get_db_session, None)
