"""Monitoring signal for denied requests (tenant isolation and RBAC).

A rising rate of HTTP 403 responses, especially for one route, indicates
cross-tenant probing or a broken role assignment. The counter is a no-op while
OpenTelemetry is disabled and is exported with the other metrics otherwise.

Attributes are bounded on purpose: the route template instead of the concrete
path, never user or tenant identifiers (cardinality and personal data).
"""

from __future__ import annotations

import re

from opentelemetry import metrics
from starlette.requests import Request

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

_meter = metrics.get_meter("nak.security")
access_denied = _meter.create_counter(
    "nak.access.denied",
    unit="{request}",
    description="Requests rejected with HTTP 403 by tenant validation or role checks",
)


def route_template(request: Request) -> str:
    """Route pattern of the request; UUIDs masked when routing did not run.

    Tenant validation rejects requests before the router matches them, so the
    concrete path is normalised instead.
    """
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if template:
        return template
    return _UUID.sub("{id}", request.url.path)


def record_access_denied(request: Request) -> None:
    access_denied.add(
        1,
        {"http.request.method": request.method, "http.route": route_template(request)},
    )
