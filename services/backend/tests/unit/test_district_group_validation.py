from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers.districts import _validate_group_assignment


@pytest.mark.asyncio
async def test_validate_group_assignment_accepts_none() -> None:
    session = MagicMock()
    await _validate_group_assignment(session, uuid.uuid4(), None)


@pytest.mark.asyncio
async def test_validate_group_assignment_rejects_cross_district() -> None:
    session = MagicMock()
    district_id = uuid.uuid4()
    group_id = uuid.uuid4()

    with patch("app.adapters.api.routers.districts.SqlCongregationGroupRepository") as repo_cls:
        repo = MagicMock()
        repo.get = AsyncMock(return_value=MagicMock(id=group_id, district_id=uuid.uuid4()))
        repo_cls.return_value = repo

        with pytest.raises(HTTPException) as exc:
            await _validate_group_assignment(session, district_id, group_id)

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_validate_group_assignment_accepts_matching_district() -> None:
    session = MagicMock()
    district_id = uuid.uuid4()
    group_id = uuid.uuid4()

    with patch("app.adapters.api.routers.districts.SqlCongregationGroupRepository") as repo_cls:
        repo = MagicMock()
        repo.get = AsyncMock(return_value=MagicMock(id=group_id, district_id=district_id))
        repo_cls.return_value = repo

        await _validate_group_assignment(session, district_id, group_id)
