import sys
import traceback
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.adapters.api.routers import (
    calendar_integrations,
    districts,
    events,
    export,
    service_assignments,
)
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    cfg = Config("alembic.ini")
    # env.py uses asyncio.run() internally — must run in a thread without an active loop
    await asyncio.to_thread(command.upgrade, cfg, "head")
    yield


app = FastAPI(
    title="NAK District Planner",
    description="Bezirksplanung für die Neuapostolische Kirche",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    detail = str(exc) if settings.app_env == "development" else "Internal Server Error"
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(events.router)
app.include_router(service_assignments.router)
app.include_router(calendar_integrations.router)
app.include_router(districts.router)
app.include_router(export.router, prefix="/api/v1")
