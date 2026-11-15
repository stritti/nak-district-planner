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
- Level resolution: `LOG_LEVEL` (default `INFO`); if `APP_ENV=production` and level is `DEBUG`, log a warning once and use `INFO`.

### Settings

`app/config.py` gains `log_level: str = "INFO"` and `log_format: str = "json"` (validated: level in the stdlib level names, format in `{json, text}`; default format becomes `text` when `app_env == "development"` unless explicitly set). Added to `.env.example` and `.env.docker*`.

### Request correlation

- New `RequestIdMiddleware` (or extension of the existing audit middleware) sets `request_id` in a `contextvars.ContextVar`: take `X-Request-ID` only when the peer is in `TRUSTED_PROXIES` (same helper as client-IP derivation, `request-identity` spec), otherwise `uuid4()`.
- A `logging.Filter` reads the context var and sets `record.request_id`; the JSON/text formatters include it. The same ID is passed to `audit_service` so `audit_logs.request_id` matches the log lines, and set as an OTel span attribute (`span.set_attribute("request_id", ...)`).
- Celery: a task decorator/signal sets `task_id` (and `task_name`) into the same context var for worker/beat logs.

### uvicorn and Celery wiring

- `docker-compose*.yml`: backend command keeps uvicorn defaults but passes `--log-config` pointing at the app's dict config (or the app configures uvicorn loggers in `setup_logging`), so `uvicorn.access` uses the redacted format and `LOG_LEVEL`; access-log lines carry method, redacted path, status, duration — health paths excluded at INFO.
- `app/celery_app.py`: on `worker_ready`/`beat_start` signals (or at import) call the same `setup_logging(service="worker")` so worker and beat emit the identical format/level; compose `--loglevel` stays as a fallback.

### Frontend

- `services/frontend/src/utils/logger.ts`: `debug/info/warn/error` wrappers around `console.*`; in production builds only `warn`/`error` emit, and all calls pass through a sanitizer that drops objects containing keys like `token`, `password`, `email` and never logs request payloads.
- Existing `console.*` call sites are migrated to the logger. Nothing is sent to the server (non-goal).

### What is deliberately not changed

- Audit persistence in `audit_logs` (separate capability `audit-logging`).
- nginx access/error log formats (runbook §1.1a) except that they must stay redaction-safe.
- OTel exporter configuration (`app/telemetry.py`); only the span attribute is added.
