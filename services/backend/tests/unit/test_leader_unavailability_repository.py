from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.db.orm_models.leader_unavailability import LeaderUnavailabilityORM
from app.adapters.db.repositories.leader_unavailability import (
    SqlLeaderUnavailabilityRepository,
)
from app.domain.models.leader_unavailability import UnavailabilityReason


class _Result:
    def __init__(self, rows: list[LeaderUnavailabilityORM]) -> None:
        self._rows = rows

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[LeaderUnavailabilityORM]:
        return self._rows


class _Session:
    def __init__(self, rows: list[LeaderUnavailabilityORM]) -> None:
        self.rows = rows
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _Result(self.rows)


@pytest.mark.asyncio
async def test_list_overlapping_maps_rows_and_scopes_by_leader() -> None:
    leader_id = uuid.uuid4()
    start_at = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
    row = LeaderUnavailabilityORM(
        id=uuid.uuid4(),
        leader_id=leader_id,
        start_at=start_at,
        end_at=start_at + timedelta(hours=2),
        reason=UnavailabilityReason.VACATION.value,
        note="Urlaub",
        created_at=start_at,
        updated_at=start_at,
    )
    session = _Session([row])
    repository = SqlLeaderUnavailabilityRepository(session)

    result = await repository.list_overlapping(
        leader_id=leader_id,
        start_at=start_at + timedelta(hours=1),
        end_at=start_at + timedelta(hours=3),
    )

    assert result[0].id == row.id
    assert result[0].reason is UnavailabilityReason.VACATION
    assert "leader_unavailabilities.leader_id" in str(session.statement)
    assert "leader_unavailabilities.start_at" in str(session.statement)
