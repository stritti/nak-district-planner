## MODIFIED Requirements

### Requirement: Request tenant context

`TenantMiddleware` SHALL extract district routing hints from the request path, the `district_id` query parameter and the `X-District-ID` header, and expose those values as **untrusted** request context. It SHALL NOT derive an authenticated subject or authorization state from an unverified bearer token. The authenticated subject SHALL be established only by verified OIDC/FastAPI authentication dependencies, which SHALL load current persisted superadmin status and effective memberships. Tenant authorization SHALL be enforced by route-level RBAC checks and PostgreSQL Row-Level Security, not by `TenantValidationMiddleware`, which is no longer part of the runtime middleware stack. Normal users SHALL be rejected with 403 when they request a district outside their effective scopes. A verified, database-authorized superadmin SHALL be permitted to access any district, including when the user has no memberships. Authentication and business validation rules remain applicable. `/health`, `/api/health` and `/api/v1/auth` SHALL retain their existing route-specific authentication exemptions.

#### Scenario: Foreign district in path for a non-superadmin

- **WHEN** an authenticated non-superadmin without an effective membership in another district requests `/api/v1/districts/{other}/...`
- **THEN** the verified route authorization rejects the request with 403
- **AND** PostgreSQL RLS does not disclose the foreign district's protected rows

#### Scenario: Superadmin with no membership selects a district

- **WHEN** a verified superadmin with no memberships requests `/api/v1/districts/{other}/...`
- **THEN** the authorized request can access that district according to the operation's business rules
- **AND** the absence of a membership does not trigger a tenant-level 403

#### Scenario: Forged token or untrusted routing context

- **WHEN** a caller supplies an unverified bearer token or an arbitrary `X-District-ID` header claiming access to another district
- **THEN** neither the middleware nor database RLS treats those claims as authorization
- **AND** protected routes require a verified subject and current database-backed permissions

#### Scenario: Superadmin status revoked during an authenticated session

- **WHEN** a user whose superadmin flag was revoked sends the next authenticated request without an effective membership for its district
- **THEN** that request is rejected with 403 and RLS prevents cross-district access
- **AND** a previously selected district or cached frontend state cannot restore global access
