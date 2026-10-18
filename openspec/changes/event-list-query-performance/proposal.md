## Why

Event-list pagination was moved into SQL in PR #618, but #626 requires load evidence and query-plan analysis before concluding the 10,000 offset bound remains acceptable or adding indexes.

## What changes

- Deterministic disposable PostgreSQL performance fixtures with large districts, many congregations and slots.
- Filter-matrix benchmarks, SQL `EXPLAIN (ANALYZE, BUFFERS)` and evidence for district-wide, congregation and applicability-array branches, total-count and page queries.
- Document tested PostgreSQL version, fixture size, index use, timing distributions, statement timeout and pagination decision.
- If an index or API contract change is warranted, isolate it in an independently reviewed OpenSpec change and migration.

## Non-goals

- Declare production latency from mocked tests or a tiny fixture.
- Silently switch the public offset/limit API to keyset pagination.
- Place load-generation artifacts or sensitive production data in source.

Issue: https://github.com/stritti/nak-district-planner/issues/626
