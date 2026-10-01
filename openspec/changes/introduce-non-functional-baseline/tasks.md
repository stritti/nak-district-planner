## 1. Audit Infrastructure

- [x] 1.1 Create audit_log table *(AuditService + Middleware in `app/main.py` registriert)*
- [x] 1.2 Implement audit logging service *(`app/application/audit_service.py`)*
- [x] 1.3 Add audit hooks to PlanningSlot operations *(`after_flush`-Hook in `app/adapters/db/domain_audit.py`: CREATE/UPDATE/DELETE mit Akteur, Zeitpunkt, alten/neuen Werten, in derselben Transaktion; Retention-Cleanup schreibt einen `BULK_OPERATION`-Eintrag. Entscheidung gegen den `DomainEventBus` in design.md)*
- [x] 1.4 Add audit hooks to ServiceAssignment operations *(Tenant über den PlanningSlot; Integrationstest mit Gemeinde-Admin unter RLS)*
- [x] 1.5 Add audit hooks to CalendarIntegration operations *(Credentials nur als `redacted_fields`; Sync-Buchhaltung wird nicht protokolliert. Export-Tokens ebenso ohne Token-Wert)*
- [x] 1.6 Add audit hooks to export token operations *(AuditMiddleware deckt state-changing Requests ab)*

## 2. Security Baseline

- [x] 2.1 Implement credential encryption at application layer *(`app/application/crypto.py`)*
- [x] 2.2 Ensure export token generation meets entropy requirement *(`secrets.token_urlsafe(32)` in `domain/models/export_token.py`)*
- [x] 2.3 Add rate limiting middleware to public endpoints *(`RateLimitMiddleware` in `main.py`)*

## 3. Performance Validation

- [x] 3.1 Benchmark matrix endpoint under district-scale load *(50 Gemeinden, 3 Monate, PostgreSQL mit RLS: p95 ≈ 230 ms, Budget 500 ms — `tests/performance`, `docs/performance-baseline.md`)*
- [x] 3.2 Add performance test case for sync duration *(500 Events: Erstimport ≈ 5,5 s, Resync ≈ 4,3 s; N+1-Befund dokumentiert. CI-Anbindung nach dem Merge von #384, das Migrations-Schritt und `0002`-Fix mitbringt)*

## 4. Operational Reliability

- [x] 4.1 Implement exponential backoff retry for sync jobs *(Celery-Autoretry mit `retry_backoff=60`, `retry_backoff_max=3600`, Full-Jitter, `max_retries=4`; `IntegrationNotFoundError` wird nicht wiederholt — `app/application/tasks.py`)*
- [x] 4.2 Emit structured logs for sync failures *(`SyncIntegrationTask.on_retry`/`on_failure` loggen `integration_id`, `error_class`, `attempt` als `extra`-Felder; Exception-Text wird bewusst nicht geloggt, da er Provider-Daten enthalten kann)*
- [x] 4.3 Add alert hook for repeated sync failures *(`SyncFailureAlerter`: SYSTEM-Notification nach erschöpften Retries, dedupliziert gegen ungelesene Alerts derselben Integration — `app/application/sync_failure_alerts.py`)*
