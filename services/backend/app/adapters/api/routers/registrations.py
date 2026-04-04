"""
Registration workflow API routes.

Public (no auth):
  GET  /api/v1/public/districts                              — list districts (for registration form)
  GET  /api/v1/public/districts/{district_id}/congregations  — list congregations (for registration form)
  POST /api/v1/districts/{district_id}/registrations         — submit self-registration

District-admin only:
  GET    /api/v1/districts/{district_id}/registrations
  POST   /api/v1/districts/{district_id}/registrations/{id}/approve
  POST   /api/v1/districts/{district_id}/registrations/{id}/reject
  DELETE /api/v1/districts/{district_id}/registrations/{id}
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.auth.permissions import PermissionError, assert_has_role_in_district
from app.adapters.api.schemas.registration import (
    RegistrationApprove,
    RegistrationCreate,
    RegistrationReject,
    RegistrationResponse,
)
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.leader_registration import SqlLeaderRegistrationRepository
from app.domain.models.leader import Leader
from app.domain.models.leader_registration import LeaderRegistration, RegistrationStatus
from app.domain.models.role import Role

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public lookup router — minimal data for the self-registration form
# ---------------------------------------------------------------------------


class PublicDistrictInfo(BaseModel):
    """Minimal district info returned by the public listing endpoint."""

    id: uuid.UUID
    name: str


class PublicCongregationInfo(BaseModel):
    """Minimal congregation info returned by the public listing endpoint."""

    id: uuid.UUID
    name: str


public_router = APIRouter(prefix="/api/v1/public", tags=["registrations-public"])


@public_router.get("/districts", response_model=list[PublicDistrictInfo])
async def list_districts_public(db: DbSession) -> list[PublicDistrictInfo]:
    """List all districts — public endpoint for the self-registration form."""
    districts = await SqlDistrictRepository(db).list_all()
    return [PublicDistrictInfo(id=d.id, name=d.name) for d in districts]


@public_router.get(
    "/districts/{district_id}/congregations",
    response_model=list[PublicCongregationInfo],
)
async def list_congregations_public(
    district_id: uuid.UUID, db: DbSession
) -> list[PublicCongregationInfo]:
    """List congregations for a district — public endpoint for the self-registration form."""
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    congregations = await SqlCongregationRepository(db).list_by_district(district_id)
    return [PublicCongregationInfo(id=c.id, name=c.name) for c in congregations]


# ---------------------------------------------------------------------------
# Registration router (per-district)
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/api/v1/districts/{district_id}/registrations",
    tags=["registrations"],
)

# Optional bearer — used only to extract user_sub when the registrant is logged in
_optional_bearer = HTTPBearer(auto_error=False)


def _to_response(reg: LeaderRegistration) -> RegistrationResponse:
    return RegistrationResponse(
        id=reg.id,
        district_id=reg.district_id,
        name=reg.name,
        email=reg.email,
        rank=reg.rank,
        congregation_id=reg.congregation_id,
        special_role=reg.special_role,
        phone=reg.phone,
        notes=reg.notes,
        status=reg.status,
        rejection_reason=reg.rejection_reason,
        user_sub=reg.user_sub,
        created_at=reg.created_at,
        updated_at=reg.updated_at,
    )


# ---------------------------------------------------------------------------
# Public endpoint — no authentication required
# ---------------------------------------------------------------------------


@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def submit_registration(
    district_id: uuid.UUID,
    body: RegistrationCreate,
    db: DbSession,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_optional_bearer),
) -> RegistrationResponse:
    """
    Submit a self-registration request for a new Amtstragender.

    This endpoint is **public** — no authentication is required, making it
    IDP-agnostic.  If a Bearer token is provided the registrant's OIDC subject
    is stored for later linking, but the token is not validated here (the admin
    can see the connection in the review UI).
    """
    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")

    # Extract user_sub from token if present (best-effort, no hard validation)
    user_sub: str | None = None
    if credentials:
        try:
            unverified = jwt.decode(
                credentials.credentials,
                options={"verify_signature": False},
            )
            user_sub = unverified.get("sub")
        except Exception:
            pass  # Token present but unreadable — proceed without linking

    reg = LeaderRegistration.create(
        district_id=district_id,
        name=body.name,
        email=body.email,
        rank=body.rank,
        congregation_id=body.congregation_id,
        special_role=body.special_role,
        phone=body.phone,
        notes=body.notes,
        user_sub=user_sub,
    )
    await SqlLeaderRegistrationRepository(db).save(reg)
    logger.info(
        "New registration submitted: registration_id=%s district_id=%s",
        reg.id,
        district_id,
    )
    return _to_response(reg)


# ---------------------------------------------------------------------------
# District-admin endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[RegistrationResponse])
async def list_registrations(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    status_filter: Optional[RegistrationStatus] = Query(default=None, alias="status"),
) -> list[RegistrationResponse]:
    """List registration requests for a district (DISTRICT_ADMIN only)."""
    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if not await SqlDistrictRepository(db).get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")

    registrations = await SqlLeaderRegistrationRepository(db).list_by_district(
        district_id, status=status_filter
    )
    return [_to_response(r) for r in registrations]


@router.post(
    "/{registration_id}/approve",
    response_model=RegistrationResponse,
)
async def approve_registration(
    district_id: uuid.UUID,
    registration_id: uuid.UUID,
    body: RegistrationApprove,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> RegistrationResponse:
    """
    Approve a registration request (DISTRICT_ADMIN only).

    Creates an active Leader record and marks the registration as APPROVED.
    The admin may override the congregation, rank, or special role.
    """
    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    reg_repo = SqlLeaderRegistrationRepository(db)
    reg = await reg_repo.get(registration_id)
    if not reg or reg.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registrierung nicht gefunden"
        )
    if reg.status != RegistrationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Registrierung ist bereits {reg.status.value}",
        )

    # Admin can override congregation / rank / special_role from the request
    congregation_id = (
        body.congregation_id if body.congregation_id is not None else reg.congregation_id
    )
    rank = body.rank if body.rank is not None else reg.rank
    special_role = body.special_role if body.special_role is not None else reg.special_role

    # Create the Leader
    leader = Leader.create(
        name=reg.name,
        district_id=district_id,
        rank=rank,
        congregation_id=congregation_id,
        special_role=special_role,
        email=reg.email,
        phone=reg.phone,
        notes=reg.notes,
        is_active=True,
    )
    await SqlLeaderRepository(db).save(leader)

    # Update registration status
    reg.status = RegistrationStatus.APPROVED
    reg.updated_at = datetime.now(timezone.utc)
    await reg_repo.save(reg)

    logger.info("Registration approved; leader record created.")
    return _to_response(reg)


@router.post(
    "/{registration_id}/reject",
    response_model=RegistrationResponse,
)
async def reject_registration(
    district_id: uuid.UUID,
    registration_id: uuid.UUID,
    body: RegistrationReject,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> RegistrationResponse:
    """Reject a registration request (DISTRICT_ADMIN only)."""
    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    reg_repo = SqlLeaderRegistrationRepository(db)
    reg = await reg_repo.get(registration_id)
    if not reg or reg.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registrierung nicht gefunden"
        )
    if reg.status != RegistrationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Registrierung ist bereits {reg.status.value}",
        )

    reg.status = RegistrationStatus.REJECTED
    reg.rejection_reason = body.reason
    reg.updated_at = datetime.now(timezone.utc)
    await reg_repo.save(reg)

    logger.info("Registration rejected.")
    return _to_response(reg)


@router.delete("/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_registration(
    district_id: uuid.UUID,
    registration_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
) -> None:
    """Delete a registration request (DISTRICT_ADMIN only)."""
    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    reg_repo = SqlLeaderRegistrationRepository(db)
    reg = await reg_repo.get(registration_id)
    if not reg or reg.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registrierung nicht gefunden"
        )
    await reg_repo.delete(registration_id)
