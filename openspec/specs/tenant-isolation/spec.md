# tenant-isolation Specification

## Purpose

Defense-in-depth isolation of districts (tenants): request-level tenant context and validation middleware plus PostgreSQL Row-Level Security evaluated under a non-owner application role.

## Requirements

### Requirement: Request tenant context

`TenantMiddleware` SHALL extract district routing hints from the request path, the `district_id` query parameter and the `X-District-ID` header, and expose those values as **untrusted** request context. It SHALL NOT derive an authenticated subject or authorization state from an unverified bearer token. `/health`, `/api/health` and `/api/v1/auth` SHALL retain their existing route-specific authentication exemptions.

#### Scenario: Forged token or untrusted routing context

- **WHEN** a caller supplies an unverified bearer token or an arbitrary `X-District-ID` header claiming access to another district
- **THEN** neither the middleware nor database RLS treats those claims as authorization
- **AND** protected routes require a verified subject and current database-backed permissions

### Requirement: Tenant authorization uses the verified subject

Verified OIDC/FastAPI authentication dependencies SHALL establish the subject and load its current persisted superadmin status and effective memberships. Route-level RBAC checks and PostgreSQL Row-Level Security SHALL enforce tenant authorization; `TenantValidationMiddleware` is no longer part of the runtime stack. Normal users SHALL get 403 for a district outside their effective scopes. A verified superadmin SHALL access any district, even without memberships.

#### Scenario: Foreign district in path
- **WHEN** an authenticated non-superadmin without an effective membership requests `/api/v1/districts/{other}/...`
- **THEN** the route authorization rejects it with 403 before any protected tenant data is returned, with RLS enforcing the boundary

#### Scenario: Foreign district in path for a non-superadmin

- **WHEN** an authenticated non-superadmin without an effective membership in another district requests `/api/v1/districts/{other}/...`
- **THEN** the verified route authorization rejects the request with 403
- **AND** PostgreSQL RLS does not disclose the foreign district's protected rows

#### Scenario: Memberships in two districts

- **WHEN** a non-superadmin holds memberships in units of district A and district B
- **THEN** route authorization and RLS allow each unit according to its own membership
- **AND** a district in which the user holds no membership remains rejected with 403

#### Scenario: Superadmin with no membership selects a district

- **WHEN** a verified superadmin with no memberships requests `/api/v1/districts/{other}/...`
- **THEN** the authorized request can access that district according to the operation's business rules
- **AND** the absence of a membership does not trigger a tenant-level 403

#### Scenario: Superadmin status revoked during an authenticated session

- **WHEN** a user whose superadmin flag was revoked sends the next authenticated request without an effective membership for its district
- **THEN** that request is rejected with 403 and RLS prevents cross-district access
- **AND** a previously selected district or cached frontend state cannot restore global access

### Requirement: Database session context
Each database session SHALL set `app.current_user_sub`, roles and district/congregation context with transaction-local `set_config`; Celery maintenance tasks SHALL instead set `app.is_system_worker=true`. The application SHALL connect with a dedicated non-owner role, while migrations run as the owner via the separate `migrate` service.

#### Scenario: Worker task
- **WHEN** a scheduled cross-tenant task runs
- **THEN** it operates under RLS with the system-worker flag rather than as table owner

### Requirement: Row-Level Security policies
RLS SHALL be enabled on tenant tables (planning slots, event instances, service assignments, leaders, invitations, external candidates, unavailabilities, notifications, export tokens, reminder and hook configurations, among others). Policies SHALL allow rows only for superadmins, the system worker or users with a matching district or congregation membership of sufficient role; public ICS export reads SHALL be scoped by `app.current_export_token`.

#### Scenario: Direct query across tenants
- **WHEN** a session for a user of district A selects planning slots of district B
- **THEN** PostgreSQL returns no rows of district B
