"""Health check endpoint for service and dependency availability."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.adapters.db.session import AsyncSessionLocal
from app.application.rate_limiter import rate_limiter
from app.config import settings

router = APIRouter(tags=["health"])


@router.api_route(
    "/health", methods=["GET", "HEAD", "OPTIONS"], include_in_schema=False
)
@router.api_route(
    "/api/health", methods=["GET", "HEAD", "OPTIONS"], include_in_schema=False
)
async def health(request: Request) -> JSONResponse:
    """Return service health and dependency connectivity."""
    response = await _build_health_response(AsyncSessionLocal)
    if request.url.path == "/api/health":
        payload = json.loads(response.body)
        payload["database"] = "ok" if payload["db"] == "ok" else "unavailable"
        payload["redis"] = payload.pop("_legacy_redis", "unavailable")
        payload.pop("db")
        return JSONResponse(status_code=response.status_code, content=payload)
    payload = json.loads(response.body)
    payload.pop("_legacy_redis", None)
    return JSONResponse(status_code=response.status_code, content=payload)


async def _build_health_response(session_factory: Callable[[], Any]) -> JSONResponse:
    """Build a health response with an injectable database session factory."""
    result: dict[str, str] = {
        "status": "ok",
        "db": "ok",
        "redis": "ok",
        "version": settings.app_version,
    }

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        result["db"] = "error"

    try:
        if rate_limiter._redis is None:
            result["_legacy_redis"] = "disconnected"
            raise RuntimeError("Redis is not connected")
        await rate_limiter._redis.ping()
    except Exception:
        result.setdefault("_legacy_redis", "unavailable")
        result["redis"] = "error"

    if result["db"] != "ok" or result["redis"] != "ok":
        result["status"] = "degraded"
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=result)

    return JSONResponse(status_code=status.HTTP_200_OK, content=result)
