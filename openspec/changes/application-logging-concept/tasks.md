## 1. Backend logging setup
- [ ] 1.1 Add `log_level` and `log_format` to `app/config.py` (validation that rejects invalid values + development default) and to `.env.example` / `.env.docker*`.
- [ ] 1.2 Create `app/logging_config.py` with `setup_logging(service=...)`: JSON Lines formatter, text formatter, production DEBUG guard, single stdout handler.
- [ ] 1.3 Re-install `install_log_redaction()` after handler setup (extend it to the Celery loggers) and apply `redact_secret_path` inside both formatters for message and stacktrace.
- [ ] 1.4 Replace `configure_logging()` in `app/main.py` with the new setup; keep the lifespan call order (logging before production guard).

## 2. Correlation IDs
- [ ] 2.1 Add a pure ASGI `RequestIdMiddleware` (outermost) with a `contextvars`-based `request_id`: honor `X-Request-ID` only from `TRUSTED_PROXIES` (reuse `client_ip.py`) and only when it matches `^[A-Za-z0-9-]{1,64}$`, otherwise `uuid4()`; reset the context var after the response.
- [ ] 2.2 Add a `logging.Filter` that copies `request_id` onto every record; render it in both formatters.
- [ ] 2.3 Make `AuditMiddleware` and `audit_service` use the context-var `request_id` instead of generating their own; set it as an OTel span attribute.
- [ ] 2.4 Set `task_id`/`task_name` via `task_prerun`, reset via `task_postrun`, and render them in the formatters.
- [ ] 2.5 Frontend nginx: add `proxy_set_header X-Request-ID $request_id;` to the `/api/` and `/api/v1/export/` locations in `services/frontend/nginx.conf`.

## 3. uvicorn, worker and beat wiring
- [ ] 3.1 Disable the uvicorn access log (`--no-access-log` in the Dockerfile `CMD` and `docker-compose.override.yml`) and write the access record from `RequestIdMiddleware` (method, redacted path without query, status, `duration_ms`, `request_id`); log `/health`, `/api/health` and 429 responses at DEBUG only. Route `uvicorn`/`uvicorn.error` to the shared handler.
- [ ] 3.2 Connect `celery.signals.setup_logging` in `app/celery_app.py` so Celery does not hijack the root logger; call `setup_logging(service="worker")` for the worker and `setup_logging(service="beat")` for beat; keep compose `--loglevel` aligned with `LOG_LEVEL`.

## 4. Frontend logger
- [ ] 4.1 Add `services/frontend/src/utils/logger.ts` (dev console vs. production warn/error, recursive sanitizer masking `token`/`password`/`secret`/`credential`/`email`/`name` keys, no payloads, no server transport) with unit tests.
- [ ] 4.2 Migrate existing `console.*` call sites to the logger.

## 5. Tests
- [ ] 5.1 Unit tests: JSON line fields, text format in development, LOG_LEVEL/LOG_FORMAT validation (invalid values rejected), DEBUG-refused-in-production fallback.
- [ ] 5.2 Unit tests: redaction of export tokens in message, exception text and stacktrace for both formatters; captured backend/worker output contains no known test credential after a credential update.
- [ ] 5.3 Integration test: one `request_id` appears in the log output, in `audit_logs` (also for a 403) and in the OTel span for the same request.
- [ ] 5.4 Negative tests: untrusted `X-Request-ID` is ignored; a trusted but oversized (>64 chars) or malformed (newline, quote, space) header gets a fresh UUID and the request (including its denial audit) succeeds; no `request_id` leaks into records after the request.
- [ ] 5.5 Test: health endpoints and 429 responses produce no INFO access-log line; access line contains `duration_ms`; worker task error line contains `service=worker`, `task_id`, `task_name`; beat lines contain `service=beat`.
- [ ] 5.6 nginx test/check: the rendered `nginx.conf` sets `X-Request-ID $request_id` on every backend location (extend the existing nginx config checks, e.g. `tests/unit/test_issue_472_hardening.py`).

## 6. Documentation (same change)
- [x] 6.1 Add the authoritative concept page `docs/operations/logging.md`.
- [x] 6.2 Register the page in the VitePress sidebar (`docs/.vitepress/config.mts`) and in `docs/documentation-map.md`.
- [ ] 6.3 Add cross-references to the logging concept in `docs/operations/production-runbook.md`, `docs/operations/opentelemetry.md` and `docs/operations/admin-scripts.md` (`nakctl logs`); document `X-Request-ID` in `docs/security/audit-logging.md`.
- [ ] 6.4 Remove the "planned" status note from `docs/operations/logging.md` once the implementation is merged.
- [ ] 6.5 Archive the change (`openspec archive application-logging-concept`), which creates `openspec/specs/logging` and applies the `request-identity` and `audit-logging` deltas to the baseline.
