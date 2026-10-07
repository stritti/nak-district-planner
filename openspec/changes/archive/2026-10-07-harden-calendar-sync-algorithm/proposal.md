## Why

The calendar synchronization engine is central to the system's integrity. Hybrid governance combines internal planning authority with external calendar systems that differ in deletion semantics, revision support, and payload completeness. The sync contract must therefore cover not only returned events, but also missing resources, partial failures, concurrent field-level edits, and outbound reconciliation.

## What Changes

- Define a deterministic field-aware sync state machine.
- Formalize idempotent processing using content hashes, provider revisions, and durable tombstones.
- Add provider reconciliation for resources that disappear from full collection results.
- Define provider-specific deletion ingestion, including timestamp-less Google cancellation tombstones.
- Define conflict detection after field-level diffing so mergeable SOFT changes do not create false conflicts.
- Define bidirectional deviation resolution, including outbound correction of external event times.
- Define deletion behavior per calendar integration (MARK_CANCELLED or HARD_DELETE).
- Define observable partial-failure semantics with a dedicated failure count and retryable connector errors.
- Define loop prevention for updates and deletes.

## Capabilities

### New Capabilities
- `calendar-sync-algorithm`: Deterministic, idempotent, reconciliation-aware synchronization engine.

### Modified Capabilities
- `hybrid-calendar-sync`: Field-aware conflict handling, deviation resolution, deletion reconciliation, and loop prevention.

## Impact

- Sync application service and state machine.
- Calendar connector contract and provider adapters.
- CalendarIntegration persistence and API configuration.
- ExternalEventLink tombstone/revision metadata.
- Sync API/background-job result schema and operational observability.
- Regression and integration tests for provider-specific edge cases.
