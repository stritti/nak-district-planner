"""app/main.py: Module."""

import logging
import sys
import traceback
from contextlib import asynccontextmanager

import httpx
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from alembic import command
from app.adapters.api import deps
from app.adapters.api.middleware.audit import AuditMiddleware
from app.adapters.api.middleware.csrf import CSRFMiddleware
from app.adapters.api.middleware.rate_limit import RateLimitMiddleware
from app.adapters.api.middleware.tenant import TenantMiddleware, TenantValidationMiddleware
from app.adapters.api.routers import (
    auth,
    calendar_integrations,
    districts,
    events_compat,
    export,
    invitations,
    leaders,
    notifications,
    planning_series,
    registrations,
    service_assignments,
    system,
)
from app.adapters.auth.oidc import OIDCAdapter
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.session import AsyncSessionLocal, engine
from app.application.audit_service import audit_service
from app.application.csrf import CSRFTokenService
from app.application.draft_service_generation import GenerateDraftServicesUseCase
from app.application.rate_limiter import RateLimitConfig, rate_limiter
from app.config import production_guard, settings
from app.telemetry import setup_telemetry


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    configure_logging()

    # Production guard — fail fast on unsafe config
    try:
        production_guard(settings)
    except RuntimeError as e:
        print("🚨", str(e))
        sys.exit(1)

    # Run migrations
    cfg = Config("alembic.ini")
    # env.py uses asyncio.run() internally — must run in a thread without an active loop
    await asyncio.to_thread(command.upgrade, cfg, "head")

    # Start audit service
    await audit_service.start()

    # Initialize OIDC adapter
    httpx_client = httpx.AsyncClient()
    oidc_adapter = OIDCAdapter(
        discovery_url=settings.oidc_discovery_url,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        issuer=settings.oidc_issuer,
        audience=settings.oidc_audience,
        httpx_client=httpx_client,
    )

    # Perform OIDC discovery early to ensure provider is reachable
    try:
        await oidc_adapter.discover()
        print(f"✓ OIDC discovery successful: {oidc_adapter.issuer}")
    except Exception as e:
        print(f"⚠ OIDC discovery failed: {e}")
        # Continue anyway, it might work at runtime

    # Set global OIDC adapter for use in dependencies
    deps.set_oidc_adapter(oidc_adapter)

    # Start rate limiter — fail-open: if Redis is unavailable, requests proceed without
    # rate limiting until Redis comes back (check_rate_limit already returns allowed=True on error).
    try:
        await rate_limiter.connect()
        logger = logging.getLogger(__name__)
        logger.info("Rate limiter connected to Redis")
    except Exception:
        logger = logging.getLogger(__name__)
        logger.warning(
            "Rate limiter could not connect to Redis — requests will not be rate limited "
            "until Redis becomes available"
        )

    yield

    # Cleanup
    await oidc_adapter.close()
    await audit_service.stop()
    try:
        await rate_limiter.close()
    except Exception:
        pass  # Shutting down — Redis connection may already be gone, safe to ignore


app = FastAPI(
    title="NAK District Planner",
    description="Bezirksplanung für die Neuapostolische Kirche",
    version="0.1.0",
    lifespan=lifespan,
)

setup_telemetry(fastapi_app=app, sqlalchemy_engine=engine)

# Initialize Rate Limiting
rate_limit_config = RateLimitConfig(
    default_limit=200,
    default_window_seconds=60,
    authenticated_multiplier=2.0,
    burst_limit=10,
    burst_window_seconds=1,
    endpoint_limits={
        "/api/health": {"limit": 60, "window": 60},
        "/api/v1/auth/oidc/discovery": {"limit": 100, "window": 60},
        "/api/v1/auth/oidc/token": {"limit": 100, "window": 60},
        "/api/v1/export/*": {"limit": 60, "window": 60},
        "/api/v1/events": {"limit": 100, "window": 60},
    },
)
app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=rate_limiter,
    config=rate_limit_config,
    exempt_paths={"/api/health"},
    exempt_methods={"OPTIONS"},
)

# Initialize Tenant Isolation
# NOTE: registration order matters — Starlette runs the LAST-added middleware
# first (outermost). TenantMiddleware must run BEFORE TenantValidationMiddleware
# so that tenant context (incl. user_sub) is already extracted when validation runs.
app.add_middleware(
    TenantValidationMiddleware,
    exempt_paths={"/api/health", "/api/v1/auth"},
    exempt_methods={"OPTIONS"},
)
app.add_middleware(
    TenantMiddleware,
    exempt_paths={"/api/health", "/api/v1/auth"},
    exempt_methods={"OPTIONS"},
)

# Initialize CSRF protection
csrf_service = CSRFTokenService()
app.add_middleware(
    CSRFMiddleware,
    csrf_service=csrf_service,
    cookie_name="csrf_token",
    header_name="X-CSRF-Token",
    exempt_paths={
        "/api/health",
        "/api/v1/auth/oidc/discovery",
        "/api/v1/auth/oidc/token",
    },
    exempt_methods={"GET", "HEAD", "OPTIONS"},
)

# Initialize Audit Logging (registered last = outermost, catches all requests
# including those that fail CSRF or other inner middleware)
app.add_middleware(
    AuditMiddleware,
    audit_service=audit_service,
    exempt_paths={"/api/health"},
    exempt_methods={"GET", "HEAD", "OPTIONS"},
)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    detail = str(exc) if settings.app_env == "development" else "Internal Server Error"
    return JSONResponse(status_code=500, content={"detail": detail})


@app.api_route("/api/health", methods=["GET", "HEAD", "OPTIONS"])
async def health() -> dict:
    """Health check endpoint.

    Returns basic health status including optional database connectivity.
    The endpoint always returns ``status: ok`` as long as the app responds,
    making it safe for Docker Compose healthchecks.
    """
    result: dict = {"status": "ok", "version": settings.app_version}

    # Check database connectivity (informational — does not affect health status)
    try:
        from sqlalchemy import text as sa_text

        async with AsyncSessionLocal() as session:
            await session.execute(sa_text("SELECT 1"))
        result["database"] = "ok"
    except Exception:
        result["database"] = "unavailable"

    return result


# Register routers
app.include_router(auth.router)
app.include_router(events_compat.router)
app.include_router(invitations.router)
app.include_router(service_assignments.router)
app.include_router(calendar_integrations.router)
app.include_router(districts.router)
app.include_router(leaders.router)
app.include_router(planning_series.router)
app.include_router(registrations.public_router)
app.include_router(registrations.overview_router)
app.include_router(registrations.router)
app.include_router(export.router, prefix="/api/v1")
app.include_router(system.router)
app.include_router(notifications.router)
