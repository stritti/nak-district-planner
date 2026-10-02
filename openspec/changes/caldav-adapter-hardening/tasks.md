## 1. Characterization
- [ ] Add representative CalDAV REPORT/multistatus fixtures.
- [ ] Cover timezone/all-day/duration events, ETags, relative and absolute hrefs, cancelled events, missing resources, malformed XML, auth failures, and 404/410/412 deletion semantics.
- [ ] Capture same-origin/path traversal security behavior.

## 2. Library decision
- [ ] Evaluate maintained caldav library vs hardened httpx + XML builder.
- [ ] Record compatibility, async strategy, security/parser behavior, dependency footprint, and testability.
- [ ] Select the smallest maintainable implementation satisfying the contract.

## 3. Adapter refactor
- [ ] Encapsulate query construction and DAV response parsing.
- [ ] Preserve iCalendar normalization behind RawCalendarEvent.
- [ ] Preserve ETag/href metadata required for safe writes/deletes.
- [ ] Integrate common retry policy only for idempotent REPORT/GET operations.

## 4. Verification
- [ ] Run common CalendarConnector contract tests plus CalDAV interoperability tests.
- [ ] Verify SSRF/path-origin and XML hardening regressions.
- [ ] Verify no CalDAV/library types leak into domain/application layers.
- [ ] Run backend tests, lint/security checks, and coverage >= 80%.
