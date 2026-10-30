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

## Library Decision (2026-10-30)

Evaluated: the maintained `caldav` package versus the existing httpx + defusedxml + icalendar stack.

| Criterion | `caldav` package | httpx + XML builder (chosen) |
|-----------|------------------|------------------------------|
| Async | Synchronous client; would need a thread offload inside the async sync worker | Native async, same client as every other connector |
| SSRF guard | Brings its own HTTP session, so `guarded_client()` (DNS pinning, private-range refusal) would have to be re-plumbed or bypassed | Uses `guarded_client()` unchanged |
| XML parsing | lxml-based object model; entity handling depends on library parser settings | defusedxml at the boundary refuses DTD entities and external references |
| Dependencies | Adds the library plus its HTTP and XML stack | No new dependency |
| Testability | Fixtures would mock library objects | Fixtures are plain DAV responses on an httpx mock |
| Scope needed | Discovery, scheduling, sync-token support we do not use | One calendar-query REPORT, GET, PUT, DELETE |

The adapter needs four requests against a configured collection URL. The library would add a second HTTP stack around the SSRF guard and a synchronous call path, without removing code we keep anyway (iCalendar normalization, href validation, ETag handling). Decision: keep httpx, move DAV details into `app/adapters/calendar/caldav_protocol.py`, and build the REPORT with an XML builder instead of string interpolation.

## Implementation Notes

- `caldav_protocol.py` owns REPORT construction, multistatus parsing, authentication and href resolution; `CalDAVConnector` only orchestrates requests and iCalendar normalization.
- `resource_url()` refuses another origin, dot segments (also percent-encoded), backslashes, a query, a fragment and the collection itself. Before this change an absolute href such as `https://host/cal/../other/x.ics` passed the prefix check for DELETE, PUT and existence probes.
- REPORT and the GET before a PUT go through `resilient_request` (bounded retries on transport errors and 408/425/429/5xx). PUT, DELETE and the existence probe are not retried.
- Href and ETag text is kept verbatim because both are persisted as resource identity and revision markers.
