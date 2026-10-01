"""Monitoring counter for denied requests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.adapters.api import access_metrics
from app.adapters.api.access_metrics import record_access_denied, route_template


def _request(path: str, route=None, method: str = "GET") -> MagicMock:
    request = MagicMock()
    request.method = method
    request.url.path = path
    request.scope = {"route": route} if route is not None else {}
    return request


def test_route_template_prefers_the_matched_route() -> None:
    route = SimpleNamespace(path="/api/v1/districts/{district_id}/matrix")
    request = _request("/api/v1/districts/0b4f/matrix", route)
    assert route_template(request) == "/api/v1/districts/{district_id}/matrix"


def test_route_template_masks_uuids_when_routing_did_not_run() -> None:
    path = (
        "/api/v1/districts/3f2b8c1e-8a4d-4c2b-9f7e-1a2b3c4d5e6f"
        "/congregations/AABBCCDD-1111-2222-3333-444455556666"
    )
    assert route_template(_request(path)) == "/api/v1/districts/{id}/congregations/{id}"


def test_record_uses_bounded_attributes_only() -> None:
    counter = MagicMock()
    route = SimpleNamespace(path="/api/v1/events/{event_id}")
    with patch.object(access_metrics, "access_denied", counter):
        record_access_denied(_request("/api/v1/events/abc", route, method="PATCH"))

    counter.add.assert_called_once_with(
        1, {"http.request.method": "PATCH", "http.route": "/api/v1/events/{event_id}"}
    )


def test_counter_is_safe_without_configured_provider() -> None:
    # OpenTelemetry disabled: the proxy counter must accept measurements silently.
    record_access_denied(_request("/api/v1/events"))
