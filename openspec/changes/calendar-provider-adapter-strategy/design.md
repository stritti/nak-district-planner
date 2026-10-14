## Context

The hexagonal architecture requires external APIs to remain adapter concerns. Raw HTTP is small and transparent but makes pagination, OAuth refresh, throttling, and API evolution our maintenance burden.

## Design Decisions

1. CalendarConnector remains the application-facing port. SDK request/response types never cross the adapter boundary.
2. Google and Microsoft are evaluated independently; adopting one SDK does not force adoption of the other.
3. SDK adoption requires measurable value over httpx for pagination, auth refresh, throttling, maintenance, and async support.
4. The existing shared retry policy remains the fallback. Retries are limited to safe/idempotent reads and honor Retry-After where available.
5. Pagination must exhaust the provider result set for the requested window or fail explicitly; partial success must never look complete.
6. Provider exceptions are normalized to typed connector errors with safe, non-provider-controlled logging.
7. Token refresh/rotation must integrate with encrypted credential persistence without leaking tokens into logs or domain objects.
8. Contract tests define behavior once and run against each adapter implementation.

## Migration Strategy

Use characterization tests around the existing adapters first. Replace one provider at a time behind the unchanged port. Keep rollback possible by isolating provider-specific implementation changes to adapter modules and dependency configuration.

## Evaluation Matrix

For each candidate SDK record: maintenance activity, async support, OAuth/token refresh, pagination support, throttling semantics, testability, dependency weight, security history, and Python-version compatibility.
