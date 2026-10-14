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

### Requirement: Calendar URLs are validated before storage
The system SHALL reject calendar integration credentials whose `url` is not an HTTPS URL with a host, contains embedded credentials, or targets `localhost` or a non-public IP literal, on create and on update, with HTTP 422 and a message that does not echo the URL.

#### Scenario: Private address on create
- **WHEN** an admin creates an ICS or CalDAV integration with `https://169.254.169.254/latest/meta-data`
- **THEN** the API SHALL respond with 422 and SHALL NOT store the integration

#### Scenario: Plain HTTP on update
- **WHEN** an admin updates credentials to `http://calendar.example.com/feed.ics` while `CALENDAR_ALLOW_INSECURE_URLS` is false
- **THEN** the API SHALL respond with 422 and SHALL NOT change the integration

### Requirement: Every outbound calendar connection is restricted to public addresses
The calendar HTTP client SHALL resolve the host of every request, including redirect hops, reject it if any resolved address is loopback, private, link-local, unique-local, reserved, multicast, or an IPv4-mapped/6to4/NAT64 form of such an address, and connect to the validated address while preserving the original Host header and TLS server name.

#### Scenario: Hostname resolves to loopback
- **WHEN** a feed hostname resolves to `127.0.0.1`, `::1`, `fc00::1` or `::ffff:10.0.0.1`
- **THEN** the connector SHALL fail with a connector error before any connection is opened

#### Scenario: Network-specific NAT64 prefix
- **WHEN** `CALENDAR_NAT64_PREFIXES` lists an RFC 6052 prefix (length 32, 40, 48, 56, 64 or 96) and a feed hostname resolves to an address inside it whose embedded IPv4 (u-octet skipped) is `10.0.0.1`, `127.0.0.1` or `169.254.169.254`
- **THEN** the connector SHALL fail before any connection is opened, while a public embedded IPv4 SHALL be accepted; invalid prefixes SHALL prevent the settings from loading

#### Scenario: Trailing-dot localhost
- **WHEN** an admin stores `https://localhost./feed.ics` or `https://foo.localhost./feed.ics`
- **THEN** the API SHALL respond with 422

#### Scenario: Deprecated IPv6 site-local address
- **WHEN** a URL literal or a DNS answer is in `fec0::/10`
- **THEN** it SHALL be treated as non-public and rejected, even though the platform reports it as globally routable

#### Scenario: Legacy numeric IPv4 literal
- **WHEN** an admin stores a URL whose host is an abbreviated, integer, hex or octal IPv4 form such as `127.1`, `2130706433` or `0x7f.1`
- **THEN** the host SHALL be interpreted as the IPv4 address it denotes and a non-public address SHALL be rejected with 422

#### Scenario: DNS rebinding between check and connect
- **WHEN** a hostname resolves to a public address during validation
- **THEN** the connection SHALL be made to exactly that address so a later DNS answer cannot redirect it

#### Scenario: Redirect to an internal host
- **WHEN** a feed responds with a redirect to an internal address
- **THEN** the redirect SHALL NOT be followed and the sync SHALL fail with a generic error

### Requirement: Calendar responses are size-limited
The calendar HTTP client SHALL abort responses larger than 10 MB, based on Content-Length and while streaming.

#### Scenario: Compressed feed (decompression bomb)
- **WHEN** a feed answers with a `Content-Encoding` other than `identity`
- **THEN** the connector SHALL reject it, since only `Accept-Encoding: identity` is requested

#### Scenario: Oversized feed
- **WHEN** a feed returns more than 10 MB
- **THEN** reading SHALL stop and the connector SHALL raise a connector error

### Requirement: A calendar fetch never takes longer than 30 seconds
The calendar HTTP client SHALL bound every fetch by one total budget of 30 seconds covering DNS resolution, every connect and TLS attempt across all resolved addresses, the response headers and the body; retries of transient failures SHALL share the same budget. Exceeding it SHALL fail with the generic connector error.

#### Scenario: Stalled TLS handshake on every address
- **WHEN** each resolved address accepts the TCP connection but never completes the TLS handshake
- **THEN** the fetch SHALL fail after at most 30 seconds in total

#### Scenario: Slowly trickling body
- **WHEN** a feed sends its body in small chunks, each within the read timeout, but slower than the budget allows
- **THEN** reading SHALL stop when the budget is used up

#### Scenario: Retries
- **WHEN** a transient failure triggers retries
- **THEN** all attempts and backoff waits together SHALL stay within the 30-second budget

### Requirement: Calendar errors do not leak targets or secrets
Connector errors and persisted `last_sync_error` values SHALL NOT contain URLs, credentials, HTTP status codes, or the distinction between transport and HTTP failures.

#### Scenario: Hostname resolves to a private address
- **WHEN** a feed hostname resolves to a private address
- **THEN** the user-facing error SHALL be identical to the one for an unresolvable host

#### Scenario: CalDAV server returns 401
- **WHEN** a CalDAV REPORT fails with HTTP 401 for a URL containing a secret path
- **THEN** the error message SHALL be the generic CalDAV load failure text without URL, user name, password or status code

### Requirement: Insecure calendar URLs are a development-only opt-in
`CALENDAR_ALLOW_INSECURE_URLS` SHALL default to false and SHALL block application startup when enabled with `APP_ENV=production`.

#### Scenario: Opt-in in production
- **WHEN** the application starts in production with `CALENDAR_ALLOW_INSECURE_URLS=true`
- **THEN** the production guard SHALL refuse to start

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
