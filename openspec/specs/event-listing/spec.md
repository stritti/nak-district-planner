# event-listing Specification

## Purpose
TBD - created by archiving change event-list-query-performance. Update Purpose after archive.

## Requirements

### Requirement: Evidence-backed event-list performance
The event-list query SHALL be benchmarked against a reproducible large PostgreSQL fixture with representative district and congregation filters, including distributed-event `applicability`, and both page and total-count queries.

#### Scenario: District-wide listing
- **WHEN** the large fixture is queried by district/date with limit/offset
- **THEN** the result and total agree with the reference semantics
- **AND** the database query plan and buffer usage are recorded

#### Scenario: Congregation and applicability filtering
- **WHEN** the listing includes congregation-local and distributed district events
- **THEN** the query plan records the OR/ANY branch and its index behavior
- **AND** unauthorized district records remain absent

#### Scenario: Deep offset
- **WHEN** offset 10000 is benchmarked
- **THEN** the measured query plan, time and buffer costs are reported
- **AND** offset pagination remains unchanged unless a separate reviewed API contract change is accepted

### Requirement: Performance rollout decision
The engineering record SHALL state whether the existing district/date index is sufficient, whether an applicability index is justified, and whether a statement timeout is appropriate, based on actual `EXPLAIN (ANALYZE, BUFFERS)` evidence.

#### Scenario: Index or API redesign needed
- **WHEN** measured plans justify a new index or keyset pagination
- **THEN** the change is specified and reviewed independently rather than silently altering API behavior

### Requirement: Repeatable and safe measurements
Benchmarks SHALL use a disposable database, defined dataset sizes, reproducible seed and a bounded query execution time. They SHALL not depend on production data.

#### Scenario: Test fails
- **WHEN** a benchmark errors or exceeds its statement timeout
- **THEN** the job reports the failure and cleans its synthetic fixture
