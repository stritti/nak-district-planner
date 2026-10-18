## 1. Instrumented workload
- [ ] 1.1 Add reproducible 50k-slot PostgreSQL fixture, tenant separation and cleanup.
- [ ] 1.2 Add benchmark harness for existing filter combinations, count and page, offsets 0/10000.

## 2. Query-plan and safety validation
- [ ] 2.1 Capture SQL `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` on actual count/page statements.
- [ ] 2.2 Verify index usage, OR/ANY branch, correctness and statement timeout behavior.
- [ ] 2.3 Document measured latency/buffer evidence and decisions.

## 3. Follow-up and quality
- [ ] 3.1 If needed, open separate OpenSpec/migration for index or keyset API.
- [ ] 3.2 Run full backend tests, CI and >=80% coverage, request independent review.
