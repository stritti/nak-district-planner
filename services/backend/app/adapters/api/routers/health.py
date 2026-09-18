"""Health check endpoint for service and dependency availability."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.adapters.db.session import AsyncSessionLocal
from app.application.rate_limiter import rate_limiter
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
@router.get("/api/health", include_in_schema=False)
async def health() -> JSONResponse:
    """Return service health and dependency connectivity."""
    result: dict[str, str] = {
        "status": "ok",
        "db": "ok",
        "redis": "ok",
        "version": settings.app_version,
    }

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        result["db"] = "error"

    try:
        if rate_limiter._redis is None:
            raise RuntimeError("Redis is not connected")
        await rate_limiter._redis.ping()
    except Exception:
        result["redis"] = "error"

    if result["db"] != "ok" or result["redis"] != "ok":
        result["status"] = "degraded"
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=result)

    return JSONResponse(status_code=status.HTTP_200_OK, content=result)
