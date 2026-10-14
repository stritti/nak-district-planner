## ADDED Requirements

### Requirement: CalDAV protocol details remain inside the adapter
The system SHALL isolate DAV XML, href, ETag, authentication, and library-specific objects inside the CalDAV adapter.

#### Scenario: CalDAV implementation library changes
- **WHEN** the underlying CalDAV implementation is replaced
- **THEN** CalendarConnector consumers and domain models SHALL remain unchanged

### Requirement: CalDAV resource locations are treated as untrusted
The adapter SHALL validate resource hrefs before write or delete operations.

#### Scenario: Resource href escapes configured calendar
- **WHEN** a DAV response contains an href with another origin or a path outside the configured calendar collection
- **THEN** the adapter SHALL reject the operation with a connector error

### Requirement: CalDAV XML processing is hardened
DAV response parsing and query construction SHALL avoid unsafe XML expansion and unsafe string interpolation.

#### Scenario: Malformed or hostile XML
- **WHEN** a server returns malformed or unsafe XML
- **THEN** the adapter SHALL fail safely without resolving external entities or exposing sensitive details

### Requirement: CalDAV deletion semantics are interoperable
The adapter SHALL preserve ETag-aware deletion and common idempotent missing-resource responses.

#### Scenario: Resource already absent
- **WHEN** a DELETE returns 404 or 410
- **THEN** the operation SHALL be treated as idempotently complete

#### Scenario: Resource revision changed
- **WHEN** an If-Match protected DELETE returns 412
- **THEN** the adapter SHALL report a connector conflict/error and SHALL NOT silently acknowledge deletion
