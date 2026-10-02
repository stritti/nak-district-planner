## Why

The CalDAV adapter currently owns REPORT XML construction, DAV response parsing, authentication details, href resolution, and iCalendar extraction. This is protocol-heavy infrastructure with subtle interoperability and security edge cases. The system needs a maintainable CalDAV boundary without changing calendar-sync domain semantics.

## What Changes

- Evaluate a maintained CalDAV client library against the existing httpx/defusedxml/icalendar implementation.
- Encapsulate query construction, multistatus parsing, authentication, ETag/href handling, and deletion behind the CalDAV adapter.
- Preserve SSRF/path-origin protections and safe XML parsing.
- Add CalDAV contract/interoperability tests including missing/deleted resources and malformed server responses.

## Capabilities

### New Capabilities
- `caldav-adapter-contract`
- `caldav-interoperability-hardening`

### Modified Capabilities
- `calendar-sync`
- `symmetric-deletion`

## Impact

Infrastructure adapter and dependencies only. Domain/application behavior and PlanningSlot aggregate rules remain unchanged.
