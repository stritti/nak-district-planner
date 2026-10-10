# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Static inventory of API routes and their authentication/authorization guards.

Used by the permission-coverage test and the RBAC coverage report
(``scripts/rbac_coverage_report.py``) so that every endpoint is accounted for.

Authentication is derived from FastAPI's dependency graph: a route is
authenticated when ``get_current_user`` is reachable from its dependencies.

Authorization is derived from the handler source: the handler — and any
module-level helper it calls, transitively — must call one of the RBAC guard
functions from ``app.adapters.auth.permissions`` or check ``is_superadmin``.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import cache
from types import ModuleType
from typing import Any

from fastapi import APIRouter
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.adapters.api import deps
from app.adapters.api import routers as routers_package
from app.adapters.auth import permissions

GUARD_FUNCTIONS: frozenset[str] = frozenset(
    guard.__name__
    for guard in (
        permissions.require_role_in_district,
        permissions.require_superadmin,
        permissions.assert_has_role_in_district,
        permissions.assert_has_role_in_congregation,
        permissions.has_role_in_district,
        permissions.has_role_in_congregation,
        permissions.get_districts_where_user_has_role,
        permissions.get_congregations_where_user_has_role,
    )
)
SUPERADMIN_ATTRIBUTE = "is_superadmin"


@dataclass(frozen=True, slots=True)
class RouteInfo:
    """One HTTP operation exposed by a router module."""

    key: str
    """Stable identifier ``<router module>.<handler name>``."""
    name: str
    """Starlette route name, resolvable via ``app.url_path_for``."""
    methods: tuple[str, ...]
    path: str
    requires_authentication: bool
    guards: frozenset[str]
    """Guard functions (and ``is_superadmin``) reachable from the handler."""

    @property
    def has_role_guard(self) -> bool:
        return bool(self.guards)


def iter_router_modules(package: ModuleType = routers_package) -> Iterator[ModuleType]:
    for module_info in pkgutil.iter_modules(package.__path__):
        yield importlib.import_module(f"{package.__name__}.{module_info.name}")


def iter_routers(module: ModuleType) -> Iterator[APIRouter]:
    for value in vars(module).values():
        if isinstance(value, APIRouter):
            yield value


def collect_routes(package: ModuleType = routers_package) -> list[RouteInfo]:
    """Return every API route defined in the router package."""
    routes: list[RouteInfo] = []
    for module in iter_router_modules(package):
        module_name = module.__name__.rsplit(".", 1)[-1]
        for router in iter_routers(module):
            for route in router.routes:
                if isinstance(route, APIRoute):
                    routes.append(_describe(module_name, module, route))
    return sorted(routes, key=lambda route: (route.path, route.methods))


def _describe(module_name: str, module: ModuleType, route: APIRoute) -> RouteInfo:
    return RouteInfo(
        key=f"{module_name}.{route.endpoint.__name__}",
        name=route.name,
        methods=tuple(sorted(route.methods or ())),
        path=route.path,
        requires_authentication=deps.get_current_user in _dependency_calls(route.dependant),
        guards=_guards_reachable_from(module, route.endpoint.__name__),
    )


def _dependency_calls(dependant: Dependant) -> Iterator[Callable[..., Any]]:
    for dependency in dependant.dependencies:
        if dependency.call is not None:
            yield dependency.call
        yield from _dependency_calls(dependency)


def _guards_reachable_from(module: ModuleType, function_name: str) -> frozenset[str]:
    functions = _module_functions(module)
    found: set[str] = set()
    pending = [function_name]
    visited: set[str] = set()
    while pending:
        name = pending.pop()
        if name in visited or name not in functions:
            continue
        visited.add(name)
        for node in ast.walk(functions[name]):
            if isinstance(node, ast.Attribute) and node.attr == SUPERADMIN_ATTRIBUTE:
                found.add(SUPERADMIN_ATTRIBUTE)
            elif isinstance(node, ast.Call) and (called := _called_name(node)):
                if called in GUARD_FUNCTIONS:
                    found.add(called)
                else:
                    pending.append(called)
    return frozenset(found)


@cache
def _module_functions(module: ModuleType) -> dict[str, ast.AST]:
    tree = ast.parse(inspect.getsource(module))
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _called_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None
