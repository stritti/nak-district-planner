from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.adapters.api.routers.leader_unavailabilities import router
from app.adapters.api.schemas.leader_unavailability import LeaderUnavailabilityCreate
from app.domain.models.leader_unavailability import UnavailabilityReason


def test_create_schema_rejects_reversed_period() -> None:
    with pytest.raises(ValidationError, match="end_at muss nach start_at liegen"):
        LeaderUnavailabilityCreate(
            leader_id="00000000-0000-0000-0000-000000000001",
            start_at=datetime(2026, 2, 2, tzinfo=UTC),
            end_at=datetime(2026, 2, 1, tzinfo=UTC),
            reason=UnavailabilityReason.VACATION,
        )


def test_router_registers_crud_routes() -> None:
    routes = {(route.path, method) for route in router.routes for method in route.methods}

    assert ("/api/v1/districts/{district_id}/leader-unavailabilities", "GET") in routes
    assert ("/api/v1/districts/{district_id}/leader-unavailabilities", "POST") in routes
    assert (
        "/api/v1/districts/{district_id}/leader-unavailabilities/{unavailability_id}",
        "PATCH",
    ) in routes
    assert (
        "/api/v1/districts/{district_id}/leader-unavailabilities/{unavailability_id}",
        "DELETE",
    ) in routes
