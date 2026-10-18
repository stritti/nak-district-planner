## 1. Design and transactional boundary
- [ ] 1.1 Inventory write routes, raw SQL paths, worker operations and existing transactional domain audit coverage.
- [ ] 1.2 Define outbox schema, RLS/grants, migration and stable event identity.
- [ ] 1.3 Add failing real-PostgreSQL tests for write rollback on outbox failure and missing tenant.

## 2. Delivery
- [ ] 2.1 Implement transactional outbox emission for ORM and bulk mutations.
- [ ] 2.2 Implement idempotent dispatcher, bounded locking/batching, retry/backoff and quarantine.
- [ ] 2.3 Add crash-replay, concurrent worker, duplicate-delivery, malformed payload and connection-failure tests.

## 3. HTTP and operations
- [ ] 3.1 Replace loss-prone middleware queue with explicit durable HTTP-denial strategy; prove no post-response fail-closed claim.
- [ ] 3.2 Cover failed DB session setup, RLS GUC and commit, bounded shutdown and load failures.
- [ ] 3.3 Update metrics, alerting, health, runbook and CI. Enforce >=80% backend coverage.

## 4. Release
- [ ] 4.1 Verify migrations, tenancy and failure semantics in disposable PostgreSQL.
- [ ] 4.2 Run all CI checks and request independent PR review before merge.
