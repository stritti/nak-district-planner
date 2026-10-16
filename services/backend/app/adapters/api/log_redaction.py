# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Keep secret ICS export tokens out of logs, audit metadata and metric labels.

``/api/v1/export/{token}/calendar.ics`` carries a bearer secret in the URL path
(calendar clients cannot send headers). Every place that records a request path
must therefore go through :func:`redact_secret_path`, and the process-wide log
filter below catches third-party loggers (``uvicorn.access``) as a safety net.
"""

from __future__ import annotations

import logging
import re

REDACTED = "{redacted}"
_EXPORT_PREFIX = "/api/v1/export/"
# Everything directly below the export prefix is the secret; `export-tokens`
# (management API) has no slash after "export" and is deliberately untouched.
_SECRET_SEGMENT = re.compile(r"(/api/v1/export/)[^/?#\s\"']+")


def redact_secret_path(value: str) -> str:
    """Replace the secret path segment of an export feed URL."""
    if _EXPORT_PREFIX not in value:
        return value
    return _SECRET_SEGMENT.sub(rf"\1{REDACTED}", value)


class RedactSecretPathsFilter(logging.Filter):
    """Redact export secrets from the formatted message of any log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - never break logging because of a bad format string
            return True
        if _EXPORT_PREFIX in message:
            record.msg = redact_secret_path(message)
            record.args = None
        return True


def install_log_redaction() -> None:
    """Attach the filter to every handler of the root and uvicorn loggers (idempotent)."""
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error"):
        for handler in logging.getLogger(name).handlers:
            if not any(isinstance(f, RedactSecretPathsFilter) for f in handler.filters):
                handler.addFilter(RedactSecretPathsFilter())
