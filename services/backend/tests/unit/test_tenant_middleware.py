"""Unit tests for tenant routing context middleware."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.adapters.api.middleware.tenant import TenantMiddleware


def make_request(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_string: str = "",
) -> Request:
    raw_headers = [
        (name.lower().encode(), value.encode()) for name, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query_string.encode(),
            "headers": raw_headers,
            "client": ("203.0.113.10", 12345),
            "scheme": "https",
            "server": ("testserver", 443),
        }
    )


@pytest.fixture
def middleware() -> TenantMiddleware:
    return TenantMiddleware(MagicMock())


def test_extracts_district_and_congregation_from_path(middleware: TenantMiddleware) -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    context: dict = {}

    middleware._extract_tenant_from_path(
        f"/api/v1/districts/{district_id}/congregations/{congregation_id}", context
    )

    assert context == {
        "district_id": district_id,
        "congregation_id": congregation_id,
        "tenant_id": district_id,
        "tenant_type": "district",
    }


def test_path_extraction_requires_complete_uuid(middleware: TenantMiddleware) -> None:
    district_id = uuid.uuid4()
    context: dict = {}

    middleware._extract_tenant_from_path(f"/api/v1/districts/{district_id}suffix/leaders", context)

    assert context == {}


def test_invalid_header_uuid_is_ignored(middleware: TenantMiddleware) -> None:
    request = make_request("/api/v1/events", headers={"X-District-ID": "not-a-uuid"})

    context = middleware._extract_tenant_context(request)

    assert "district_id" not in context
    assert "tenant_id" not in context


def test_query_context_preserves_district_as_tenant(middleware: TenantMiddleware) -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    request = make_request(
        "/api/v1/events",
        query_string=f"district_id={district_id}&congregation_id={congregation_id}",
    )

    context = middleware._extract_tenant_context(request)

    assert context["district_id"] == district_id
    assert context["congregation_id"] == congregation_id
    assert context["tenant_id"] == district_id
    assert context["tenant_type"] == "district"


def test_forged_bearer_subject_is_never_interpreted_by_tenant_middleware(
    middleware: TenantMiddleware,
) -> None:
    district_id = uuid.uuid4()
    forged = "eyJhbGciOiJub25lIn0.eyJzdWIiOiJ2aWN0aW0ifQ."
    request = make_request(
        f"/api/v1/districts/{district_id}/leaders",
        headers={"Authorization": f"Bearer {forged}"},
    )

    context = middleware._extract_tenant_context(request)

    assert "user_sub" not in context
    assert middleware._verified_sub(request) is None


def test_verified_subject_is_read_only_from_request_state(middleware: TenantMiddleware) -> None:
    request = make_request("/api/v1/events")
    request.state.user = MagicMock(sub="verified-user", email="user@example.org")
    request.state.user_roles = ["PLANNER"]

    context = middleware._extract_tenant_context(request)

    assert middleware._verified_sub(request) == "verified-user"
    assert context["user_email"] == "user@example.org"
    assert context["user_roles"] == ["PLANNER"]


@pytest.mark.asyncio
async def test_dispatch_sets_and_always_clears_tenant_context(middleware: TenantMiddleware) -> None:
    district_id = uuid.uuid4()
    request = make_request(f"/api/v1/districts/{district_id}/leaders")
    call_next = AsyncMock(return_value=Response("ok"))

    with (
        patch("app.adapters.api.middleware.tenant.TenantContext.set_context") as set_context,
        patch("app.adapters.api.middleware.tenant.TenantContext.clear_context") as clear_context,
    ):
        response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert request.state.tenant_context["district_id"] == district_id
    set_context.assert_called_once()
    clear_context.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_clears_context_when_downstream_raises(middleware: TenantMiddleware) -> None:
    request = make_request(f"/api/v1/districts/{uuid.uuid4()}/leaders")
    call_next = AsyncMock(side_effect=RuntimeError("boom"))

    with (
        patch("app.adapters.api.middleware.tenant.TenantContext.set_context"),
        patch("app.adapters.api.middleware.tenant.TenantContext.clear_context") as clear_context,
        pytest.raises(RuntimeError, match="boom"),
    ):
        await middleware.dispatch(request, call_next)

    clear_context.assert_called_once()


@pytest.mark.asyncio
async def test_exempt_request_does_not_touch_context(middleware: TenantMiddleware) -> None:
    request = make_request("/api/health")
    call_next = AsyncMock(return_value=Response("ok"))

    with patch("app.adapters.api.middleware.tenant.TenantContext.set_context") as set_context:
        await middleware.dispatch(request, call_next)

    set_context.assert_not_called()
    call_next.assert_awaited_once_with(request)
