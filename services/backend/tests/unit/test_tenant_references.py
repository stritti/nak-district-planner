# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Request-body references (congregation_id, leader_id) must belong to the district (#468).

Every endpoint that stores such an ID from a request body rejects IDs that are
unknown or belong to another district with the same 422 response, before
anything is persisted.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api import tenant_references
from app.adapters.api.routers import calendar_integrations as calendar_router
from app.adapters.api.routers import districts as districts_router
from app.adapters.api.routers import export as export_router
from app.adapters.api.routers import leaders as leaders_router
from app.adapters.api.routers import planning_series as series_router
from app.adapters.api.routers import registrations as registrations_router
from app.adapters.api.routers import service_assignments as sa_router
from app.adapters.api.schemas.calendar_integration import CalendarIntegrationCreate
from app.adapters.api.schemas.district import CongregationCreate, CongregationUpdate
from app.adapters.api.schemas.export_token import ExportTokenCreate
from app.adapters.api.schemas.leader import LeaderCreate, LeaderUpdate
from app.adapters.api.schemas.planning_series import PlanningSeriesCreate, PlanningSeriesUpdate
from app.adapters.api.schemas.registration import RegistrationApprove, RegistrationCreate
from app.adapters.api.schemas.service_assignment import (
    ServiceAssignmentCreate,
    ServiceAssignmentUpdate,
)
from app.adapters.auth.permissions import PermissionError
from app.domain.models.calendar_integration import CalendarType
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.export_token import TokenType
from app.domain.models.invitation import InvitationTargetType
from app.domain.models.leader import Leader
from app.domain.models.leader_registration import LeaderRegistration
from app.domain.models.membership import ScopeType
from app.domain.models.planning_series import PlanningSeries
from app.domain.models.planning_slot import PlanningSlot
from app.domain.models.role import Role
from app.domain.models.service_assignment import ServiceAssignment

DISTRICT = uuid.uuid4()
OTHER_DISTRICT = uuid.uuid4()
FOREIGN_ID = uuid.uuid4()


def _db(owner_district: uuid.UUID | None = OTHER_DISTRICT) -> AsyncMock:
    """Session whose ownership lookup reports ``owner_district`` for any referenced ID."""
    db = AsyncMock()
    db.scalar.return_value = owner_district
    return db


def _found(repo_attr_value: object) -> AsyncMock:
    repo = AsyncMock()
    repo.get.return_value = repo_attr_value
    return repo


def _assert_rejected(exc: pytest.ExceptionInfo[HTTPException], field: str) -> None:
    assert exc.value.status_code == 422
    assert field in exc.value.detail


# ── helper ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_helper_accepts_reference_of_same_district() -> None:
    db = _db(owner_district=DISTRICT)
    await tenant_references.ensure_congregation_in_district(db, DISTRICT, uuid.uuid4())
    await tenant_references.ensure_leader_in_district(db, DISTRICT, uuid.uuid4())
    assert db.scalar.await_count == 2


@pytest.mark.asyncio
async def test_helper_skips_lookup_for_missing_reference() -> None:
    db = _db()
    await tenant_references.ensure_congregation_in_district(db, DISTRICT, None)
    await tenant_references.ensure_leader_in_district(db, DISTRICT, None)
    db.scalar.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", [OTHER_DISTRICT, None], ids=["foreign", "unknown"])
async def test_helper_rejects_foreign_and_unknown_ids_identically(owner: uuid.UUID | None) -> None:
    with pytest.raises(HTTPException) as cong_exc:
        await tenant_references.ensure_congregation_in_district(_db(owner), DISTRICT, FOREIGN_ID)
    with pytest.raises(HTTPException) as leader_exc:
        await tenant_references.ensure_leader_in_district(_db(owner), DISTRICT, FOREIGN_ID)

    _assert_rejected(cong_exc, "congregation_id")
    _assert_rejected(leader_exc, "leader_id")
    # Same body for unknown and foreign IDs: no cross-tenant existence oracle.
    assert str(FOREIGN_ID) not in cong_exc.value.detail


# ── export tokens ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["congregation_id", "leader_id"])
async def test_export_token_rejects_foreign_reference(field: str) -> None:
    repo = AsyncMock()
    body = ExportTokenCreate(
        label="X", token_type=TokenType.INTERNAL, district_id=DISTRICT, **{field: FOREIGN_ID}
    )
    with patch("app.adapters.api.routers.export.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await export_router.create_export_token(object(), body, _db(), repo=repo)

    _assert_rejected(exc, field)
    repo.save.assert_not_awaited()


# ── calendar integrations ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_calendar_integration_rejects_foreign_congregation_for_district_admin() -> None:
    """District admin of DISTRICT (no congregation role) must not attach a foreign congregation."""
    service = AsyncMock()
    body = CalendarIntegrationCreate(
        district_id=DISTRICT,
        congregation_id=FOREIGN_ID,
        name="Kalender",
        type=CalendarType.ICS,
        credentials={"url": "https://example.org/cal.ics"},
    )
    with (
        patch(
            "app.adapters.api.routers.calendar_integrations.assert_has_role_in_congregation",
            side_effect=PermissionError("no congregation role"),
        ),
        patch("app.adapters.api.routers.calendar_integrations.require_role_in_district"),
    ):
        with pytest.raises(HTTPException) as exc:
            await calendar_router.create_calendar_integration(
                body, object(), _db(), service=service, cong_repo=AsyncMock()
            )

    _assert_rejected(exc, "congregation_id")
    service.create_integration.assert_not_awaited()


# ── registrations ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_registration_submit_rejects_foreign_congregation() -> None:
    reg_repo = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await registrations_router.submit_registration(
            DISTRICT,
            RegistrationCreate(name="Max", email="max@example.com", congregation_id=FOREIGN_ID),
            _db(),
            credentials=None,
            district_repo=_found(District.create(name="D")),
            reg_repo=reg_repo,
        )

    _assert_rejected(exc, "congregation_id")
    reg_repo.save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["body", "registration"])
