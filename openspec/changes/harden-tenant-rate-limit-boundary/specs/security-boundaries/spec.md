## ADDED Requirements

### Requirement: Tenant authorization uses only verified user identity
Middleware SHALL NOT decode an unverified Bearer payload to derive a user subject for membership or tenant authorization decisions.

#### Scenario: Forged bearer subject targets a district
- **WHEN** a request contains a syntactically JWT-like Bearer token with an attacker-chosen `sub`
- **AND** no authentication layer has verified that token yet
- **THEN** tenant middleware does not expose that `sub` as authenticated tenant context
- **AND** authorization is deferred to the normal authenticated RBAC/RLS path

### Requirement: Bearer presence does not grant authenticated rate limits
The rate limiter SHALL consider a request authenticated only when a verified principal is already available. An arbitrary Authorization header SHALL NOT receive an authenticated-user multiplier.

### Requirement: Sensitive public endpoints retain fallback abuse protection
When the distributed Valkey limiter fails open, the application SHALL apply a bounded process-local rate limit to security-sensitive public POST endpoints.

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