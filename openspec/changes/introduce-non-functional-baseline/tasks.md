## 1. Audit Infrastructure

- [x] 1.1 Create audit_log table *(AuditService + Middleware in `app/main.py` registriert)*
- [x] 1.2 Implement audit logging service *(`app/application/audit_service.py`)*
- [ ] 1.3 Add audit hooks to PlanningSlot operations *(generische AuditMiddleware deckt HTTP-Requests ab; domänenspezifische Hooks fehlen — sollen auf dem `DomainEventBus` aus `event-driven-mail-hooks` (#379) aufsetzen statt eine zweite Hook-Infrastruktur einzuführen)*
- [ ] 1.4 Add audit hooks to ServiceAssignment operations *(siehe 1.3)*
- [ ] 1.5 Add audit hooks to CalendarIntegration operations *(siehe 1.3 — Middleware deckt bereits die CalendarIntegration-Router ab)*
- [x] 1.6 Add audit hooks to export token operations *(AuditMiddleware deckt state-changing Requests ab)*

## 2. Security Baseline

- [x] 2.1 Implement credential encryption at application layer *(`app/application/crypto.py`)*
- [x] 2.2 Ensure export token generation meets entropy requirement *(`secrets.token_urlsafe(32)` in `domain/models/export_token.py`)*
- [x] 2.3 Add rate limiting middleware to public endpoints *(`RateLimitMiddleware` in `main.py`)*

## 3. Performance Validation

- [ ] 3.1 Benchmark matrix endpoint under district-scale load
- [ ] 3.2 Add performance test case for sync duration

## 4. Operational Reliability

- [x] 4.1 Implement exponential backoff retry for sync jobs *(Celery-Autoretry mit `retry_backoff=60`, `retry_backoff_max=3600`, Full-Jitter, `max_retries=4`; `IntegrationNotFoundError` wird nicht wiederholt — `app/application/tasks.py`)*
- [x] 4.2 Emit structured logs for sync failures *(`SyncIntegrationTask.on_retry`/`on_failure` loggen `integration_id`, `error_class`, `attempt` als `extra`-Felder; Exception-Text wird bewusst nicht geloggt, da er Provider-Daten enthalten kann)*
- [x] 4.3 Add alert hook for repeated sync failures *(`SyncFailureAlerter`: SYSTEM-Notification nach erschöpften Retries, dedupliziert gegen ungelesene Alerts derselben Integration — `app/application/sync_failure_alerts.py`)*