async def test_registration_approve_rejects_foreign_congregation(source: str) -> None:
    reg = LeaderRegistration.create(
        district_id=DISTRICT,
        name="Max",
        email="max@example.com",
        congregation_id=FOREIGN_ID if source == "registration" else None,
    )
    body = RegistrationApprove(
        role=Role.VIEWER,
        scope_type=ScopeType.DISTRICT,
        scope_id=DISTRICT,
        congregation_id=FOREIGN_ID if source == "body" else None,
    )
    leader_repo = AsyncMock()
    with patch("app.adapters.api.routers.registrations.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await registrations_router.approve_registration(
                DISTRICT,
                reg.id,
                body,
                object(),
                _db(),
                reg_repo=_found(reg),
                cong_repo=AsyncMock(),
                leader_repo=leader_repo,
                mem_repo=AsyncMock(),
            )

    _assert_rejected(exc, "congregation_id")
    leader_repo.save.assert_not_awaited()


# ── leaders ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_leader_create_rejects_foreign_congregation() -> None:
    leaders_repo = AsyncMock()
    with patch("app.adapters.api.routers.leaders.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await leaders_router.create_leader(
                DISTRICT,
                LeaderCreate(name="N", congregation_id=FOREIGN_ID),
                object(),
                _db(),
                districts=_found(District.create(name="D")),
                leaders_repo=leaders_repo,
            )

    _assert_rejected(exc, "congregation_id")
    leaders_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_leader_update_rejects_foreign_congregation() -> None:
    leaders_repo = _found(Leader.create(name="L", district_id=DISTRICT))
    with patch("app.adapters.api.routers.leaders.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await leaders_router.update_leader(
                DISTRICT,
                uuid.uuid4(),
                LeaderUpdate(congregation_id=FOREIGN_ID),
                object(),
                _db(),
                leaders_repo=leaders_repo,
            )

    _assert_rejected(exc, "congregation_id")
    leaders_repo.save.assert_not_awaited()


# ── planning series ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_planning_series_create_rejects_foreign_congregation() -> None:
    repo = AsyncMock()
    body = PlanningSeriesCreate(
        district_id=DISTRICT, congregation_id=FOREIGN_ID, default_planning_time=time(9, 30)
    )
    with patch("app.adapters.api.routers.planning_series.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await series_router.create_planning_series(body, object(), _db(), repo=repo)

    _assert_rejected(exc, "congregation_id")
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_planning_series_update_rejects_foreign_congregation() -> None:
    series = PlanningSeries.create(district_id=DISTRICT, default_planning_time=time(9, 30))
    repo = _found(series)
    with patch("app.adapters.api.routers.planning_series.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await series_router.update_planning_series(
                series.id, PlanningSeriesUpdate(congregation_id=FOREIGN_ID), object(), _db(), repo=repo
            )

    _assert_rejected(exc, "congregation_id")
    repo.save.assert_not_awaited()


# ── congregations: invitation target ────────────────────────────────────────


@pytest.mark.asyncio
async def test_congregation_create_rejects_foreign_invitation_target() -> None:
    cong_repo = AsyncMock()
    body = CongregationCreate(
        name="G",
        invitation_target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        invitation_target_congregation_id=FOREIGN_ID,
    )
    with patch("app.adapters.api.routers.districts.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await districts_router.create_congregation(
                DISTRICT,
                body,
                object(),
                _db(),
                district_repo=_found(District.create(name="D")),
                cong_repo=cong_repo,
                group_repo=AsyncMock(),
            )

    _assert_rejected(exc, "invitation_target_congregation_id")
    cong_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_congregation_update_rejects_foreign_invitation_target() -> None:
    congregation = Congregation.create(name="G", district_id=DISTRICT)
    cong_repo = _found(congregation)
    body = CongregationUpdate(
        invitation_target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        invitation_target_congregation_id=FOREIGN_ID,
    )
    with patch("app.adapters.api.routers.districts.assert_has_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await districts_router.update_congregation(
                DISTRICT, congregation.id, body, object(), _db(), cong_repo=cong_repo,
                group_repo=AsyncMock(),
            )

    _assert_rejected(exc, "invitation_target_congregation_id")
    cong_repo.save.assert_not_awaited()


# ── service assignments ─────────────────────────────────────────────────────


def _slot() -> PlanningSlot:
    return PlanningSlot.create(
        district_id=DISTRICT, planning_date=date(2026, 6, 15), planning_time=time(10, 0)
    )


@pytest.mark.asyncio
async def test_assignment_create_rejects_foreign_leader() -> None:
    slot = _slot()
    sa_repo = AsyncMock()
    with patch("app.adapters.api.routers.service_assignments.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await sa_router.create_assignment(
                slot.id, ServiceAssignmentCreate(leader_id=FOREIGN_ID), object(), _db(),
                _found(slot), sa_repo,
            )

    _assert_rejected(exc, "leader_id")
    sa_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_assignment_update_rejects_foreign_leader() -> None:
    slot = _slot()
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    sa_repo = _found(assignment)
    with patch("app.adapters.api.routers.service_assignments.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await sa_router.update_assignment(
                slot.id, assignment.id, ServiceAssignmentUpdate(leader_id=FOREIGN_ID), object(),
                _db(), _found(slot), sa_repo, AsyncMock(),
            )

    _assert_rejected(exc, "leader_id")
    sa_repo.save.assert_not_awaited()
