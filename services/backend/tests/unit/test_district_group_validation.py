from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.adapters.api.routers.districts import _validate_group_assignment


@pytest.mark.asyncio
async def test_validate_group_assignment_accepts_none() -> None:
    await _validate_group_assignment(AsyncMock(), uuid.uuid4(), None)


@pytest.mark.asyncio
async def test_validate_group_assignment_rejects_cross_district() -> None:
    district_id = uuid.uuid4()
    group_id = uuid.uuid4()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=MagicMock(id=group_id, district_id=uuid.uuid4()))
    with pytest.raises(HTTPException) as exc:
        await _validate_group_assignment(repo, district_id, group_id)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_validate_group_assignment_accepts_matching_district() -> None:
    district_id = uuid.uuid4()
    group_id = uuid.uuid4()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=MagicMock(id=group_id, district_id=district_id))
    await _validate_group_assignment(repo, district_id, group_id)
