## ADDED Requirements

### Requirement: Connector registry pattern
The sync service SHALL use a dictionary registry to map calendar types to connector classes.

#### Scenario: New calendar provider
- **WHEN** a new CalendarType value is added to the enum
- **THEN** registering the connector SHALL require only adding an entry to `_CONNECTOR_MAP`
  without modifying any conditional branching logic

#### Scenario: Unknown calendar type
- **WHEN** `_get_connector()` is called with an unregistered CalendarType
- **THEN** the system SHALL raise a `NotImplementedError` with a descriptive message

### Requirement: OAuth stubs are clearly marked as not implemented
The system SHALL prevent users from configuring Google or Microsoft calendar integrations
until the OAuth flows are fully implemented.

#### Scenario: OAuth stub invoked
- **WHEN** the sync service attempts to use `GoogleCalendarConnector` or `MicrosoftGraphCalendarConnector`
- **THEN** a `NotImplementedError` SHALL be raised with a message indicating the feature is not yet available

### Requirement: Typed sync result objects
The sync service SHALL return a typed result object instead of an untyped dictionary.

#### Scenario: Sync completes
- **WHEN** a calendar sync run finishes
- **THEN** the result SHALL be a `SyncResult` dataclass with fields `created`, `updated`,
  `cancelled`, and `errors`

### Requirement: Health check endpoint
The system SHALL expose a health check endpoint that verifies database and cache connectivity.

#### Scenario: All services healthy
- **WHEN** `GET /health` is called and both the database and Redis are reachable
- **THEN** the response SHALL be HTTP 200 with `{ "status": "ok", "db": "ok", "redis": "ok" }`

#### Scenario: Database unreachable
- **WHEN** `GET /health` is called and the database is not reachable
- **THEN** the response SHALL be HTTP 503 with `{ "status": "degraded", "db": "error" }`
