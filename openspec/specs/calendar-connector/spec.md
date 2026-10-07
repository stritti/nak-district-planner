# calendar-connector Specification

## Purpose

Defines how external calendar sources (ICS, CalDAV, Google, Microsoft 365) are connected to a district or congregation: the framework-free `CalendarConnector` port, its provider adapters, encrypted credential storage and the `/api/v1/calendar-integrations` management API. Synchronisation semantics live in `calendar-sync`; review of unmatched events in `external-event-ingestion`.

## Requirements

### Requirement: CalendarConnector port
The domain SHALL define an abstract `CalendarConnector` port in `app/domain/ports/calendar.py` whose abstract `fetch_events(credentials, from_dt, to_dt)` method returns normalised `RawCalendarEvent` value objects (uid, title, start/end, description, content hash, cancellation flag, optional revision marker and resource id). Connectors SHALL receive already decrypted credentials and SHALL NOT import FastAPI or SQLAlchemy.

#### Scenario: Incomplete connector implementation
- **WHEN** a subclass does not implement `fetch_events`
- **THEN** instantiating it raises `TypeError`

#### Scenario: Read-only connector receives a write request
- **WHEN** `update_event_times` or `delete_event` is called on a connector that does not override them
- **THEN** the connector raises `CalendarConnectorError` instead of silently succeeding

### Requirement: Provider adapters
The system SHALL provide connector adapters for `ICS`, `CALDAV`, `GOOGLE` and `MICROSOFT` integration types and SHALL select the adapter from a type-to-class registry. Provider and network failures SHALL surface as `CalendarConnectorError`.

#### Scenario: ICS feed is unreachable or invalid
- **WHEN** an ICS URL times out, returns an HTTP error or does not contain valid iCalendar data
- **THEN** the connector raises `CalendarConnectorError`

#### Scenario: Unknown integration type
- **WHEN** a sync is requested for a type without a registered connector
- **THEN** the sync fails explicitly instead of returning an empty result

### Requirement: Integration configuration
A `CalendarIntegration` SHALL belong to a district and MAY be scoped to one congregation of that district. It SHALL carry `type`, `sync_interval` (minutes, default 60), `capabilities` (`READ`, `WRITE`, `WEBHOOK`; default `READ`), `is_active`, an optional `default_category`, `delete_behavior` (`MARK_CANCELLED` default or `HARD_DELETE`), `last_synced_at` and `last_sync_error`.

#### Scenario: Congregation outside the district
- **WHEN** an integration is created for a congregation that does not belong to the given district
- **THEN** the API responds with 404 and no integration is stored

### Requirement: Credentials are encrypted at rest and never returned
Integration credentials SHALL be stored only as a Fernet token produced by `app.application.crypto.encrypt_credentials`, keyed from the application `SECRET_KEY`, and SHALL be decrypted only immediately before a connector call. API responses SHALL NOT contain credentials in plaintext or encrypted form.

#### Scenario: Integration is read through the API
- **WHEN** a client lists or updates calendar integrations
- **THEN** the response contains no `credentials` field

#### Scenario: Secret key mismatch
- **WHEN** stored credentials cannot be decrypted with the current key
- **THEN** a `CryptoError` is raised and the manual sync endpoint responds with 400

### Requirement: Calendar integration management API
The system SHALL expose `POST`, `GET`, `PATCH` and `DELETE` on `/api/v1/calendar-integrations` plus `POST /api/v1/calendar-integrations/{id}/sync`. District-level integrations SHALL require `DISTRICT_ADMIN`; congregation-scoped integrations SHALL accept `CONGREGATION_ADMIN` of that congregation or `DISTRICT_ADMIN`. Listing without `district_id` or `congregation_id` SHALL be reserved to superadmins.

#### Scenario: Viewer tries to create an integration
- **WHEN** a user with only `VIEWER` in the district posts a district-level integration
- **THEN** the API responds with 403

#### Scenario: Unscoped listing by a regular user
- **WHEN** a non-superadmin calls `GET /api/v1/calendar-integrations` without a scope parameter
- **THEN** the API responds with 403
