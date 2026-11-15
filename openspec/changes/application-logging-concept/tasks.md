## 1. Backend logging setup
- [ ] 1.1 Add `log_level` and `log_format` to `app/config.py` (validation + development default) and to `.env.example` / `.env.docker*`.
- [ ] 1.2 Create `app/logging_config.py` with `setup_logging(service=...)`: JSON Lines formatter, text formatter, production DEBUG guard, single stdout handler.
- [ ] 1.3 Re-install `install_log_redaction()` after handler setup and apply `redact_secret_path` inside the JSON formatter for message and stacktrace.
- [ ] 1.4 Replace `configure_logging()` in `app/main.py` with the new setup; keep the lifespan call order (logging before production guard).

## 2. Correlation IDs
- [ ] 2.1 Add a `contextvars`-based `request_id` (honoring `X-Request-ID` only from `TRUSTED_PROXIES`, reusing the `request-identity` client-IP helper) via middleware.
- [ ] 2.2 Add a `logging.Filter` that copies `request_id` onto every record; render it in both formatters.
- [ ] 2.3 Pass the same `request_id` to `audit_service` and set it as an OTel span attribute.
- [ ] 2.4 Set `task_id`/`task_name` in the context var for Celery tasks and render them in the formatters.

## 3. uvicorn, worker and beat wiring
- [ ] 3.1 Configure uvicorn access/error loggers in `setup_logging` with the redacted access format (method, redacted path, status, duration); exempt `/health` and `/api/health` at INFO.
- [ ] 3.2 Call `setup_logging(service="worker")` from `app/celery_app.py` on worker/beat start so worker and beat share format and level; keep compose `--loglevel` as fallback.

## 4. Frontend logger
- [ ] 4.1 Add `services/frontend/src/utils/logger.ts` (dev console vs. production warn/error, sanitizer dropping `token`/`password`/`email`, no payloads, no server transport).
- [ ] 4.2 Migrate existing `console.*` call sites to the logger.

## 5. Tests
- [ ] 5.1 Unit tests: JSON line fields, text format in development, LOG_LEVEL parsing, DEBUG-refused-in-production fallback.
- [ ] 5.2 Unit tests: redaction of export tokens in message, exception text and stacktrace for both formatters.
- [ ] 5.3 Integration test: one `request_id` appears in the log output, in `audit_logs` and in the OTel span for the same request; untrusted `X-Request-ID` is ignored.
- [ ] 5.4 Test: health endpoints produce no INFO access-log line; worker task error line contains `service`, `task_id`, `task_name`.

## 6. Documentation (same change)
- [x] 6.1 Add the authoritative concept page `docs/operations/logging.md`.
- [x] 6.2 Register the page in the VitePress sidebar (`docs/.vitepress/config.mts`) and in `docs/documentation-map.md`.
- [ ] 6.3 Add cross-references to the logging concept in `docs/operations/production-runbook.md`, `docs/operations/opentelemetry.md` and `docs/operations/admin-scripts.md` (`nakctl logs`).
- [ ] 6.4 Update the baseline: move the `logging` capability from this change into `openspec/specs/logging` and record MODIFIED deltas for `request-identity` and `audit-logging` once implementation lands.
