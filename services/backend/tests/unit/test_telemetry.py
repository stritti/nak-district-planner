"""Unit tests for app/telemetry.py.

All OTel SDK components are mocked so no real OTLP endpoint is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.telemetry import setup_telemetry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(*, otel_enabled: bool = True, endpoint: str = "http://otel:4318"):
    """Return a mock settings object."""
    s = MagicMock()
    s.otel_enabled = otel_enabled
    s.otel_service_name = "test-service"
    s.otel_endpoint = endpoint
    return s


# ---------------------------------------------------------------------------
# Tests: disabled path
# ---------------------------------------------------------------------------


class TestSetupTelemetryDisabled:
    def test_no_provider_when_disabled(self):
        """When otel_enabled=False no TracerProvider must be created."""
        mock_settings = _make_settings(otel_enabled=False)

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.TracerProvider") as mock_provider,
            patch("app.telemetry.trace.set_tracer_provider") as mock_set,
        ):
            setup_telemetry()

            mock_provider.assert_not_called()
            mock_set.assert_not_called()

    def test_no_instrumentors_when_disabled(self):
        """When otel_enabled=False none of the instrumentors must be called."""
        mock_settings = _make_settings(otel_enabled=False)

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.FastAPIInstrumentor") as mock_fastapi,
            patch("app.telemetry.SQLAlchemyInstrumentor") as mock_sqla,
            patch("app.telemetry.HTTPXClientInstrumentor") as mock_httpx,
            patch("app.telemetry.CeleryInstrumentor") as mock_celery,
        ):
            setup_telemetry()

            mock_fastapi.instrument_app.assert_not_called()
            mock_sqla.assert_not_called()
            mock_httpx.assert_not_called()
            mock_celery.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: enabled path
# ---------------------------------------------------------------------------


class TestSetupTelemetryEnabled:
    def test_provider_configured_with_resource(self):
        """TracerProvider must receive a Resource with the configured service name."""
        mock_settings = _make_settings()

        mock_provider = MagicMock()
        mock_resource = MagicMock()

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create", return_value=mock_resource) as mock_res,
            patch("app.telemetry.TracerProvider", return_value=mock_provider) as mock_tp,
            patch("app.telemetry.trace.set_tracer_provider") as mock_set,
            patch("app.telemetry.OTLPSpanExporter"),
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor"),
            patch("app.telemetry.SQLAlchemyInstrumentor"),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry()

            mock_res.assert_called_once_with({"service.name": "test-service"})
            mock_tp.assert_called_once_with(resource=mock_resource)
            mock_set.assert_called_once_with(mock_provider)

    def test_otlp_exporter_uses_configured_endpoint(self):
        """The OTLP exporter endpoint must be constructed from settings."""
        mock_settings = _make_settings(endpoint="http://collector:4318")

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create"),
            patch("app.telemetry.TracerProvider"),
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter") as mock_exp,
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor"),
            patch("app.telemetry.SQLAlchemyInstrumentor"),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry()

            mock_exp.assert_called_once_with(endpoint="http://collector:4318/v1/traces")

    def test_otlp_exporter_strips_trailing_slash(self):
        """A trailing slash in OTEL_ENDPOINT must not produce a double slash in the URL."""
        mock_settings = _make_settings(endpoint="http://collector:4318/")

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create"),
            patch("app.telemetry.TracerProvider"),
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter") as mock_exp,
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor"),
            patch("app.telemetry.SQLAlchemyInstrumentor"),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry()

            mock_exp.assert_called_once_with(endpoint="http://collector:4318/v1/traces")

    def test_batch_span_processor_added_to_provider(self):
        """A BatchSpanProcessor wrapping the exporter must be added to the provider."""
        mock_settings = _make_settings()
        mock_provider = MagicMock()
        mock_processor = MagicMock()
        mock_exporter = MagicMock()

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create"),
            patch("app.telemetry.TracerProvider", return_value=mock_provider),
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter", return_value=mock_exporter),
            patch("app.telemetry.BatchSpanProcessor", return_value=mock_processor) as mock_bsp,
            patch("app.telemetry.FastAPIInstrumentor"),
            patch("app.telemetry.SQLAlchemyInstrumentor"),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry()

            mock_bsp.assert_called_once_with(mock_exporter)
            mock_provider.add_span_processor.assert_called_once_with(mock_processor)

    def test_fastapi_instrumented_when_app_provided(self):
        """FastAPI app must be instrumented when passed to setup_telemetry."""
        mock_settings = _make_settings()
        mock_fastapi_app = MagicMock()

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create"),
            patch("app.telemetry.TracerProvider"),
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter"),
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor") as mock_fastapi,
            patch("app.telemetry.SQLAlchemyInstrumentor"),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry(fastapi_app=mock_fastapi_app)

            mock_fastapi.instrument_app.assert_called_once_with(mock_fastapi_app)

    def test_fastapi_not_instrumented_when_no_app(self):
        """FastAPI instrumentation must be skipped when no app is passed."""
        mock_settings = _make_settings()

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create"),
            patch("app.telemetry.TracerProvider"),
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter"),
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor") as mock_fastapi,
            patch("app.telemetry.SQLAlchemyInstrumentor"),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry()

            mock_fastapi.instrument_app.assert_not_called()

    def test_sqlalchemy_instrumented_when_engine_provided(self):
        """SQLAlchemy engine must be instrumented when passed to setup_telemetry."""
        mock_settings = _make_settings()
        mock_engine = MagicMock()
        mock_sqla_instance = MagicMock()

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create"),
            patch("app.telemetry.TracerProvider"),
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter"),
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor"),
            patch("app.telemetry.SQLAlchemyInstrumentor", return_value=mock_sqla_instance),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry(sqlalchemy_engine=mock_engine)

            mock_sqla_instance.instrument.assert_called_once_with(engine=mock_engine.sync_engine)

    def test_sqlalchemy_not_instrumented_when_no_engine(self):
        """SQLAlchemy instrumentation must be skipped when no engine is passed."""
        mock_settings = _make_settings()
        mock_sqla_instance = MagicMock()

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create"),
            patch("app.telemetry.TracerProvider"),
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter"),
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor"),
            patch("app.telemetry.SQLAlchemyInstrumentor", return_value=mock_sqla_instance),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry()

            mock_sqla_instance.instrument.assert_not_called()

    def test_httpx_and_celery_always_instrumented(self):
        """HTTPX and Celery instrumentation must always run when OTel is enabled."""
        mock_settings = _make_settings()
        mock_httpx_instance = MagicMock()
        mock_celery_instance = MagicMock()

        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.Resource.create"),
            patch("app.telemetry.TracerProvider"),
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter"),
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor"),
            patch("app.telemetry.SQLAlchemyInstrumentor"),
            patch("app.telemetry.HTTPXClientInstrumentor", return_value=mock_httpx_instance),
            patch("app.telemetry.CeleryInstrumentor", return_value=mock_celery_instance),
        ):
            setup_telemetry()

            mock_httpx_instance.instrument.assert_called_once()
            mock_celery_instance.instrument.assert_called_once()

    def test_idempotent_when_already_initialized(self):
        """setup_telemetry() must be a no-op when a custom TracerProvider is already set."""
        mock_settings = _make_settings()

        # Return a non-ProxyTracerProvider to simulate an already-initialized state.
        with (
            patch("app.telemetry.settings", mock_settings),
            patch("app.telemetry.trace.get_tracer_provider", return_value=MagicMock()),
            patch("app.telemetry.TracerProvider") as mock_tp,
            patch("app.telemetry.trace.set_tracer_provider"),
            patch("app.telemetry.OTLPSpanExporter"),
            patch("app.telemetry.BatchSpanProcessor"),
            patch("app.telemetry.FastAPIInstrumentor"),
            patch("app.telemetry.SQLAlchemyInstrumentor"),
            patch("app.telemetry.HTTPXClientInstrumentor"),
            patch("app.telemetry.CeleryInstrumentor"),
        ):
            setup_telemetry()

            mock_tp.assert_not_called()
