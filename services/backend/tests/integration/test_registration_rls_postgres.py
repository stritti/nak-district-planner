# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Public registration under row-level security, anonymous and with the registrant's token.

Found in the manual acceptance of the Keycloak onboarding: a logged-in registrant's insert
violated the ``leader_registrations`` policy (HTTP 500), because the transaction began
(district lookup) before the token was read and carried no user. Skipped unless
``RLS_TEST_DATABASE_URL`` and ``RLS_TEST_APP_PASSWORD`` are configured.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.adapters.api.routers import registrations as router
from app.adapters.api.schemas.registration import RegistrationCreate
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.leader_registration import SqlLeaderRegistrationRepository
from app.adapters.db.session import AuditedSession, _set_tenant_gucs
from app.tenant import TenantContext

OWNER_DSN = os.getenv("RLS_TEST_DATABASE_URL")
APP_PASSWORD = os.getenv("RLS_TEST_APP_PASSWORD")
APP_ROLE = os.getenv("APP_DB_USER", "nak_app")

pytestmark = pytest.mark.skipif(
    not (OWNER_DSN and APP_PASSWORD),
    reason="RLS_TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
)


def _url(**overrides):
    return make_url(OWNER_DSN).set(drivername="postgresql+asyncpg", **overrides)


@pytest.fixture
async def owner() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_url())
    yield engine
    await engine.dispose()


@pytest.fixture
async def app_sessions() -> AsyncIterator[async_sessionmaker]:
    engine = create_async_engine(_url(username=APP_ROLE, password=APP_PASSWORD))
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    yield async_sessionmaker(engine, expire_on_commit=False, sync_session_class=AuditedSession)
    await engine.dispose()


@pytest.fixture
async def district(owner: AsyncEngine) -> AsyncIterator[uuid.UUID]:
    district_id = uuid.uuid4()
    async with owner.begin() as conn:
        await conn.execute(
            text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:i, :n, now(), now())"),
            {"i": district_id, "n": f"Reg {district_id.hex[:8]}"},
        )
    yield district_id
    async with owner.begin() as conn:
        await conn.execute(text("DELETE FROM leader_registrations WHERE district_id = :i"), {"i": district_id})
        await conn.execute(text("DELETE FROM districts WHERE id = :i"), {"i": district_id})


async def _submit(app_sessions, district_id, email, *, claims=None):
    """Call the route like the framework does: anonymous context, one session, optional token."""
    TenantContext.clear_context()
    adapter = AsyncMock()
    adapter.validate_token.return_value = claims or {}
    request = SimpleNamespace(state=SimpleNamespace())
    async with app_sessions() as session:
        with patch.object(router.api_deps, "get_oidc_adapter", return_value=adapter):
            response = await router.submit_registration(
                district_id,
                RegistrationCreate(name="Erika Beispiel", email=email),
                session,
                request=request,
                credentials=type("Cred", (), {"credentials": "t"})() if claims else None,
                district_repo=SqlDistrictRepository(session),
                reg_repo=SqlLeaderRegistrationRepository(session),
            )
        await session.commit()
    return response, request


async def test_an_anonymous_registration_is_accepted(app_sessions, district) -> None:
    response, _ = await _submit(app_sessions, district, "anon@example.org")

    assert response.user_sub is None and response.status.value == "PENDING"


async def test_a_logged_in_registration_is_bound_to_the_token_subject(app_sessions, district) -> None:
    response, request = await _submit(app_sessions, district, "erika@example.org", claims={"sub": "oidc|erika", "email": "erika@example.org", "email_verified": True})

    assert response.user_sub == "oidc|erika"
    assert request.state.user.sub == "oidc|erika"

@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "oidc|wrong", "email": "wrong@example.org", "email_verified": True},
        {"sub": "oidc|wrong", "email": "erika@example.org", "email_verified": False},
        {"sub": "oidc|wrong", "email": "erika@example.org", "email_verified": "true"},
        {"sub": "oidc|wrong", "email_verified": True},
    ],
)
async def test_unverified_or_mismatched_registrant_creates_no_row(
    app_sessions, district, owner, claims
) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await _submit(app_sessions, district, "erika@example.org", claims=claims)

    assert exc.value.status_code == 403
    async with owner.connect() as conn:
        count = await conn.scalar(
            text("SELECT count(*) FROM leader_registrations WHERE district_id = :id"),
            {"id": district},
        )
    assert count == 0
