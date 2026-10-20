# Event List Query Performance Verification

## Current flow

`GET /api/v1/events` delegates to `SqlPlanningSlotRepository.list_page`, which runs separate total-count and paginated queries filtered by district and date, with optional group, congregation, approval, status and service category. The congregation branch includes an OR over own slots and applicable district slots using `ANY(applicability)`. It orders by `planning_date`, `planning_time`, `id`, using the existing public `limit <=500` and `offset <=10000` contract.

## Workload and measurements

Build synthetic data inside a disposable test database: at least 25 congregations, 50,000 planning slots across multiple dates, a mix of confirmed/active, cancelled, district-scope and congregation-scope entries, plus a separate tenant. Use fixed random seed and documented category/applicability distributions. Exercise every filter combination defined in `tests/integration/test_event_listing_postgres.py` and specific representative cases: district query, own congregation, distributed events with `applicability`, empty group, active/confirmed service, pages at offset 0 and 10,000, and count-only behavior.

Use SQLAlchemy's actual generated statements and bound parameters with `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for the count and page query separately. Record wall clock after a warm-up with multiple repetitions, JSON plan digest, scanned rows, shared buffers and index scans. Assert correctness against existing SQL integration tests. Metrics are *observations* from the controlled CI/dev PostgreSQL version, not production SLO promises; publish actual numbers only after running.

## Decisions

Investigate whether the existing `(district_id, planning_date)` index is used. For the congregation OR and `ANY(applicability)` predicates, observe row estimate accuracy and bitmap/index behavior. Consider a GIN/index migration only when an analyzed plan and repeated workload demonstrate benefit. Any migration includes before/after results, write-amplification cost and tests.

Retain offset/limit by default for compatibility. If offset 10,000 and the total query exceed an acceptable tested bound, produce a *separate* versioned OpenSpec/API/Frontend keyset proposal with migration strategy rather than changing semantics as part of a performance probe.

Set and exercise a database-side statement timeout in performance tests; propose a repository-level timeout only if baseline measurements justify it and the API can map timeout to a safe operational error without returning partial data. Record the explicit choice in the runbook.

## CI and safety

Performance tests run on a real disposable PostgreSQL database and are labeled separately from quick correctness tests. Avoid flaky strict wall-clock thresholds on shared CI runners: keep structural assertions on plans and parameters, and store timing data for review. The existing CI already runs `tests/performance`. Include cleanup in failure paths and verify row-level security or tenant scope remains intact. Backend test coverage >=80%.
