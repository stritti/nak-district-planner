# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Application logging setup (OpenSpec ``logging``)."""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import celery_app, logging_config
from app.adapters.api.log_redaction import RedactSecretPathsFilter
from app.config import Settings
from app.logging_config import (
    ContextFilter,
    JsonFormatter,
    TextFormatter,
    request_id_var,
    setup_logging,
    task_id_var,
    task_name_var,
)

TOKEN = "s3cr3t-export-token-value"
FEED = f"/api/v1/export/{TOKEN}/calendar.ics"


@pytest.fixture
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in handlers:
        root.addHandler(handler)
    root.setLevel(level)


def _capture(config: Settings, service: str = "backend") -> io.StringIO:
    setup_logging(service=service, config=config)
    stream = io.StringIO()
    (handler,) = logging.getLogger().handlers
    assert isinstance(handler, logging.StreamHandler)
    handler.setStream(stream)
    return stream


def _lines(stream: io.StringIO) -> list[str]:
    return [line for line in stream.getvalue().splitlines() if line]


def _json_lines(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in _lines(stream)]


def _record(msg: str, *, level: int = logging.INFO, exc_info=None) -> logging.LogRecord:
    return logging.LogRecord("app.test", level, __file__, 1, msg, None, exc_info)


# ----------------------------------------------------------------- settings


def test_log_settings_defaults_and_development_format() -> None:
    dev = Settings(app_env="development")
    assert dev.log_level == "INFO"
    assert dev.effective_log_format == "text"
    assert Settings(app_env="staging").effective_log_format == "json"
    assert Settings(app_env="development", log_format="JSON").effective_log_format == "json"
    assert Settings(app_env="development", log_format=" ").log_format is None
    assert Settings(log_level="warning").log_level == "WARNING"


@pytest.mark.parametrize("field,value", [("log_level", "VERBOSE"), ("log_format", "xml")])
def test_invalid_log_settings_stop_startup(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})


# ----------------------------------------------------------------- format


def test_production_line_is_json_with_mandatory_fields(restore_logging: None) -> None:
    stream = _capture(Settings(app_env="staging", log_format="json"))
    logging.getLogger("app.main").info("started %s", "ok")
    (entry,) = _json_lines(stream)
    assert entry["message"] == "started ok"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "app.main"
    assert entry["service"] == "backend"
    assert entry["env"] == "staging"
    assert entry["version"]
    assert entry["timestamp"].endswith("+00:00")
    assert "request_id" not in entry


def test_explicit_text_format_wins_in_production(restore_logging: None) -> None:
    stream = _capture(Settings(app_env="staging", log_format="text"))
    logging.getLogger("app.main").warning("plain")
    (line,) = _lines(stream)
    assert "WARNING [app.main] plain" in line
    assert not line.startswith("{")


def test_error_record_contains_exception_object() -> None:
    formatter = JsonFormatter("worker", "production", "1.0.0")
    try:
        raise RuntimeError(f"boom {FEED}")
    except RuntimeError:
        import sys

        record = _record("failed", level=logging.ERROR, exc_info=sys.exc_info())
    entry = json.loads(formatter.format(record))
    assert entry["exception"]["type"] == "RuntimeError"
    assert TOKEN not in json.dumps(entry)
    assert "{redacted}" in entry["exception"]["message"]
    assert "Traceback" in entry["exception"]["stacktrace"]


def test_json_formatter_renders_stack_info_redacted() -> None:
    record = _record("with stack")
    record.stack_info = f"Stack: {FEED}"
    entry = json.loads(JsonFormatter("backend", "production", "1").format(record))
    assert entry["stack"] == "Stack: /api/v1/export/{redacted}/calendar.ics"


# ----------------------------------------------------------------- level


def _production_debug() -> Settings:
    # model_construct skips the production OIDC validation, which is irrelevant here.
    return Settings.model_construct(
        **{**Settings().model_dump(), "app_env": "production", "log_level": "DEBUG"}
    )


def test_debug_refused_in_production(restore_logging: None) -> None:
    stream = _capture(_production_debug())
    logging.getLogger("app.x").debug("hidden")
    assert logging.getLogger().level == logging.INFO
    assert "hidden" not in stream.getvalue()


def test_debug_refusal_warns_once_per_setup(restore_logging: None, capsys) -> None:
    setup_logging(config=_production_debug())
    out = capsys.readouterr().out
    assert out.count("LOG_LEVEL=DEBUG is not allowed") == 1


def test_warning_level_suppresses_info(restore_logging: None) -> None:
    stream = _capture(Settings(app_env="staging", log_format="json", log_level="WARNING"))
    logging.getLogger("app.x").info("quiet")
    logging.getLogger("app.x").debug("quieter")
    logging.getLogger("app.x").warning("loud")
    assert [e["message"] for e in _json_lines(stream)] == ["loud"]


# ----------------------------------------------------------------- redaction


