"""OpenTelemetry setup for the NAK District Planner backend.

Initialises tracing and metrics providers with OTLP/HTTP exporters when
telemetry is enabled.  HTTPX and Celery are instrumented automatically, while
FastAPI and SQLAlchemy are only instrumented when the corresponding objects are
passed to ``setup_telemetry()``.  All instrumentation is skipped when
``settings.otel_enabled`` is ``False`` or when non-default tracer/meter
providers are already registered (idempotency guard).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.metrics._internal import _ProxyMeterProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import ProxyTracerProvider

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

    # Idempotency: configure tracing and metrics independently.  A deployment
    # may preconfigure one signal while leaving the other on its proxy/default
    # provider; the missing signal still needs setup.
    tracing_initialized = not isinstance(trace.get_tracer_provider(), ProxyTracerProvider)
    metrics_initialized = not isinstance(metrics.get_meter_provider(), _ProxyMeterProvider)
    if tracing_initialized and metrics_initialized:
        logger.debug("OpenTelemetry tracing and metrics already initialized; skipping.")
        return

    otel_base_endpoint = settings.otel_endpoint.rstrip("/")
    resource = Resource.create({SERVICE_NAME: settings.otel_service_name})

    if not tracing_initialized:
        exporter = OTLPSpanExporter(endpoint=f"{otel_base_endpoint}/v1/traces")
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

    if not metrics_initialized:
        metric_exporter = OTLPMetricExporter(endpoint=f"{otel_base_endpoint}/v1/metrics")
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

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
        otel_base_endpoint,
    )
