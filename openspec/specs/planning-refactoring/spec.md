# planning-refactoring Specification

## Purpose
Consolidates the technical refactoring rules introduced by #474: a single planning-series generation implementation with UTC generation keys and deletion-ledger suppression, Celery entrypoints kept in inbound adapters, one external event fingerprint calculation, and non-destructive frontend error handling.

## Requirements

### Requirement: Unified planning-series generation

All API and background requests to materialize a planning series SHALL use
the same series-expansion, UTC generation-key, idempotency, and deletion-suppression
implementation. When a slot is inserted, its internal event instance SHALL be
created in the same transaction.

#### Scenario: Repeated generation at a UTC date boundary
- **WHEN** an administrator requests generation twice for a local-time slot close to midnight
- **THEN** the second request SHALL not create another slot or event instance

#### Scenario: Previously removed occurrence
- **WHEN** the generator encounters an occurrence with a deletion-ledger key
- **THEN** neither a slot nor an internal event instance SHALL be recreated

### Requirement: Non-destructive CSRF failure handling

A rejected state-changing request SHALL surface an HTTP error without reloading
the page or discarding unsaved inputs.

#### Scenario: CSRF validation returns 403
- **WHEN** a save operation receives a CSRF validation error
- **THEN** the current form SHALL remain mounted and the caller SHALL receive
  a structured error containing status 403

### Requirement: Unknown frontend routes

Unknown frontend URLs SHALL display a public not-found page with a link back to
the event overview rather than a blank router outlet.

#### Scenario: Unknown URL
- **WHEN** a browser navigates to an unregistered URL
- **THEN** the frontend SHALL render the not-found page

### Requirement: Configurable expected matrix duration

Matrix expected end times SHALL use `sync_expected_duration_minutes` unless
the caller specifies an explicit duration.

#### Scenario: Duration override
- **WHEN** configured duration is 60 minutes and the actual end matches
- **THEN** the matrix SHALL not mark an end-time deviation

### Requirement: Canonical external calendar fingerprint

All synchronized provider events SHALL use one deterministic fingerprint over
the sync-relevant fields. Connectors SHALL not independently compute or persist
an unused content hash.

#### Scenario: Event cancellation is detected
- **WHEN** the same provider event changes from active to cancelled
- **THEN** the canonical fingerprint SHALL change so synchronization can detect it

### Requirement: Inbound worker and application dependency boundaries

Celery task entrypoints SHALL reside under `app.adapters.worker` while business
operations remain in application services. Registered Beat jobs SHALL reference
existing tasks, and unused task entrypoints SHALL be removed. Application services
SHALL not import HTTP API request schemas.

#### Scenario: Worker executes a scheduled task
- **WHEN** Celery loads its declared task modules and dispatches a scheduled job
- **THEN** the task SHALL remain registered and SHALL call its application service

#### Scenario: Architecture debt is repaid
- **WHEN** an API schema dependency or application-layer Celery entrypoint is removed
- **THEN** the corresponding exception SHALL be removed from the architecture test allowlist

### Requirement: Simplified frontend and dependency surface

The affected UI components SHALL use Tailwind utilities instead of component-local
style blocks. Unused frontend components, unused OIDC sample variables, and unused
backend dependencies SHALL be removed without altering existing user workflows.

#### Scenario: Existing views are rendered
- **WHEN** the matrix, confirmation dialog, deviation indicator, or toast appears
- **THEN** its content and interactions SHALL remain available using shared styling

### Requirement: Authenticated and observable CI coverage reporting

Backend CI SHALL enforce its local coverage threshold and critical-router coverage
independently of external reporting. The Codecov upload SHALL run only with a
configured `CODECOV_TOKEN` secret and SHALL fail the CI job when that
authenticated upload fails. When the secret is unavailable (including forked
pull requests), CI SHALL explicitly warn and SHALL retain its local coverage
gate and downloadable coverage artifact.

#### Scenario: Missing Codecov token
- **WHEN** a pull request runs without a configured `CODECOV_TOKEN`
- **THEN** CI SHALL skip the external upload, report the reason, and still
  enforce its local coverage thresholds

#### Scenario: Authenticated Codecov upload fails
- **WHEN** `CODECOV_TOKEN` is configured and Codecov rejects the report
- **THEN** the backend CI job SHALL fail instead of reporting a false success

### Requirement: Stable multi-interval series recurrence

Weekly and monthly recurring series SHALL use a stable series-based anchor,
preferentially `active_from` and otherwise the creation date. Daily rolling
generation windows SHALL not affect interval parity. Calendar-week parity SHALL
be computed on Monday-based weeks.

#### Scenario: Biweekly generation with a moving window
- **WHEN** a biweekly Monday series starts on June 1 and the next generator run
  begins June 2
- **THEN** the same June 15 occurrence SHALL be selected, without introducing
  a June 8 occurrence

#### Scenario: Every-two-month recurrence
- **WHEN** a two-month series begins in January and generation is requested
  from February
- **THEN** its next occurrences SHALL remain in March and May, rather than
  changing the month parity to February and April

#### Scenario: Implicit weekday across recurrence formats
- **WHEN** a weekly series omits explicit weekdays but defines `active_from`
- **THEN** both the modern and legacy recurrence formats SHALL use the
  `active_from` weekday; without `active_from` they SHALL use the creation weekday

### Requirement: Planning generation compatibility

Both scheduled worker entrypoints SHALL instantiate their use cases with all
required repositories. Series generation SHALL default uncategorized slots to
`Gottesdienst` without overriding an explicit category. The generated event
duration SHALL honor the current configured duration when generation runs.

#### Scenario: Scheduled draft generation
- **WHEN** the daily draft-service task executes
- **THEN** it SHALL provide district, congregation, slot and event repositories
  to the draft generation use case

#### Scenario: Unset series category
- **WHEN** a recurring series has no category
- **THEN** its generated PlanningSlot SHALL have category `Gottesdienst`
  so that it remains classified as a worship service

#### Scenario: Updated event duration
- **WHEN** the configured expected duration differs from its import-time value
- **THEN** the generated EventInstance SHALL use the current value

### Requirement: Typed calendar integration commands

HTTP request schemas SHALL be explicitly converted into typed application
commands. Update commands SHALL distinguish omitted fields from explicit null,
including clearing the nullable default category, without depending on dynamic
string-keyed dictionaries in application code.

#### Scenario: Clear default category
- **WHEN** the update request explicitly includes `default_category: null`
- **THEN** the category SHALL be cleared without modifying other omitted fields

#### Scenario: New HTTP schema property
- **WHEN** an unrelated optional property is added to the HTTP create schema
- **THEN** the application command mapper SHALL remain compatible

### Requirement: Invalid recurrence isolation

Create and update requests SHALL reject recurrence intervals that are not positive
integers, including booleans, strings, zero and negative numbers. The scheduled
generator SHALL log and skip any previously persisted series with an invalid
interval, without stopping generation of valid series in other districts.

#### Scenario: Invalid recurrence requested
- **WHEN** a district administrator creates or updates a series with an invalid
  recurrence interval
- **THEN** the API SHALL reject the request with HTTP 422

#### Scenario: Malformed legacy series in scheduled batch
- **WHEN** the database contains one malformed series and another valid series
- **THEN** the malformed series SHALL be skipped with a log warning and the
  valid series SHALL still create its scheduled occurrence
