## ADDED Requirements

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
The in-process fallback limiter SHALL cap the number of buckets and SHALL NOT scan the complete bucket set on every sensitive request.

#### Scenario: Many identifiers arrive during a Valkey outage
- **WHEN** requests create more local buckets than the configured maximum
- **THEN** old buckets are evicted while memory remains bounded
- **AND** stale-bucket cleanup is performed periodically rather than on every request
