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
