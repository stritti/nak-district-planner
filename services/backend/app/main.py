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
from app.adapters.api.routers import (
    auth,
    calendar_integrations,
    districts,
    events,
    export,
    invitations,
    leaders,
    registrations,
    service_assignments,
)
from app.adapters.auth.oidc import OIDCAdapter
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.event import SqlEventRepository
from app.adapters.db.session import AsyncSessionLocal, engine
from app.application.draft_service_generation import GenerateDraftServicesUseCase
from app.config import settings
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

    # Run migrations
    cfg = Config("alembic.ini")
    # env.py uses asyncio.run() internally — must run in a thread without an active loop
    await asyncio.to_thread(command.upgrade, cfg, "head")

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

    if settings.startup_generate_draft_services:
        logger = logging.getLogger(__name__)

        async with AsyncSessionLocal() as session:
            use_case = GenerateDraftServicesUseCase(
                district_repo=SqlDistrictRepository(session),
                congregation_repo=SqlCongregationRepository(session),
                event_repo=SqlEventRepository(session),
            )
            result = await use_case.run()
            await session.commit()

        logger.info(
            "startup draft generation: districts=%d congregations=%d created=%d "
            "skipped_existing=%d adopted_existing=%d invalid_configurations=%d",
            result["districts"],
            result["congregations"],
            result["created"],
            result["skipped_existing"],
            result["adopted_existing"],
            result["invalid_configurations"],
        )

    yield

    # Cleanup
    await oidc_adapter.close()


app = FastAPI(
    title="NAK District Planner",
    description="Bezirksplanung für die Neuapostolische Kirche",
    version="0.1.0",
    lifespan=lifespan,
)

setup_telemetry(fastapi_app=app, sqlalchemy_engine=engine)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    detail = str(exc) if settings.app_env == "development" else "Internal Server Error"
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


# Register routers
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(invitations.router)
app.include_router(service_assignments.router)
app.include_router(calendar_integrations.router)
app.include_router(districts.router)
app.include_router(leaders.router)
app.include_router(registrations.public_router)
app.include_router(registrations.overview_router)
app.include_router(registrations.router)
app.include_router(export.router, prefix="/api/v1")
