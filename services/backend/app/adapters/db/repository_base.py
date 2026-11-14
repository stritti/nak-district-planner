# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Shared skeleton for SQLAlchemy repository adapters."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ORMT = TypeVar("ORMT")
DomainT = TypeVar("DomainT")


class SqlRepository[ORMT, DomainT]:
    """Get/upsert skeleton shared by the SQL repositories.

    Subclasses declare ``orm_type`` and ``_fields`` (ORM column -> domain
    attribute) and inherit ``save``: fetch by id, create and add when missing,
    copy the mapped fields (enum members unwrapped to their value, so String
    and ``sa.Enum`` columns both accept them), then flush. Repositories with
    extra write semantics (insert-only, invariants, locking) override ``save``.
    """

    orm_type: type[ORMT]
    _fields: ClassVar[dict[str, str]] = {}

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entity: DomainT) -> None:
        row = await self._session.get(self.orm_type, entity.id)
        if row is None:
            row = self.orm_type()
            self._session.add(row)
        for orm_field, attr in self._fields.items():
            value: Any = getattr(entity, attr)
            if isinstance(value, Enum):
                value = value.value
            setattr(row, orm_field, value)
        await self._session.flush()
