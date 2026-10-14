# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SqlAuditLogRepository maps domain values onto the PostgreSQL enums."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.db.orm_models.audit_log import AuditAction as OrmAction
from app.adapters.db.orm_models.audit_log import AuditStatus as OrmStatus
from app.adapters.db.repositories.audit_log import SqlAuditLogRepository, _as_uuid
from app.domain.models.audit_log import AuditAction, AuditLogCreate, AuditStatus


def _repo() -> tuple[SqlAuditLogRepository, MagicMock]:
    session = MagicMock()
    session.flush = AsyncMock()
    return SqlAuditLogRepository(session), session


@pytest.mark.parametrize(
    "status, stored",
    [
        (AuditStatus.SUCCESS, OrmStatus.SUCCESS),
        (AuditStatus.FAILED, OrmStatus.FAILED),
        (None, OrmStatus.SUCCESS),
    ],
)
async def test_domain_status_is_stored_as_database_enum(status, stored) -> None:
    # Domain values are lower case ("failed"); the database enum only knows "FAILED".
    repo, session = _repo()

    created = await repo.create(
        AuditLogCreate(action=AuditAction.ACCESS_DENIED, resource_type="districts", status=status)
    )

    orm_row = session.add.call_args.args[0]
    assert orm_row.status is stored
    assert orm_row.action is OrmAction.ACCESS_DENIED
    assert created.status is AuditStatus[stored.name]
    assert created.action is AuditAction.ACCESS_DENIED


async def test_tenant_ids_from_path_parameters_are_converted() -> None:
    repo, session = _repo()
    district = uuid.uuid4()

    await repo.create(
        AuditLogCreate(
            action=AuditAction.UPDATE,
            resource_type="leaders",
            district_id=str(district),
            congregation_id="not-a-uuid",
        )
    )

    orm_row = session.add.call_args.args[0]
    assert orm_row.district_id == district
    assert orm_row.congregation_id is None


def test_as_uuid_passes_through_uuid_and_none() -> None:
    value = uuid.uuid4()
    assert _as_uuid(value) is value
    assert _as_uuid(None) is None
