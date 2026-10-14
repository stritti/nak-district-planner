# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Check that IDs taken from a request body belong to the addressed district.

Path parameters are resolved and authorized by the routers; IDs inside request
bodies (congregation_id, leader_id, ...) are not, so a planner of district A
could otherwise attach records of district B. Unknown and foreign IDs both
answer 422 with the same message (like ``_validate_group_assignment`` in the
districts router), so the check does not reveal whether an ID exists elsewhere.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.orm_models.leader import LeaderORM


def _reject(field: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"{field} ist ungueltig oder gehoert nicht zum Bezirk",
    )


async def ensure_congregation_in_district(
    session: AsyncSession,
    district_id: uuid.UUID,
    congregation_id: uuid.UUID | None,
    *,
    field: str = "congregation_id",
) -> None:
    """Raise 422 unless ``congregation_id`` is None or a congregation of the district."""
    if congregation_id is None:
        return
    owner = await session.scalar(
        select(CongregationORM.district_id).where(CongregationORM.id == congregation_id)
    )
    if owner != district_id:
        raise _reject(field)


async def ensure_leader_in_district(
    session: AsyncSession,
    district_id: uuid.UUID,
    leader_id: uuid.UUID | None,
    *,
    field: str = "leader_id",
) -> None:
    """Raise 422 unless ``leader_id`` is None or a leader of the district."""
    if leader_id is None:
        return
    owner = await session.scalar(select(LeaderORM.district_id).where(LeaderORM.id == leader_id))
    if owner != district_id:
        raise _reject(field)
