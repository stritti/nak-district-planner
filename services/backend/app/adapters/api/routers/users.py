# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""User administration: memberships per unit and the global superadmin status.

  GET    /api/v1/users                                      — users the caller may manage
  PUT    /api/v1/users/{sub}/memberships                    — assign a role in one unit
  DELETE /api/v1/users/{sub}/memberships/{membership_id}    — remove one membership
  PUT    /api/v1/users/{sub}/superadmin                     — grant or revoke (superadmins only)

Superadmins manage every user and unit. A district admin manages the district
and its congregations, a congregation admin only that congregation; neither
may grant a role above their own, and a congregation admin never touches
district memberships. Other administrators see only users who already hold a
membership in a unit they manage; new users arrive through registration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.api.deps import (
    CurrentUserContext,
    CurrentUserWithMemberships,
    DbSession,
    get_congregation_repository,
    get_district_repository,
    get_membership_repository,
    get_user_repository,
)
from app.adapters.api.schemas.user_admin import (
    AdminMembershipOut,
    AdminUserOut,
    MembershipAssign,
    SuperadminUpdate,
)
from app.adapters.auth.permissions import require_superadmin
from app.adapters.db.domain_audit import insert_statement_audit, statement_audit_row
from app.adapters.db.orm_models.audit_log import AuditAction
from app.adapters.db.repositories.membership import SqlMembershipRepository
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.membership_policy import management_level, manages_any_unit, may_manage
from app.domain.models.user import User
from app.domain.ports.repositories import (
    CongregationRepository,
    DistrictRepository,
    UserRepository,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])

_SUPERADMIN_ERRORS = {
    "forbidden": (
        status.HTTP_403_FORBIDDEN,
        "Nur Superadmins dürfen den Superadmin-Status ändern.",
    ),
    "not_found": (status.HTTP_404_NOT_FOUND, "Benutzer nicht gefunden"),
    "last_superadmin": (
        status.HTTP_409_CONFLICT,
        "Der letzte Superadmin kann nicht entzogen werden.",
    ),
    "concurrent_change": (
        status.HTTP_409_CONFLICT,
        "Gleichzeitige Änderung des Superadmin-Status, bitte erneut versuchen.",
    ),
}


@dataclass(frozen=True)
class _Unit:
    name: str
    district_id: uuid.UUID


async def _units(
    district_repo: DistrictRepository,
    congregation_repo: CongregationRepository,
    memberships: list[Membership],
) -> dict[uuid.UUID, _Unit]:
    """Name and district of every unit the memberships refer to and the caller may read."""
    congregation_ids = [m.scope_id for m in memberships if m.scope_type == ScopeType.CONGREGATION]
    units = {d.id: _Unit(d.name, d.id) for d in await district_repo.list_all()}
    for congregation in await congregation_repo.list_by_ids(congregation_ids):
        units[congregation.id] = _Unit(congregation.name, congregation.district_id)
    return units


async def _unit(
    district_repo: DistrictRepository,
    congregation_repo: CongregationRepository,
    scope_type: ScopeType,
    scope_id: uuid.UUID,
) -> _Unit:
    """The unit a write targets; unknown or unreadable units answer 404 alike."""
    if scope_type == ScopeType.DISTRICT:
        district = await district_repo.get(scope_id)
        if district is not None:
            return _Unit(district.name, district.id)
    else:
        congregation = await congregation_repo.get(scope_id)
        if congregation is not None:
            return _Unit(congregation.name, congregation.district_id)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Einheit nicht gefunden")


def _level(auth: CurrentUserContext, membership_scope: ScopeType, scope_id: uuid.UUID, unit: _Unit):
    return management_level(
        auth.memberships,
        is_superadmin=auth.user.is_superadmin,
        scope_type=membership_scope,
        scope_id=scope_id,
        district_id=unit.district_id,
    )


def _user_out(
    user: User,
    memberships: list[Membership],
    units: dict[uuid.UUID, _Unit],
    auth: CurrentUserContext,
) -> AdminUserOut:
    shown = []
    for membership in memberships:
        unit = units.get(membership.scope_id)
        if unit is None or _level(auth, membership.scope_type, membership.scope_id, unit) is None:
            continue
        shown.append(
            AdminMembershipOut(
                id=membership.id,
                role=membership.role,
                scope_type=membership.scope_type,
                scope_id=membership.scope_id,
                scope_name=unit.name,
                district_id=unit.district_id,
            )
        )
    shown.sort(key=lambda m: (m.scope_name or "", m.scope_type.value))
    return AdminUserOut(
        sub=user.sub,
        email=user.email,
        username=user.username,
        name=user.name,
        is_superadmin=user.is_superadmin if auth.user.is_superadmin else None,
        memberships=shown,
    )


async def _target_user(user_repo: UserRepository, sub: str) -> User:
    user = await user_repo.get_by_sub(sub)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden")
    return user


async def _single_user_out(
    sub: str,
    auth: CurrentUserContext,
    user_repo: UserRepository,
    membership_repo: SqlMembershipRepository,
    district_repo: DistrictRepository,
    congregation_repo: CongregationRepository,
) -> AdminUserOut:
    user = await _target_user(user_repo, sub)
    memberships = await membership_repo.get_all_by_user(sub)
    return _user_out(
        user, memberships, await _units(district_repo, congregation_repo, memberships), auth
    )


