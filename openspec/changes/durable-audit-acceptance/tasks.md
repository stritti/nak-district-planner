## 1. Transactional boundary
- [x] 1.1 A mutation whose audited tenant cannot be resolved is rejected instead of skipped (`AuditTenantResolutionError`, unit and real-PostgreSQL rollback tests)
- [ ] 1.2 Session dependency with `scope="function"`: a failed commit yields 5xx before the response; test with injected commit failure on the real app stack

## 2. HTTP audit
- [ ] 2.1 Synchronous durable audit for denials and failed state-changing requests; 503 and counter when the insert fails
- [ ] 2.2 Successful writes: request-scoped marker for domain audit rows; HTTP entry inside the request transaction only when none exists
- [ ] 2.3 Remove `AuditService` queue, writer and lifespan hooks

## 3. Operations and closure
- [ ] 3.1 Metric, log line without payload, runbook section (audit failures, 503 semantics, outage behaviour)
- [ ] 3.2 Real-PostgreSQL tests for commit failure, audit insert failure, atomic HTTP entry, no duplicate with domain audit; coverage >= 80 %
- [ ] 3.3 Baseline spec updated, change archived