@pytest.mark.parametrize("fmt", ["json", "text"])
def test_export_token_redacted_in_both_formats(restore_logging: None, fmt: str) -> None:
    stream = _capture(Settings(app_env="staging", log_format=fmt))
    try:
        raise ValueError(f"feed {FEED} failed")
    except ValueError:
        logging.getLogger("app.export").exception("request %s failed", FEED)
    output = stream.getvalue()
    assert TOKEN not in output
    assert "{redacted}" in output


def test_formatters_redact_without_the_handler_filter() -> None:
    record = _record(f"GET {FEED}")
    assert TOKEN not in JsonFormatter("backend", "production", "1").format(record)
    assert TOKEN not in TextFormatter().format(_record(f"GET {FEED}"))


def test_handlers_carry_redaction_and_context_filters(restore_logging: None) -> None:
    setup_logging(config=Settings(app_env="staging"))
    (handler,) = logging.getLogger().handlers
    kinds = {type(f) for f in handler.filters}
    assert {RedactSecretPathsFilter, ContextFilter} <= kinds
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "celery"):
        assert logging.getLogger(name).handlers == []
        assert logging.getLogger(name).propagate is True


def test_uvicorn_records_reach_the_shared_handler(restore_logging: None) -> None:
    stream = _capture(Settings(app_env="staging", log_format="json"))
    logging.getLogger("uvicorn.error").error("bind failed")
    (entry,) = _json_lines(stream)
    assert entry["logger"] == "uvicorn.error"


# ----------------------------------------------------------------- context


def test_request_id_from_context_and_no_leak_afterwards(restore_logging: None) -> None:
    stream = _capture(Settings(app_env="staging", log_format="json"))
    token = request_id_var.set("req-123")
    try:
        logging.getLogger("app.x").error("inside")
    finally:
        request_id_var.reset(token)
    logging.getLogger("app.x").error("outside")
    inside, outside = _json_lines(stream)
    assert inside["request_id"] == "req-123"
    assert "request_id" not in outside


def test_explicit_request_id_extra_is_kept(restore_logging: None) -> None:
    stream = _capture(Settings(app_env="staging", log_format="json"))
    logging.getLogger("app.x").error("handler", extra={"request_id": "from-state"})
    assert _json_lines(stream)[0]["request_id"] == "from-state"


def test_text_format_appends_correlation_ids(restore_logging: None) -> None:
    stream = _capture(Settings(app_env="development"))
    token = request_id_var.set("abc")
    try:
        logging.getLogger("app.x").info("hello")
    finally:
        request_id_var.reset(token)
    assert _lines(stream)[0].endswith("INFO [app.x] hello [request_id=abc]")


# ----------------------------------------------------------------- celery


def test_celery_service_name_from_argv() -> None:
    assert celery_app._celery_service(["celery", "-A", "app.celery_app", "beat"]) == "beat"
    assert celery_app._celery_service(["celery", "-A", "app.celery_app", "worker"]) == "worker"


def test_celery_setup_logging_receiver_is_connected() -> None:
    from celery import signals

    receivers = [r[1]() for r in signals.setup_logging.receivers]
    assert celery_app.configure_celery_logging in receivers


@pytest.mark.parametrize("service", ["worker", "beat"])
def test_celery_receiver_configures_service(
    restore_logging: None, monkeypatch, service: str
) -> None:
    monkeypatch.setattr(celery_app.sys, "argv", ["celery", "-A", "app.celery_app", service])
    monkeypatch.setattr(logging_config, "settings", Settings(app_env="staging", log_format="json"))
    celery_app.configure_celery_logging(loglevel="INFO")
    (handler,) = logging.getLogger().handlers
    stream = io.StringIO()
    handler.setStream(stream)
    logging.getLogger("celery.beat").info("tick")
    assert _json_lines(stream)[0]["service"] == service


def test_task_context_is_bound_and_cleared(restore_logging: None) -> None:
    stream = _capture(Settings(app_env="staging", log_format="json"), service="worker")

    class _Task:
        name = "sync_all_active_integrations"

    celery_app.bind_task_log_context(task_id="t-1", task=_Task())
    logging.getLogger("app.adapters.worker.tasks").error("sync failed")
    celery_app.clear_task_log_context()
    logging.getLogger("app.adapters.worker.tasks").info("after")
    failed, after = _json_lines(stream)
    assert failed["service"] == "worker"
    assert failed["task_id"] == "t-1"
    assert failed["task_name"] == "sync_all_active_integrations"
    assert "task_id" not in after and "task_name" not in after
    assert task_id_var.get() is None and task_name_var.get() is None


# ----------------------------------------------------------------- deployment


ROOT = Path(__file__).parents[4]


def test_uvicorn_access_log_is_disabled_everywhere() -> None:
    assert '"--no-access-log"' in (ROOT / "services/backend/Dockerfile").read_text()
    assert "--no-access-log" in (ROOT / "docker-compose.override.yml").read_text()


def test_app_writes_no_log_files() -> None:
    sources = (ROOT / "services/backend/app").rglob("*.py")
    assert not any("FileHandler" in path.read_text() for path in sources)