@router.get("", response_model=list[AdminUserOut])
async def list_users(
    auth: CurrentUserWithMemberships,
    user_repo: UserRepository = Depends(get_user_repository),
    membership_repo: SqlMembershipRepository = Depends(get_membership_repository),
    district_repo: DistrictRepository = Depends(get_district_repository),
    congregation_repo: CongregationRepository = Depends(get_congregation_repository),
) -> list[AdminUserOut]:
    """Users with the memberships the caller manages; superadmins see every user."""
    if not manages_any_unit(auth.memberships, is_superadmin=auth.user.is_superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Keine Benutzerverwaltung"
        )
    memberships = await membership_repo.list_visible()
    units = await _units(district_repo, congregation_repo, memberships)
    by_user: dict[str, list[Membership]] = {}
    for membership in memberships:
        by_user.setdefault(membership.user_sub, []).append(membership)

    if auth.user.is_superadmin:
        users = await user_repo.list_all()
        return [_user_out(u, by_user.get(u.sub, []), units, auth) for u in users]

    result = [
        _user_out(u, by_user[u.sub], units, auth)
        for u in await user_repo.list_by_subs(set(by_user))
    ]
    return [user for user in result if user.memberships]


@router.put("/{sub}/memberships", response_model=AdminUserOut)
async def assign_membership(
    sub: str,
    body: MembershipAssign,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    user_repo: UserRepository = Depends(get_user_repository),
    membership_repo: SqlMembershipRepository = Depends(get_membership_repository),
    district_repo: DistrictRepository = Depends(get_district_repository),
    congregation_repo: CongregationRepository = Depends(get_congregation_repository),
) -> AdminUserOut:
    """Assign a role in one unit; the user's memberships in other units stay as they are."""
    await _target_user(user_repo, sub)
    unit = await _unit(district_repo, congregation_repo, body.scope_type, body.scope_id)
    existing = await membership_repo.get_by_user_and_scope(sub, body.scope_type, body.scope_id)
    level = _level(auth, body.scope_type, body.scope_id, unit)
    if not may_manage(level, body.role, existing.role if existing else None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Diese Rolle in dieser Einheit darf nur eine höher berechtigte Person vergeben.",
        )

    membership = await membership_repo.upsert_by_scope(
        user_sub=sub, scope_type=body.scope_type, scope_id=body.scope_id, role=body.role
    )
    if existing is None or existing.role != body.role:
        await insert_statement_audit(
            db,
            statement_audit_row(
                AuditAction.CREATE if existing is None else AuditAction.UPDATE,
                "membership",
                resource_id=membership.id,
                district_id=unit.district_id,
                congregation_id=body.scope_id
                if body.scope_type == ScopeType.CONGREGATION
                else None,
                old_values={"role": existing.role} if existing else None,
                new_values={
                    "user_sub": sub,
                    "role": body.role,
                    "scope_type": body.scope_type,
                    "scope_id": body.scope_id,
                },
            ),
        )
    return await _single_user_out(
        sub, auth, user_repo, membership_repo, district_repo, congregation_repo
    )


@router.delete("/{sub}/memberships/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_membership(
    sub: str,
    membership_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    membership_repo: SqlMembershipRepository = Depends(get_membership_repository),
    district_repo: DistrictRepository = Depends(get_district_repository),
    congregation_repo: CongregationRepository = Depends(get_congregation_repository),
) -> None:
    """Remove one membership; the user's other memberships stay."""
    membership = await membership_repo.get_by_id(membership_id)
    if membership is None or membership.user_sub != sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zuordnung nicht gefunden"
        )
    unit = await _unit(district_repo, congregation_repo, membership.scope_type, membership.scope_id)
    if not may_manage(
        _level(auth, membership.scope_type, membership.scope_id, unit), membership.role
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Diese Zuordnung darf nur eine höher berechtigte Person entfernen.",
        )

    await insert_statement_audit(
        db,
        statement_audit_row(
            AuditAction.DELETE,
            "membership",
            resource_id=membership.id,
            district_id=unit.district_id,
            congregation_id=membership.scope_id
            if membership.scope_type == ScopeType.CONGREGATION
            else None,
            old_values={
                "user_sub": sub,
                "role": membership.role,
                "scope_type": membership.scope_type,
                "scope_id": membership.scope_id,
            },
        ),
    )
    await membership_repo.delete(membership.id)


@router.put("/{sub}/superadmin", response_model=AdminUserOut)
async def set_superadmin(
    sub: str,
    body: SuperadminUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    user_repo: UserRepository = Depends(get_user_repository),
    membership_repo: SqlMembershipRepository = Depends(get_membership_repository),
    district_repo: DistrictRepository = Depends(get_district_repository),
    congregation_repo: CongregationRepository = Depends(get_congregation_repository),
) -> AdminUserOut:
    """Grant or revoke the global superadmin status; the last superadmin always remains."""
    require_superadmin(auth.user, detail=_SUPERADMIN_ERRORS["forbidden"][1])
    target = await _target_user(user_repo, sub)
    if target.is_superadmin == body.is_superadmin:
        return await _single_user_out(
            sub, auth, user_repo, membership_repo, district_repo, congregation_repo
        )
    # Written before the change: a superadmin revoking themselves loses the
    # right to insert audit entries once the flag is gone. A refused change
    # rolls the entry back together with the request.
    await insert_statement_audit(
        db,
        statement_audit_row(
            AuditAction.UPDATE,
            "user_superadmin",
            resource_id=None,
            old_values={"is_superadmin": target.is_superadmin},
            new_values={"user_sub": sub, "is_superadmin": body.is_superadmin},
        ),
    )
    outcome = await user_repo.set_superadmin(sub, body.is_superadmin)
    if outcome in _SUPERADMIN_ERRORS:
        code, detail = _SUPERADMIN_ERRORS[outcome]
        raise HTTPException(status_code=code, detail=detail)
    if sub == auth.user.sub:
        auth.user.is_superadmin = body.is_superadmin
    return await _single_user_out(
        sub, auth, user_repo, membership_repo, district_repo, congregation_repo
    )
