## Why

The application currently logs with `logging.basicConfig` at a hardcoded `INFO` level and a plain text format (`services/backend/app/main.py:59`). There is no configurable level or format, no structured output for log aggregation, and the `request_id` that `AuditMiddleware` already generates for `audit_logs` never reaches application log records, so log lines cannot be correlated with audit entries or OTel traces. Operators have no single authoritative description of what is logged where, at which level, with which redaction and retention rules — only scattered runbook notes.

## What Changes

- Introduce a single application-logging concept (documented authoritatively in `docs/operations/logging.md`) covering backend API, Celery worker/beat, frontend and the bundled nginx proxies.
- Backend emits structured JSON Lines on stdout in production (`LOG_FORMAT=json`, default outside development) and human-readable text in development; level configurable via `LOG_LEVEL` (default `INFO`, `DEBUG` refused in production).
- One `request_id` per HTTP request (honoring `X-Request-ID` only from `TRUSTED_PROXIES`, per the `request-identity` spec) is attached to every log record of that request via a `contextvars`-based filter, referenced in `audit_logs` and set as an OTel span attribute; Celery tasks log `task_id`.
- The existing process-wide secret redaction (`install_log_redaction`) stays installed on all handlers and is extended to the new JSON formatter; secrets, PII and request payloads are never logged.
- uvicorn access/error logs use a defined redacted format; health endpoints are not logged at INFO.
- Frontend logs through a small logger utility: console output in development only, errors in production, never PII/tokens/payloads, and nothing is sent to the server.

## Capabilities

### New Capabilities
- `logging`: structured, redacted, correlatable application logging for backend, worker, beat and frontend, distinct from `audit-logging` (database) and OTel telemetry.

### Modified Capabilities
- `request-identity`: the shared trusted-proxy rule is reused for `X-Request-ID`.
- `audit-logging`: the audit entry's `request_id` becomes the same ID that appears in application log records.

## Impact

- `services/backend/app`: new logging setup module (stdlib `logging` only, JSON formatter, filters), config fields `LOG_LEVEL`/`LOG_FORMAT`, request-ID middleware/filter, uvicorn log config, Celery worker/beat setup; `.env.example` and the `.env.docker*` templates gain the new variables; compose log levels stay aligned with `LOG_LEVEL`.
- `services/frontend`: logger utility replacing ad-hoc `console.*` calls.
- Tests: unit tests for format, level fallback, redaction and request-ID propagation; integration test asserting `request_id` in log output and `audit_logs`.
- VitePress pages affected: new `docs/operations/logging.md` (authoritative concept), plus cross-references in `docs/operations/production-runbook.md`, `docs/operations/opentelemetry.md`, `docs/operations/admin-scripts.md`, the sidebar in `docs/.vitepress/config.mts` and `docs/documentation-map.md`.

## Dependencies

- `audit-logging` baseline: `request_id` is already persisted in `audit_logs`; this change only shares it with application logs.
- `request-identity` baseline: trusted-proxy IP derivation is reused for `X-Request-ID`.
- `security-boundaries` / `external-ics-proxy-redaction`: the export-token redaction filter must keep working on the new formatter.

## Non-goals

- No replacement of the database audit log; no central log aggregation mandate (OTLP remains optional).
- No client-side error-tracking service; the frontend never sends browser logs to the server.
- No new third-party logging dependency: stdlib `logging` with a JSON formatter is sufficient.
