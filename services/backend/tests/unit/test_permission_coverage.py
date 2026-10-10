# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Automated RBAC coverage: every API route is authenticated and role-guarded.

Adding an endpoint without ``get_current_user`` in its dependency graph, or
without a guard from ``app.adapters.auth.permissions`` in its handler, fails
this test. Intentional exceptions must be listed below with a justification,
which keeps ``docs/rbac-coverage.md`` honest (see
``scripts/rbac_coverage_report.py``).
"""

from __future__ import annotations

import importlib.util
import re
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.adapters.api.route_inventory import GUARD_FUNCTIONS, RouteInfo, collect_routes
from app.adapters.auth.permissions import require_superadmin

# Endpoints reachable without a Bearer token. Keep this list short.
PUBLIC_ENDPOINTS: dict[str, str] = {
    "health.health": "Liveness/Readiness-Probe für Orchestrierung",
    "auth.get_oidc_discovery": "OIDC-Konfiguration wird vor dem Login benötigt",
    "auth.exchange_oidc_token": "Authorization-Code-Tausch und Refresh-Session benötigen keinen Access Token",
    "auth.revoke_oidc_refresh_token": "Logout muss auch mit abgelaufenem Access Token möglich bleiben; CSRF schützt den Cookie-POST",
    "export.export_calendar_ics": "Token-basierter ICS-Feed; das Export-Token ist das Geheimnis",
    "registrations.list_districts_public": "Bezirksauswahl im Selbstregistrierungsformular",
    "registrations.list_congregations_public": "Gemeindeauswahl im Selbstregistrierungsformular",
    "registrations.submit_registration": "Selbstregistrierung neuer Amtsträger (Freigabe durch Admin)",
}

# Authenticated endpoints that intentionally need no role in a specific scope.
AUTHENTICATED_WITHOUT_ROLE: dict[str, str] = {
    "districts.list_de_states": "Statische Liste der Bundesländer ohne Mandantenbezug",
}


@pytest.fixture(scope="module")
def routes() -> list[RouteInfo]:
    return collect_routes()


def _describe(routes: list[RouteInfo]) -> str:
    return "\n".join(f"  {','.join(r.methods)} {r.path} ({r.key})" for r in routes)


def test_inventory_discovers_all_router_modules(routes) -> None:
    modules = {route.key.split(".", 1)[0] for route in routes}
    assert {"auth", "districts", "events", "export", "notifications", "system"} <= modules
    assert len(routes) > 50


def test_every_route_is_mounted_in_the_application(routes) -> None:
    from app.main import app

    for route in routes:
        params = dict.fromkeys(re.findall(r"{(\w+)(?::\w+)?}", route.path), "x")
        assert app.url_path_for(route.name, **params), route.key


def test_every_non_public_route_requires_authentication(routes) -> None:
    unauthenticated = [
        route
        for route in routes
        if route.key not in PUBLIC_ENDPOINTS and not route.requires_authentication
    ]
    assert not unauthenticated, (
        "Routes without get_current_user dependency (add auth or document in "
        f"PUBLIC_ENDPOINTS):\n{_describe(unauthenticated)}"
    )


def test_public_allowlist_contains_only_public_routes(routes) -> None:
    by_key = {route.key: route for route in routes}
    stale = sorted(set(PUBLIC_ENDPOINTS) - set(by_key))
    now_authenticated = sorted(
        key for key in PUBLIC_ENDPOINTS if key in by_key and by_key[key].requires_authentication
    )
    assert not stale, f"PUBLIC_ENDPOINTS references unknown routes: {stale}"
    assert not now_authenticated, f"No longer public, remove from allowlist: {now_authenticated}"


def test_every_authenticated_route_has_a_role_guard(routes) -> None:
    unguarded = [
        route
        for route in routes
        if route.requires_authentication
        and not route.has_role_guard
        and route.key not in AUTHENTICATED_WITHOUT_ROLE
    ]
    assert not unguarded, (
        f"Authenticated routes without RBAC guard ({sorted(GUARD_FUNCTIONS)}); add a guard "
        f"or document in AUTHENTICATED_WITHOUT_ROLE:\n{_describe(unguarded)}"
    )


def test_role_exception_allowlist_is_not_stale(routes) -> None:
    by_key = {route.key: route for route in routes}
    stale = sorted(
        key for key in AUTHENTICATED_WITHOUT_ROLE if key not in by_key or by_key[key].has_role_guard
    )
    assert not stale, f"Remove from AUTHENTICATED_WITHOUT_ROLE: {stale}"


def test_route_keys_are_unique_per_method_and_path(routes) -> None:
    seen: dict[tuple[tuple[str, ...], str], str] = {}
    duplicates = []
    for route in routes:
        signature = (route.methods, route.path)
        if signature in seen:
            duplicates.append(f"{route.key} duplicates {seen[signature]}")
        seen[signature] = route.key
    assert not duplicates, duplicates


BACKEND_ROOT = Path(__file__).resolve().parents[2]
COVERAGE_DOC = BACKEND_ROOT.parents[1] / "docs" / "rbac-coverage.md"


@pytest.mark.skipif(not COVERAGE_DOC.exists(), reason="docs/ not available (container build)")
def test_generated_inventory_in_docs_is_up_to_date(routes) -> None:
    spec = importlib.util.spec_from_file_location(
        "rbac_coverage_report", BACKEND_ROOT / "scripts" / "rbac_coverage_report.py"
    )
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)

    match = re.search(
        r"<!-- rbac-inventory:start -->\n(.*?)\n<!-- rbac-inventory:end -->",
        COVERAGE_DOC.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert match, "Generated section markers missing in docs/rbac-coverage.md"
    assert match.group(1) == report.render(routes), (
        "docs/rbac-coverage.md is outdated; run `uv run python scripts/rbac_coverage_report.py`"
    )


class TestInventoryMechanics:
    """The analyser itself, exercised against a synthetic router package."""

    @pytest.fixture
    def synthetic_routes(self, tmp_path, monkeypatch) -> dict[str, RouteInfo]:
        package = tmp_path / "rbac_fixture_routers"
        package.mkdir()
        (package / "__init__.py").write_text("")
        (package / "sample.py").write_text(
            textwrap.dedent(
                """
                from fastapi import APIRouter

                from app.adapters.api.deps import CurrentUserWithMemberships
                from app.adapters.auth.permissions import (
                    require_role_in_district,
                    require_superadmin,
                )

                router = APIRouter(prefix="/sample")


                def _load_and_check(auth):
                    return _nested_check(auth)


                def _nested_check(auth):
                    require_role_in_district(auth, None, None)


                @router.get("/public")
                async def public():
                    return {}


                @router.get("/unguarded")
                async def unguarded(auth: CurrentUserWithMemberships):
                    return {}


                @router.get("/direct")
                async def direct(auth: CurrentUserWithMemberships):
                    require_superadmin(auth.user)


                @router.get("/transitive")
                async def transitive(auth: CurrentUserWithMemberships):
                    _load_and_check(auth)


                @router.get("/attribute")
                async def attribute(auth: CurrentUserWithMemberships):
                    return auth.user.is_superadmin                """
            )
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        import rbac_fixture_routers

        try:
            yield {route.key: route for route in collect_routes(rbac_fixture_routers)}
        finally:
            for name in [m for m in sys.modules if m.startswith("rbac_fixture_routers")]:
                del sys.modules[name]

    def test_unauthenticated_route_is_detected(self, synthetic_routes) -> None:
        route = synthetic_routes["sample.public"]
        assert not route.requires_authentication
        assert not route.has_role_guard
        assert route.path == "/sample/public"
        assert route.methods == ("GET",)

    def test_authenticated_route_without_guard_is_detected(self, synthetic_routes) -> None:
        route = synthetic_routes["sample.unguarded"]
        assert route.requires_authentication
        assert not route.has_role_guard

    def test_direct_guard_call(self, synthetic_routes) -> None:
        assert synthetic_routes["sample.direct"].guards == {"require_superadmin"}

    def test_guard_in_transitive_module_helper(self, synthetic_routes) -> None:
        assert synthetic_routes["sample.transitive"].guards == {"require_role_in_district"}

    def test_superadmin_attribute_check(self, synthetic_routes) -> None:
        assert synthetic_routes["sample.attribute"].guards == {"is_superadmin"}


class TestRequireSuperadmin:
    def test_superadmin_passes(self) -> None:
        require_superadmin(SimpleNamespace(is_superadmin=True))

    @pytest.mark.parametrize(
        "user",
        [
            SimpleNamespace(is_superadmin=False),
            SimpleNamespace(is_superadmin="true"),
            SimpleNamespace(is_superadmin=1),
            SimpleNamespace(),
            None,
        ],
        ids=["false", "truthy-string", "truthy-int", "missing-attribute", "none"],
    )
    def test_everything_else_is_rejected(self, user) -> None:
        with pytest.raises(HTTPException) as exc_info:
            require_superadmin(user, "nope")
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "nope"
