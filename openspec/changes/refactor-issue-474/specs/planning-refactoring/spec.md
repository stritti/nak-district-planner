## ADDED Requirements

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
