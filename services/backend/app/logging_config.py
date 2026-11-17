# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Process-wide application logging (OpenSpec ``logging``, docs/operations/logging.md).

One stdout handler on the root logger, JSON Lines in production and readable
text in development. Correlation IDs (``request_id``, ``task_id``,
``task_name``) live in context variables and are copied onto every record by a
handler filter, so third-party loggers that propagate to root carry them too.
Both formatters redact secret export paths in the rendered line, independent of
the redaction filter that ``install_log_redaction`` attaches to the handlers.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import traceback
from datetime import UTC, datetime

from app.adapters.api.log_redaction import install_log_redaction, redact_secret_path
from app.config import Settings, settings

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
task_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("task_id", default=None)
task_name_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "task_name", default=None
)

# Optional structured fields rendered when present on the record (``extra=``).
_CONTEXT_FIELDS = ("request_id", "task_id", "task_name")
_EXTRA_FIELDS = ("method", "path", "status", "duration_ms")
_THIRD_PARTY_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "celery")


def current_request_id() -> str | None:
    return request_id_var.get()


class ContextFilter(logging.Filter):
    """Copy correlation IDs from the context onto the record (explicit extras win)."""

    def filter(self, record: logging.LogRecord) -> bool:
        for name, var in (
            ("request_id", request_id_var),
            ("task_id", task_id_var),
            ("task_name", task_name_var),
        ):
            if getattr(record, name, None) is None:
                setattr(record, name, var.get())
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line with the mandatory fields of the logging spec."""

    def __init__(self, service: str, env: str, version: str) -> None:
        super().__init__()
        self._static = {"service": service, "env": env, "version": version}

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_secret_path(record.getMessage()),
            **self._static,
        }
        for name in (*_CONTEXT_FIELDS, *_EXTRA_FIELDS):
            value = getattr(record, name, None)
            if value is not None:
                entry[name] = value
        if record.exc_info and record.exc_info[0] is not None:
            exc_type, exc_value, _tb = record.exc_info
            stacktrace = record.exc_text or "".join(traceback.format_exception(*record.exc_info))
            entry["exception"] = {
                "type": exc_type.__name__,
                "message": redact_secret_path(str(exc_value)),
                "stacktrace": redact_secret_path(stacktrace),
            }
        if record.stack_info:
            entry["stack"] = redact_secret_path(record.stack_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable development format; correlation IDs are appended when set."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        ids = " ".join(
            f"{name}={value}"
            for name in _CONTEXT_FIELDS
            if (value := getattr(record, name, None)) is not None
        )
        if ids:
            first, sep, rest = line.partition("\n")
            line = f"{first} [{ids}]{sep}{rest}"
        return redact_secret_path(line)


def resolve_level(config: Settings) -> tuple[int, bool]:
    """Return the effective level and whether DEBUG was refused in production."""
    if config.app_env == "production" and config.log_level == "DEBUG":
        return logging.INFO, True
    return logging.getLevelNamesMapping()[config.log_level], False


def setup_logging(service: str = "backend", config: Settings | None = None) -> None:
    """Configure the root logger with a single stdout handler (idempotent)."""
    config = config or settings
    level, debug_refused = resolve_level(config)

    handler = logging.StreamHandler(sys.stdout)
    if config.effective_log_format == "json":
        handler.setFormatter(JsonFormatter(service, config.app_env, config.app_version))
    else:
        handler.setFormatter(TextFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn and Celery install their own handlers; route everything through root.
    for name in _THIRD_PARTY_LOGGERS:
        third_party = logging.getLogger(name)
        third_party.handlers.clear()
        third_party.propagate = True
        third_party.setLevel(logging.NOTSET)

    install_log_redaction()

    if debug_refused:
        logging.getLogger(__name__).warning(
            "LOG_LEVEL=DEBUG is not allowed with APP_ENV=production; using INFO"
        )
