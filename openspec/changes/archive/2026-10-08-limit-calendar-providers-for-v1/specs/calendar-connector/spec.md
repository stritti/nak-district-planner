## ADDED Requirements

### Requirement: Version 1.0 supports only ICS and CalDAV calendar providers
The system SHALL accept only `ICS` and `CALDAV` as calendar integration types for new integrations and SHALL reject `GOOGLE` and `MICROSOFT` with HTTP 422 and a message naming the supported providers. The integration type SHALL NOT be changeable via update.

#### Scenario: Creating a Google integration
- **WHEN** an admin creates a calendar integration with type `GOOGLE` or `MICROSOFT`
- **THEN** the API SHALL respond with 422 stating that only ICS and CalDAV are supported, and SHALL NOT store the integration

#### Scenario: Changing the type to Microsoft
- **WHEN** an admin sends a PATCH with `type: MICROSOFT`
- **THEN** the API SHALL respond with 422 and SHALL NOT change the integration

### Requirement: Existing unsupported integrations are kept but not synchronised
Existing `GOOGLE` and `MICROSOFT` integrations SHALL remain readable, SHALL be skipped by the automatic sync with a warning log entry, and a manual sync SHALL fail with HTTP 409 without contacting the provider.

#### Scenario: Automatic sync
- **WHEN** the periodic sync job runs and an active integration has type `GOOGLE`
- **THEN** no sync task SHALL be dispatched for it and a warning naming the integration SHALL be logged

#### Scenario: Manual sync
- **WHEN** an admin triggers a sync for a `MICROSOFT` integration
- **THEN** the API SHALL respond with 409 and a message that the provider is not supported in version 1.0

#### Scenario: Resolving a conflict on a Google-linked event
- **WHEN** a planner resolves a deviation or sync conflict whose writable link belongs to a `GOOGLE` or `MICROSOFT` integration
- **THEN** the provider SHALL NOT be contacted, the API SHALL respond with 409, and the local state SHALL remain retryable

### Requirement: UI offers only supported providers
The calendar integration form SHALL offer ICS and CalDAV as selectable types and SHALL show Google and Microsoft only as disabled options marked "geplant".

#### Scenario: Opening the create form
- **WHEN** an admin opens the form for a new calendar integration
- **THEN** only ICS and CalDAV SHALL be selectable and Google/Microsoft SHALL be shown disabled as "geplant"
