## Context

CalDAV is a protocol family rather than one uniform server API. Hand-built XML is transparent but increases maintenance cost and interoperability risk. A library is valuable only if it preserves security controls and does not leak its object model beyond the adapter.

## Design Decisions

1. CalendarConnector remains the only application-facing boundary.
2. Evaluate the maintained `caldav` package against keeping httpx + XML builders; adoption is evidence-based, not mandatory.
3. XML parsing must remain protected against entity expansion/XXE. If a library parser cannot provide equivalent guarantees, keep hardened parsing at the boundary.
4. Resource hrefs are untrusted. Delete/update targets must remain same-origin and within the configured calendar collection.
5. ETag/If-Match semantics and 404/410 idempotency remain explicit adapter behavior.
6. REPORT/query construction must use a library or XML builder rather than interpolating untrusted values into XML strings.
7. Server-specific quirks are isolated behind adapter helpers and covered by fixtures/contract tests, not branches in sync_service.
8. Missing resources/deletion detection must integrate with the common deletion/tombstone semantics without inventing CalDAV-specific domain states.

## Migration Strategy

First add characterization fixtures for representative DAV multistatus responses. Introduce the selected implementation behind the unchanged CalDAVConnector. Keep fixtures independent of the chosen library so an implementation rollback does not invalidate the contract tests.
