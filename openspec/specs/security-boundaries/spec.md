# security-boundaries Specification

## Purpose
Legt fest, welche Identitaet Tenant-Autorisierung und Rate-Limiting vertrauen duerfen, und wie sensitive oeffentliche Endpunkte bei Valkey-Ausfall begrenzt bleiben.

## Requirements

### Requirement: Tenant authorization uses only verified user identity
Middleware SHALL NOT decode an unverified Bearer payload to derive a user subject for membership or tenant authorization decisions. Tenant authorization SHALL be enforced after token validation by authenticated RBAC checks and PostgreSQL RLS.

#### Scenario: Forged bearer subject targets a district
- **WHEN** a request contains a syntactically JWT-like Bearer token with an attacker-chosen `sub`
- **AND** no authentication layer has verified that token yet
- **THEN** tenant middleware does not expose that `sub` as authenticated tenant context
- **AND** authorization is deferred to the normal authenticated RBAC/RLS path

#### Scenario: Foreign tenant resource is addressed
- **WHEN** an authenticated user addresses a resource outside the user's permitted tenant scope
- **THEN** authenticated RBAC and RLS enforce isolation
- **AND** pre-authentication middleware does not infer membership from bearer payload claims

### Requirement: Bearer presence does not grant authenticated rate limits
The rate limiter SHALL consider a request authenticated only when a verified principal is already available. An arbitrary Authorization header SHALL NOT receive an authenticated-user multiplier.

#### Scenario: Unverified bearer header on a business endpoint
- **WHEN** a request carries an `Authorization: Bearer` header
- **AND** no verified principal is available on the request
- **THEN** the rate limiter applies the anonymous limit keyed by client IP
- **AND** no authenticated-user multiplier is granted

### Requirement: Sensitive public endpoints retain fallback abuse protection
When the distributed Valkey limiter fails open, the application SHALL apply a bounded process-local rate limit to explicitly declared security-sensitive public POST endpoints. Fallback limits SHALL be named configuration rather than route-specific numeric literals embedded in request dispatch logic.

#### Scenario: OIDC token exchange during Valkey outage
- **WHEN** the distributed normal or burst rate-limit check fails open
- **AND** repeated requests target `/api/v1/auth/oidc/token`
- **THEN** a process-local sliding-window limit is enforced
- **AND** requests above the local limit receive HTTP 429

#### Scenario: Public self-registration during Valkey outage
- **WHEN** the distributed limiter fails open
- **AND** repeated POST requests target a district self-registration collection endpoint
- **THEN** a stricter process-local sliding-window limit is enforced

#### Scenario: Ordinary business endpoint during Valkey outage
- **WHEN** the distributed limiter fails open on a non-sensitive business endpoint
- **THEN** the documented availability-first fail-open behaviour remains unchanged

### Requirement: Local fallback remains bounded under outage load
The in-process fallback limiter SHALL cap the number of buckets and SHALL NOT scan the complete bucket set on every sensitive request. Buckets SHALL be keyed by client identity and matched rule, not by raw request path, and a single bucket SHALL NOT hold more entries than its limit.

The fallback limiter is process-local: the effective limit is `limit × worker processes × replicas`, and counters reset on process restart. It is an outage safeguard, not a replacement for the distributed limiter.

#### Scenario: Path variation cannot evict an exhausted bucket
- **WHEN** a client has exhausted the self-registration fallback limit
- **AND** it sends requests to many different district UUIDs on the same route
- **THEN** all those requests share the client's single rule bucket
- **AND** the client remains limited

#### Scenario: Single client floods one endpoint
- **WHEN** one client sends far more requests than the limit within the window
- **THEN** denied requests are not recorded and the bucket size stays at the limit

#### Scenario: Many identifiers arrive during a Valkey outage
- **WHEN** requests create more local buckets than the configured maximum
- **THEN** old buckets are evicted while memory remains bounded
- **AND** stale-bucket cleanup is performed periodically rather than on every request

### Requirement: Distributed rate-limit buckets have bounded route cardinality
The distributed rate limiter SHALL key Valkey buckets by client, window and a bounded scope: the matching configured endpoint rule, otherwise one client-global bucket, with a separate burst bucket. Request paths, route parameters and export secrets SHALL NOT become key material.

#### Scenario: Invalid export tokens cannot reset a limit
- **WHEN** one client sends requests to many distinct invalid `/api/v1/export/{token}/calendar.ics` URLs
- **THEN** all requests count against the same export-rule bucket and the client-global burst window
- **AND** exhausting the limit produces HTTP 429

#### Scenario: Independent clients and burst windows
- **WHEN** two clients send requests through a trusted reverse proxy
- **THEN** each uses its own bounded buckets
- **AND** the burst counter is independent of the normal window

#### Scenario: Unrelated traffic does not exhaust a stricter route limit
- **WHEN** a client sends more requests to unconfigured routes than a configured route's ceiling
- **THEN** a request to the configured route is still evaluated only against its own bucket
