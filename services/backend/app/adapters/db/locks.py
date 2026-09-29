"""PostgreSQL advisory-lock helpers."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def advisory_lock_key(value: UUID) -> int:
    """Derive a signed 64-bit advisory-lock key from a UUID.

    PostgreSQL advisory locks accept bigint keys. UUIDs are 128 bit, so this
    intentionally uses the first 64 bits. A collision is theoretically possible
    but sufficiently unlikely for transaction-scoped serialization here.
    """
    return int.from_bytes(value.bytes[:8], "big", signed=True)


async def acquire_advisory_xact_lock(session: AsyncSession, value: UUID) -> None:
    """Acquire a transaction-scoped advisory lock for *value*."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": advisory_lock_key(value)},
    )
