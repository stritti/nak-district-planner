# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/db/repositories/export_token.py: Module."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.export_token import ExportTokenORM
from app.domain.models.export_token import (
    ExportToken,
    TokenType,
    hash_export_token,
    is_hashed_export_token,
)


def _orm_to_domain(row: ExportTokenORM) -> ExportToken:
    return ExportToken(
        id=row.id,
        token=row.token,
        label=row.label,
        token_type=TokenType(row.token_type),
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        leader_id=row.leader_id,
        created_at=row.created_at,
        subject_sub=row.subject_sub,
    )


class SqlExportTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, token: ExportToken) -> ExportToken:
        row = ExportTokenORM(
            id=token.id,
            token=token.token,
            label=token.label,
            token_type=token.token_type,
            district_id=token.district_id,
            congregation_id=token.congregation_id,
            leader_id=token.leader_id,
            created_at=token.created_at,
            subject_sub=token.subject_sub,
        )
        self._session.add(row)
        await self._session.flush()
        return token

    async def get_by_token(self, token: str) -> ExportToken | None:
        result = await self._session.execute(
            select(ExportTokenORM).where(ExportTokenORM.token == hash_export_token(token))
        )
        row = result.scalar_one_or_none()
        if row is None:
            result = await self._session.execute(
                select(ExportTokenORM).where(ExportTokenORM.token == token)
            )
            row = result.scalar_one_or_none()
            if row is not None and is_hashed_export_token(row.token):
                row = None
        return _orm_to_domain(row) if row else None

    async def get_orm(self, token_id: uuid.UUID) -> ExportTokenORM | None:
        result = await self._session.execute(
            select(ExportTokenORM).where(ExportTokenORM.id == token_id)
        )
        return result.scalar_one_or_none()

    async def hash_stored_token(self, row: ExportTokenORM) -> None:
        """Replace a legacy plaintext token value with its hash in place."""
        row.token = hash_export_token(row.token)
        await self._session.flush()

    async def get(self, token_id: uuid.UUID) -> ExportToken | None:
        result = await self._session.execute(
            select(ExportTokenORM).where(ExportTokenORM.id == token_id)
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list_by_district(self, district_id: uuid.UUID) -> list[ExportToken]:
        result = await self._session.execute(
            select(ExportTokenORM)
            .where(ExportTokenORM.district_id == district_id)
            .order_by(ExportTokenORM.created_at.desc())
        )
        return [_orm_to_domain(row) for row in result.scalars()]

    async def list_all(self) -> list[ExportToken]:
        result = await self._session.execute(
            select(ExportTokenORM).order_by(ExportTokenORM.created_at.desc())
        )
        return [_orm_to_domain(row) for row in result.scalars()]

    async def delete(self, token_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(ExportTokenORM).where(ExportTokenORM.id == token_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True
