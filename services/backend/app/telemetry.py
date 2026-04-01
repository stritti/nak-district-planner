"""OpenTelemetry setup for the NAK District Planner backend.

Initialises a TracerProvider with an OTLP/HTTP exporter and automatically
instruments FastAPI, SQLAlchemy, HTTPX, and Celery when telemetry is enabled.
All instrumentation is skipped when ``settings.otel_enabled`` is ``False``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import settings

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def setup_telemetry(
    fastapi_app: FastAPI | None = None, sqlalchemy_engine: Any | None = None
) -> None:
    """Configure and start OpenTelemetry tracing.

    Args:
        fastapi_app: The FastAPI application instance to instrument.
            When *None*, FastAPI instrumentation is skipped.
        sqlalchemy_engine: An async SQLAlchemy engine to instrument.
            When *None*, SQLAlchemy instrumentation is skipped.
    """
    if not settings.otel_enabled:
        logger.debug("OpenTelemetry is disabled (OTEL_ENABLED=false).")
        return

    resource = Resource.create({SERVICE_NAME: settings.otel_service_name})

    exporter = OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces")
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if fastapi_app is not None:
        FastAPIInstrumentor.instrument_app(fastapi_app)
        logger.info("OpenTelemetry: FastAPI instrumented.")

    if sqlalchemy_engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine.sync_engine)
        logger.info("OpenTelemetry: SQLAlchemy instrumented.")

    HTTPXClientInstrumentor().instrument()
    logger.info("OpenTelemetry: HTTPX instrumented.")

    CeleryInstrumentor().instrument()
    logger.info("OpenTelemetry: Celery instrumented.")

    logger.info(
        "OpenTelemetry tracing active — service=%s endpoint=%s",
        settings.otel_service_name,
        settings.otel_endpoint,
    )
