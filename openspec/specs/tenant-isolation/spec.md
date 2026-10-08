# tenant-isolation Specification

## Purpose

Defense-in-depth isolation of districts (tenants): request-level tenant context and validation middleware plus PostgreSQL Row-Level Security evaluated under a non-owner application role.

## Requirements

### Requirement: Request tenant context
`TenantMiddleware` SHALL extract the tenant (district) from the path, the `district_id` query parameter or the `X-District-ID` header and the verified user subject, and SHALL expose it via context variables. `TenantValidationMiddleware` SHALL pre-check authenticated requests that name a tenant and reject them with 403 when the subject has no membership there; authoritative authorization SHALL remain in the route dependencies. `/health`, `/api/health` and `/api/v1/auth` SHALL be exempt.

#### Scenario: Foreign district in path
- **WHEN** an authenticated user without membership requests `/api/v1/districts/{other}/...`
- **THEN** the request is rejected with 403 before reaching the router

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
