## ADDED Requirements

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
