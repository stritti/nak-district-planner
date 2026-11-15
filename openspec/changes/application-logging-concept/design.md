# Application Logging Concept — Design

The authoritative, operator-facing concept lives in `docs/operations/logging.md`. This file records the implementation design for the backend and frontend.

## Current state

- `services/backend/app/main.py:59` calls `logging.basicConfig(level=INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s", force=True)` in the lifespan, then `install_log_redaction()`.
- `app/adapters/api/log_redaction.py` installs `RedactSecretPathsFilter` on root and uvicorn handlers; it redacts `/api/v1/export/<token>` from message, `exc_text` and `stack_info`.
- `AuditMiddleware` (`app/adapters/api/middleware/audit.py:90`) generates a `request_id = uuid4()` per request and persists it in `audit_logs`; application log records never see it.
- Celery worker/beat run with `--loglevel=info` from compose; no shared format.
- Frontend uses ad-hoc `console.*` calls.

## Design

### Logging setup module (backend)

New module `app/logging_config.py` (stdlib `logging` only, no new dependency):

- `setup_logging()` reads `settings.log_level` and `settings.log_format` and configures the root logger with a single `StreamHandler(sys.stdout)`.
- `JsonFormatter` renders one JSON object per line with fields `timestamp` (UTC ISO 8601), `level`, `logger`, `message`, `service`, `env`, `version`, plus `request_id`/`task_id` when present in the record, and `exception` (`type`, `message`, redacted `stacktrace`) for error records.
- Text formatter keeps the current human-readable shape for `APP_ENV=development`.
- `install_log_redaction()` is called after handler setup so the filter also applies to the new handler; the JSON formatter applies `redact_secret_path` to the rendered message and stacktrace as well, so redaction holds even if a handler is added later without the filter.
- Level resolution: `LOG_LEVEL` (default `INFO`); if `APP_ENV=production` and level is `DEBUG`, log a warning once and use `INFO`. Unlike `production_guard`, this deliberately does not abort the start: a too-verbose level is an operator slip, not an unsafe configuration, and refusing to start would turn a log setting into an outage. Invalid values (`LOG_LEVEL=VERBOSE`, `LOG_FORMAT=xml`) are rejected by settings validation and stop the service.

### Settings

`app/config.py` gains `log_level: str = "INFO"` and `log_format: str = "json"` (validated: level in the stdlib level names, format in `{json, text}`; default format becomes `text` when `app_env == "development"` unless explicitly set). Added to `.env.example` and `.env.docker*`.

### Request correlation

- New pure ASGI `RequestIdMiddleware`, registered outermost (before `AuditMiddleware`), sets `request_id` in a `contextvars.ContextVar` and resets the token after the response, so no ID leaks into later records. It takes `X-Request-ID` only when the peer is in `TRUSTED_PROXIES` (reusing `app/adapters/api/client_ip.py`) **and** the value matches `^[A-Za-z0-9-]{1,64}$`; otherwise `uuid4()`. The length limit keeps the value inside `audit_logs.request_id` (`String(100)`, migration 0012): an oversized header must never make the audit insert fail, because a failed denial audit turns into 503. The charset rules out log injection (newlines, quotes) in text and JSON output.
- `AuditMiddleware` reads the ID from the context var instead of calling `uuid.uuid4()` (`middleware/audit.py:90`); domain audit entries written via `audit_service` use the same value.
- A `logging.Filter` reads the context var and sets `record.request_id`; the JSON/text formatters include it. The same middleware sets it as an OTel span attribute (`span.set_attribute("request_id", ...)`) on the current server span.

### nginx and external proxies

- Frontend nginx (`services/frontend/nginx.conf`): every backend `location` (`/api/` and `^~ /api/v1/export/`) adds `proxy_set_header X-Request-ID $request_id;`. nginx otherwise forwards request headers unchanged, so without this line every client could choose its own ID through the trusted proxy. `$request_id` is 32 hex characters and matches the validation pattern.
- Traefik (`docker-compose.prod.yml`) and any other external TLS proxy need no change: whatever `X-Request-ID` they pass is overwritten by the frontend nginx, which is the only peer in `TRUSTED_PROXIES`. Correlating with the external proxy's own access log is out of scope.
- Direct access to port 8000 (development) comes from an untrusted peer and always gets a fresh UUID.

### uvicorn and Celery wiring

- uvicorn's access logger has no request duration, so it is disabled (`--no-access-log` in the Dockerfile `CMD` and the backend command of `docker-compose.override.yml`) and `RequestIdMiddleware` writes the access record itself on logger `app.access`: method, `redact_secret_path(path)` without query string, status, `duration_ms`, `request_id`. `/health`, `/api/health` and 429 responses from the rate limiter are logged at `DEBUG` only. `setup_logging` routes `uvicorn` and `uvicorn.error` to the shared handler.
- `app/celery_app.py`: connect `celery.signals.setup_logging` — when any receiver is connected, Celery skips its own root-logger configuration (`worker_hijack_root_logger`), so the app's format survives. The receiver calls `setup_logging(service="beat")` when started as `celery beat` and `setup_logging(service="worker")` otherwise (detected from the signal's `loglevel`/argv or a `CELERY_SERVICE` env var set in compose). The existing `worker_init`/`beat_init` receivers stay for the schema check.
- `task_prerun` sets `task_id`/`task_name` into a context var, `task_postrun` resets it; the logging filter copies them onto the record. Compose `--loglevel` is kept aligned with `LOG_LEVEL`.

### Frontend

- `services/frontend/src/utils/logger.ts`: `debug/info/warn/error` wrappers around `console.*`; in production builds only `warn`/`error` emit. All arguments pass through a sanitizer that recursively replaces values of keys matching `token|password|secret|credential|email|name` (case-insensitive substring, so `accessToken`, `displayName` are covered) with `[redacted]`; `Error` objects are reduced to `name`, `message` and `stack`. Axios request/response objects are never passed to the logger.
- Existing `console.*` call sites are migrated to the logger. Nothing is sent to the server (non-goal).

### What is deliberately not changed

- Audit persistence in `audit_logs` (separate capability `audit-logging`).
- nginx access/error log formats (runbook §1.1a) except that they must stay redaction-safe.
- OTel exporter configuration (`app/telemetry.py`); only the span attribute is added.
