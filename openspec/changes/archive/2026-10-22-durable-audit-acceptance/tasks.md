## 1. Transactional boundary
- [x] 1.1 A mutation whose audited tenant cannot be resolved is rejected instead of skipped (`AuditTenantResolutionError`, unit and real-PostgreSQL rollback tests)
- [x] 1.2 Session dependency with `scope="function"`: a failed commit yields 5xx before the response (#694; unit, guard and real-PostgreSQL COMMIT rejection)

## 2. HTTP audit
- [x] 2.1 (#695) Synchronous durable audit for denials and failed state-changing requests; 503 and counter when the insert fails
- [x] 2.2 (#695) Successful writes: request-scoped marker for domain audit rows; HTTP entry inside the request transaction only when none exists
- [x] 2.3 (#695) Remove `AuditService` queue, writer and lifespan hooks

## 3. Operations and closure
- [x] 3.1 (#695) Metric `nak.audit.write_failures`, log line without payload, runbook section (audit failures, 503 semantics, outage behaviour)
- [x] 3.2 (#695) Real-PostgreSQL tests for commit failure, audit insert failure, atomic HTTP entry, no duplicate with domain audit; coverage >= 80 %
- [x] 3.3 Baseline spec updated, change archived
