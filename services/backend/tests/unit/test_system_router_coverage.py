# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""System version endpoint: real role guards, caching and fail-closed behavior."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import system
from app.adapters.version_check.cache import VersionCache
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


def _auth(
    *, role: Role | None = Role.DISTRICT_ADMIN,
    superadmin: bool = False,
    scope: ScopeType = ScopeType.DISTRICT,
) -> SimpleNamespace:
    memberships = []
    if role is not None:
        memberships.append(
            Membership.create(
                user_sub="operator", role=role,
                scope_type=scope, scope_id=uuid.uuid4(),
            )
        )
    return SimpleNamespace(
        user_sub="operator",
        user=SimpleNamespace(is_superadmin=superadmin),
        memberships=memberships,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [None, Role.VIEWER, Role.PLANNER])
@pytest.mark.parametrize("scope", [ScopeType.DISTRICT, ScopeType.CONGREGATION])
async def test_non_admin_cannot_probe_versions(role: Role | None, scope: ScopeType) -> None:
    with patch.object(system.GhcrTagFetcher, "fetch_tags") as fetch:
        with pytest.raises(HTTPException) as error:
            await system.get_version(_auth(role=role, scope=scope), refresh=True)
    assert error.value.status_code == 403
    fetch.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "scope"),
    [
        (Role.DISTRICT_ADMIN, ScopeType.DISTRICT),
        (Role.CONGREGATION_ADMIN, ScopeType.DISTRICT),
        (Role.CONGREGATION_ADMIN, ScopeType.CONGREGATION),
    ],
)
async def test_district_admin_roles_may_fetch_versions(
    monkeypatch: pytest.MonkeyPatch, role: Role, scope: ScopeType
) -> None:
    cache = VersionCache(ttl_seconds=3600)
    monkeypatch.setattr(system, "version_cache", cache)
    with patch.object(
        system.GhcrTagFetcher, "fetch_tags",
        return_value=["latest", "1.0.0", "1.0.1"],
    ) as fetch:
        out = await system.get_version(_auth(role=role, scope=scope), refresh=False)

    assert out.latest_version == "1.0.1"
    assert out.release_url.endswith("/releases/tag/v1.0.1")
    assert out.last_checked is not None
    assert out.update_available == system.is_newer("1.0.1", out.current_version)
    fetch.assert_called_once_with("backend")


@pytest.mark.asyncio
async def test_superadmin_can_fetch_without_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(system, "version_cache", VersionCache())
    with patch.object(
        system.GhcrTagFetcher, "fetch_tags", return_value=["1.0.0"]
    ):
        out = await system.get_version(_auth(role=None, superadmin=True), refresh=False)
    assert out.latest_version == "1.0.0"


@pytest.mark.asyncio
async def test_cached_version_avoids_repeated_network_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = VersionCache(ttl_seconds=3600)
    cache.set("1.0.1")
    monkeypatch.setattr(system, "version_cache", cache)

    with patch.object(system.GhcrTagFetcher, "fetch_tags") as fetch:
        out = await system.get_version(_auth(), refresh=False)

    fetch.assert_not_called()
    assert out.latest_version == "1.0.1"


@pytest.mark.asyncio
async def test_forced_refresh_replaces_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = VersionCache()
    cache.set("1.0.1")
    monkeypatch.setattr(system, "version_cache", cache)
    with patch.object(
        system.GhcrTagFetcher, "fetch_tags", return_value=["1.0.2"]
    ) as fetch:
        out = await system.get_version(_auth(), refresh=True)

    fetch.assert_called_once_with("backend")
    assert out.latest_version == "1.0.2"
    assert cache.get() == "1.0.2"


@pytest.mark.asyncio
async def test_provider_exception_returns_existing_cached_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = VersionCache()
    cache.set("1.0.1")
    monkeypatch.setattr(system, "version_cache", cache)
    with patch.object(
        system.GhcrTagFetcher, "fetch_tags",
        side_effect=RuntimeError("GHCR unavailable"),
    ):
        out = await system.get_version(_auth(), refresh=True)
    assert out.latest_version == "1.0.1"
    assert cache.get() == "1.0.1"


@pytest.mark.asyncio
async def test_provider_exception_without_cache_reports_no_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = VersionCache()
    monkeypatch.setattr(system, "version_cache", cache)
    with patch.object(
        system.GhcrTagFetcher, "fetch_tags",
        side_effect=RuntimeError("GHCR unavailable"),
    ):
        out = await system.get_version(_auth(), refresh=False)
    assert out.latest_version is None
    assert out.release_url is None
    assert out.update_available is False


@pytest.mark.asyncio
async def test_no_semver_tags_returns_no_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(system, "version_cache", VersionCache())
    with patch.object(
        system.GhcrTagFetcher, "fetch_tags", return_value=["latest", "sha-1234567"]
    ):
        out = await system.get_version(_auth(), refresh=False)

    assert out.latest_version is None
    assert out.update_available is False
    assert out.release_url is None
