# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Transaction-scoped PostgreSQL advisory locks."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def advisory_lock_key(value: UUID) -> int:
    """Convert UUID to the signed bigint accepted by PostgreSQL advisory locks."""
    return int.from_bytes(value.bytes[:8], "big", signed=True)


async def acquire_advisory_xact_lock(session: AsyncSession, value: UUID) -> None:
    """Lock a stable identifier until the current transaction commits or rolls back."""
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": advisory_lock_key(value)})


async def acquire_account_xact_lock(session: AsyncSession, user_sub: str) -> None:
    """Lock a person's account (OIDC ``sub``) until the current transaction ends.

    Duties booked by account and services of the leader linked to that account
    both take it, so their conflict checks cannot pass concurrently.
    """
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:sub, 0))"), {"sub": user_sub}
    )
