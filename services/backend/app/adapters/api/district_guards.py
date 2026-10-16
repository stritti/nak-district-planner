"""Shared district-level guards for routers.

Centralises the "authorise first, then 404 on unknown district" sequence that
was duplicated across routers, so error text and ordering stay consistent.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.auth.permissions import AuthContext, require_role_in_district
from app.adapters.db.orm_models.district import DistrictORM
from app.domain.models.role import Role

DISTRICT_NOT_FOUND_DETAIL = "Bezirk nicht gefunden"


async def require_district_admin(
    district_id: uuid.UUID, auth: AuthContext, db: AsyncSession
) -> None:
    """Require DISTRICT_ADMIN in the district, then verify the district exists."""
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    if await db.get(DistrictORM, district_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=DISTRICT_NOT_FOUND_DETAIL)
