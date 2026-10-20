## 1. Instrumented workload
- [x] 1.1 Add reproducible 50k-slot PostgreSQL fixture, tenant separation and cleanup.
- [x] 1.2 Add benchmark harness for existing filter combinations, count and page, offsets 0/10000.

## 2. Query-plan and safety validation
- [x] 2.1 Capture SQL `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` on actual count/page statements.
- [x] 2.2 Verify index usage, OR/ANY branch, correctness and statement timeout behavior.
- [x] 2.3 Document measured latency/buffer evidence and decisions.

## 3. Follow-up and quality
- [x] 3.1 If needed, open separate OpenSpec/migration for index or keyset API (not needed per the measured plans, see `docs/operations/event-list-performance.md`).
- [x] 3.2 Run full backend tests, CI and >=80% coverage, request independent review.
