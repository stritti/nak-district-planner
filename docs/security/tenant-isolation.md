# Tenant Isolation (SEC-020, SEC-021)

## Overview

This document describes the Tenant Isolation implementation for the NAK District Planner application, addressing security issues **SEC-020** (Insufficient Tenant Isolation) and **SEC-021** (Cross-Tenant Data Access) from the security analysis.

## Threat Description

In a multi-tenant application, insufficient tenant isolation can lead to:
- **Cross-Tenant Data Access**: Users can access data belonging to other tenants
- **Privilege Escalation**: Users can access data at higher privilege levels
- **Data Leakage**: Sensitive data from one tenant can be exposed to another
- **Compliance Violations**: Failure to meet data segregation requirements

## Solution: Multi-Layer Tenant Isolation

The implementation provides **Defense in Depth** with multiple layers of tenant isolation:

### Layer 1: Application-Level (Middleware)

- **TenantMiddleware**: Extracts tenant context from requests
- **TenantValidationMiddleware**: Validates tenant access
- **Permission Checks**: Role-based access control

### Layer 2: Service-Level (Validation)

- **TenantValidationService**: Validates user memberships in tenants
- **Cross-Tenant Access Validation**: Validates access across tenant hierarchies

### Layer 3: Database-Level (RLS Policies)

- **PostgreSQL Row-Level Security**: Enforces tenant isolation at the database level
- **Automatic Filtering**: Database automatically filters rows based on tenant context

## Architecture

### Tenant Model

The NAK District Planner uses a hierarchical tenant model:

```text
┌─────────────────────────────────────────────────────────────┐
│                        District (Root Tenant)                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  District Admin Users                                       ││
│  │  - Can access all congregations in the district             ││
│  │  - Can manage district-wide settings                        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Congregation 1 (Sub-Tenant)                                ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │  Congregation Admin Users                               │││
│  │  │  - Can access congregation data                         │││
│  │  │  - Can manage congregation settings                     │││
│  │  └─────────────────────────────────────────────────────┘││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │  Planner Users                                          │││
│  │  │  - Can create and manage events                         │││
│  │  │  - Can assign services                                   │││
│  │  └─────────────────────────────────────────────────────┘││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │  Viewer Users                                           │││
│  │  │  - Can view events and assignments                       │││
│  │  └─────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Congregation 2 (Sub-Tenant)                                ││
│  │  ...                                                     ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Tenant Context (`app/tenant.py`)

```python
# Context variables for tenant information
current_tenant: ContextVar[Optional[uuid.UUID]]
current_district: ContextVar[Optional[uuid.UUID]]
current_congregation: ContextVar[Optional[uuid.UUID]]
current_user_sub: ContextVar[Optional[str]]
current_user_roles: ContextVar[Optional[list[str]]]

class TenantContext:
    @staticmethod
    def get_tenant() -> uuid.UUID | None
    @staticmethod
    def get_district() -> uuid.UUID | None
    @staticmethod
    def get_congregation() -> uuid.UUID | None
    @staticmethod
    def set_context(...)
    @staticmethod
    def clear_context()
```

### Tenant Middleware (`app/adapters/api/middleware/tenant.py`)

```python
```python
class TenantMiddleware:
    """Extracts tenant context from requests."""

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Extract tenant context from path params, query params, or headers
        tenant_context = self._extract_tenant_context(request)

        # Set tenant context variables
        TenantContext.set_context(**tenant_context)

        # Add to request state
        request.state.tenant_context = tenant_context

        # Process request
        response = await call_next(request)

        # Clear context
        TenantContext.clear_context()

        return response

class TenantValidationMiddleware:
    """Validates tenant access for authenticated users."""

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Skip for exempt paths/methods
        # Validate tenant access
        # Return 403 if access denied
```

### Tenant Validation Service (`app/application/tenant_validation.py`)

```python
class TenantValidationService:
    """Validates tenant access and memberships."""

    async def validate_user_in_district(
        self, user_sub: str, district_id: uuid.UUID, required_role: Role | None = None
    ) -> bool

    async def validate_user_in_congregation(
        self, user_sub: str, congregation_id: uuid.UUID, required_role: Role | None = None
    ) -> bool

    async def validate_user_in_tenant(
        self, user_sub: str, tenant_id: uuid.UUID, tenant_type: str, required_role: Role | None = None
    ) -> bool

    async def validate_cross_tenant_access(
        self, user_sub: str, resource_tenant_id: uuid.UUID, resource_tenant_type: str,
        access_tenant_id: uuid.UUID | None = None, access_tenant_type: str | None = None
    ) -> bool

    async def get_user_districts(self, user_sub: str) -> list[uuid.UUID]
    async def get_user_congregations(self, user_sub: str, district_id: uuid.UUID | None = None) -> list[uuid.UUID]
    async def get_tenant_district(self, tenant_id: uuid.UUID, tenant_type: str) -> uuid.UUID | None
```

### RLS Policies (`app/adapters/db/migrations/rls_policies.py`)

PostgreSQL Row-Level Security policies for tenant-specific tables:

```sql
-- Enable RLS on a table
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Create policy for read access
CREATE POLICY events_tenant_isolation_policy ON events
    USING (
        -- User is superadmin
        (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
        OR
        -- Event belongs to a congregation user has access to
        (EXISTS (
            SELECT 1 FROM memberships m
            WHERE m.user_sub = current_setting('app.current_user_sub')
            AND m.scope_type = 'congregation'
            AND m.scope_id = events.congregation_id
        ))
        OR
        -- Event belongs to a district user has access to
        (EXISTS (
            SELECT 1 FROM memberships m
            WHERE m.user_sub = current_setting('app.current_user_sub')
            AND m.scope_type = 'district'
            AND m.scope_id = events.district_id
        ))
    );

-- Create policy for write access
CREATE POLICY events_write_policy ON events
    FOR INSERT OR UPDATE
    USING (
        -- User is superadmin
        (EXISTS (SELECT 1 FROM users WHERE sub = current_setting('app.current_user_sub') AND is_superadmin = true))
        OR
        -- User has write role in the event's congregation
        (EXISTS (
            SELECT 1 FROM memberships m
            WHERE m.user_sub = current_setting('app.current_user_sub')
            AND m.scope_type = 'congregation'
            AND m.scope_id = NEW.congregation_id
            AND m.role IN ('PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
        ))
    );
```

Tables added after the baseline revision `0014` receive their policies in
dedicated migrations (e.g. `0022` for `external_event_candidates` and
`leader_unavailabilities`) — `RLS_POLICIES` must not reference tables that do
not exist yet when `0014` runs.

### Verifying RLS against PostgreSQL

`services/backend/tests/integration/test_rls_postgres.py` runs as the
NOBYPASSRLS application role against a freshly migrated database (CI job
`backend-tests`). It fails when a table with a tenant key (`district_id`,
`congregation_id`, `leader_id`, `planning_slot_id`) has no RLS, unless the
table is listed with a justification in `RLS_EXEMPT_TABLES`. Locally:

```bash
cd services/backend
DATABASE_URL=postgresql+asyncpg://nak:changeme@localhost:5432/nak_rls \
  APP_DB_PASSWORD=local-only uv run alembic upgrade head
RLS_TEST_DATABASE_URL=postgresql://nak:changeme@localhost:5432/nak_rls \
  RLS_TEST_APP_PASSWORD=local-only uv run pytest tests/integration/test_rls_postgres.py \
  tests/integration/test_tenant_isolation_api.py tests/performance/test_rls_overhead.py
```

`test_tenant_isolation_api.py` covers the same boundary end to end through the
HTTP API: middleware, token verification (only the OIDC call is mocked),
membership loading, role guards and repositories on the application role. It
checks CRUD within the own district, refused access to foreign districts,
foreign rows being invisible even under the own district path, and the
`ACCESS_DENIED` audit entry.

## Integration

### FastAPI Integration (`app/main.py`)

```python
from app.adapters.api.middleware.tenant import TenantMiddleware, TenantValidationMiddleware
from app.tenant import TenantContext

# Add middleware (order matters!)
# TenantMiddleware should run before TenantValidationMiddleware
app.add_middleware(
    TenantMiddleware,
    exempt_paths={"/api/health", "/api/v1/auth"},
    exempt_methods={"OPTIONS"},
)
app.add_middleware(
    TenantValidationMiddleware,
    exempt_paths={"/api/health", "/api/v1/auth"},
    exempt_methods={"GET", "HEAD", "OPTIONS"},
)
```

### Setting Tenant Context

Tenant context can be set from various sources:

1. **Path Parameters**: `/api/v1/districts/{district_id}/events`
2. **Query Parameters**: `/api/v1/events?district_id=...`
3. **Headers**: `X-District-ID`, `X-Congregation-ID`
4. **Manual**: `TenantContext.set_context(...)`

### Using Tenant Context in Services

```python
from app.tenant import TenantContext

class EventService:
    async def get_events(self, session: AsyncSession) -> list[Event]:
        # Get current tenant context
        district_id = TenantContext.get_district()
        congregation_id = TenantContext.get_congregation()
        user_sub = TenantContext.get_user_sub()

        # Use context in queries
        query = select(EventORM)

        if district_id:
            query = query.where(EventORM.district_id == district_id)
        elif congregation_id:
            query = query.where(EventORM.congregation_id == congregation_id)

        # Execute query
        result = await session.execute(query)
        return result.scalars().all()
```

### Validating Tenant Access

```python
from app.application.tenant_validation import TenantValidationService

class EventService:
    async def create_event(
        self, session: AsyncSession, event_data: EventCreate, user_sub: str
    ) -> Event:
        # Validate user has access to the district
        validator = TenantValidationService(session)
        await validator.validate_user_in_district(
            user_sub=user_sub,
            district_id=event_data.district_id,
            required_role=Role.PLANNER,
        )

        # Create event
        event = EventORM(**event_data.dict())
        session.add(event)
        await session.commit()
        return event
```

## Tenant Hierarchy and Access Rules

### Access Matrix

| User Role | District Access | Congregation Access | Cross-Tenant Access |
|-----------|-----------------|---------------------|---------------------|
| VIEWER | Read-only | Read-only in assigned congregations | No |
| PLANNER | Read/Write | Read/Write in assigned congregations | No |
| CONGREGATION_ADMIN | Read/Write | Full access in assigned congregations | No |
| DISTRICT_ADMIN | Full access | Full access in all congregations | Yes (to congregations in district) |
| SUPERADMIN | Full access | Full access | Yes (all tenants) |

### Cross-Tenant Access Rules

1. **District Admin → Congregation**: Can access all congregations in their district
2. **Superadmin → Any Tenant**: Can access all districts and congregations
3. **Regular User → Same Tenant**: Can access their own district/congregation
4. **Regular User → Different Tenant**: Access denied

## Database-Level Security (RLS)

### PostgreSQL RLS Setup

RLS policies are applied to the following tables:

- `events` - Events belong to congregations and districts
- `service_assignments` - Assignments belong to congregations
- `leaders` - Leaders belong to congregations
- `invitations` - Invitations belong to congregations
- `calendar_integrations` - Integrations belong to congregations
- `memberships` - Memberships are sensitive (only admins can see)

### Setting RLS Context

The RLS identity is a per-transaction GUC. `app/adapters/db/session.py`
(`_set_tenant_gucs`) sets it at the beginning of every transaction from the
`TenantContext`:

```sql
SELECT set_config('app.current_user_sub', :sub, true);   -- verified subject only
SELECT set_config('app.is_system_worker', 'true', true);  -- Celery tasks
```

Only a **verified** identity may reach `app.current_user_sub`:

- `TenantMiddleware` stores the subject in `TenantContext` only when a user was
  authenticated earlier in the stack (`request.state.user`). The subject it
  decodes from the Bearer token without verification is kept in
  `request.state.tenant_context` and used for nothing but the validation
  pre-check. Before this rule, a forged token let public endpoints (which never
  verify a token) run their queries with any chosen RLS identity.
- `TenantValidationMiddleware` sets the claimed subject explicitly on its own,
  short-lived session to read that subject's memberships.
- The route dependency (`get_current_user_with_memberships`) verifies the token
  and then sets the verified subject and roles for the rest of the request.

## Performance

Measured against PostgreSQL 16 with five districts (6,500 planning slots,
3,250 assignments), the application role `nak_app` versus the table owner
(RLS bypassed). Test: `services/backend/tests/performance/test_rls_overhead.py`.

| Query (p95, one district) | Owner (no RLS) | `nak_app` (RLS) | Guard |
|---|---|---|---|
| Planning slots of a district, 3 months (1,300 rows) | ~40–105 ms | ~40–120 ms | 250 ms |
| Assignments for those slots (650 rows) | ~5 ms | ~7 ms | 100 ms |
| `TenantValidationService.validate_user_in_district` | – | ~2–5 ms | 25 ms |

- RLS adds no measurable cost to the slot query: the membership subqueries are
  hashed and evaluated once per query. The spread of that query comes from
  transferring 1,300 wide rows and is the same without RLS.
- **Finding (fixed by migration `0024`):** `service_assignments` had no index
  besides its primary key. The assignment lookup of every matrix request
  (`planning_slot_id = ANY(...)`, `event_id` as fallback) scanned the
  assignments of all districts; depending on table statistics the RLS plan
  took ~240 ms server-side for one district. With indexes on
  `planning_slot_id`, `event_id` and `leader_id` it takes ~7 ms. The indexes
  also serve the cascading foreign keys when slots or leaders are deleted.
- The guards catch order-of-magnitude regressions (unhashed per-row membership
  checks, missing indexes) and leave headroom for shared CI runners.
- The whole matrix endpoint (50 congregations, 3 months) measured ~230 ms p95
  under RLS before the indexes (`docs/performance-baseline.md`, NFR work
  package).

## Security Features

### Defense in Depth

1. **Application Layer**: Middleware extracts and validates tenant context
2. **Service Layer**: Services validate tenant access before operations
3. **Database Layer**: RLS policies enforce tenant isolation at query time

### Cross-Tenant Protection

- Users cannot access data from other tenants
- District admins can only access congregations in their district
- Superadmins have full access
- All access is logged (via audit logging)

### Hierarchical Access

- District admins can access all congregations in their district
- Congregation admins can only access their own congregation
- Planners can only access congregations they have permissions for

### Fail-Secure Behavior

- If tenant context cannot be determined, access is denied
- If validation fails, access is denied
- RLS policies default to denying access

## Testing

### Unit Tests

```bash
# Run tenant validation tests
pytest tests/unit/test_tenant_validation.py -v
```

### Manual Testing

1. **Test tenant isolation:**

   ```bash
   # Get token for user in district 1
   TOKEN=$(get_token_for_user_in_district_1)

   # Try to access district 2's events
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/districts/2/events
   # Should return 403 Forbidden
   ```

2. **Test cross-tenant access:**

   ```bash
   # Get token for district admin
   TOKEN=$(get_district_admin_token)

   # Try to access congregation in their district
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/congregations/1/events
   # Should return 200 OK (if congregation is in their district)

   # Try to access congregation in another district
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/congregations/2/events
   # Should return 403 Forbidden
   ```

3. **Test superadmin access:**

   ```bash
   # Get token for superadmin
   TOKEN=$(get_superadmin_token)

   # Try to access any district/congregation
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/districts/1/events
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/congregations/1/events
   # Both should return 200 OK
   ```

## Monitoring

Every request rejected with HTTP 403, whether by `TenantValidationMiddleware`
or by a role guard in a router, leaves two signals:

1. **Audit entry** with `action = ACCESS_DENIED`, `status = FAILED`, the probed
   `district_id`/`congregation_id` and the route in `extra_metadata`. Reads are
   included; a rejected GET of another tenant's data is the typical probe.
   Requests rejected before authentication carry the unverified subject as
   `extra_metadata.claimed_sub`, never as `user_sub`. District admins of the
   probed district can read these entries (audit RLS policy).
2. **Metric** `nak.access.denied` (OpenTelemetry counter, exported when
   `OTEL_ENABLED=true`) with the bounded attributes `http.request.method` and
   `http.route` (route template, UUIDs masked; no user or tenant identifiers).

### Alerting

Example rules for a Prometheus-compatible backend (the OTLP exporter turns
`nak.access.denied` into `nak_access_denied_total`):

```yaml
groups:
  - name: tenant-isolation
    rules:
      - alert: TenantProbing
        # Many denials on one route: scripted access to foreign tenants.
        expr: sum by (http_route) (increase(nak_access_denied_total[5m])) > 20
        labels: {severity: warning}
      - alert: AccessDeniedSpike
        # Sudden rise overall: broken role assignment or attack.
        expr: sum(rate(nak_access_denied_total[5m])) > 3 * sum(rate(nak_access_denied_total[1h] offset 1d))
        for: 10m
        labels: {severity: warning}
```

To find the subject behind an alert, query the audit log:

```sql
SELECT timestamp, coalesce(user_sub, extra_metadata->>'claimed_sub') AS subject,
       district_id, extra_metadata->>'path' AS path
FROM audit_logs
WHERE action = 'ACCESS_DENIED' AND timestamp > now() - interval '1 hour'
ORDER BY timestamp DESC;
```

### Dashboard

Recommended panels: denials per route (stacked, 5-minute rate), top subjects
from the audit query above, and the ratio of denied to all requests
(`http.server.request.duration` count from the FastAPI instrumentation).

## Rollback Plan

RLS is the last line of defence; disable it only to restore service, never
as a permanent fix, and only for the table that misbehaves.

1. **Identify** the table from the error (`new row violates row-level security
   policy for table …`) or the slow query.
2. **Emergency switch for one table**, as the migration owner:

   ```sql
   ALTER TABLE <table> DISABLE ROW LEVEL SECURITY;  -- policies stay defined
   ```

   Application guards (`require_role_in_district`, tenant validation) keep
   protecting the API meanwhile. Record the change in the incident log.
3. **Fix forward** with a migration that corrects the policy, then
   `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;` (and `FORCE` where it was
   set before), verified by `tests/integration/test_rls_postgres.py`.
4. **Schema rollback** only when a policy migration itself is faulty:
   `alembic downgrade <revision>`. Every RLS migration (`0014`, `0022`) has a
   downgrade that drops exactly its own policies and disables RLS on its
   tables.

## Compliance

This implementation addresses the following security and compliance requirements:

- **OWASP ASVS**: V12.3 (Tenant Isolation)
- **OWASP Top 10**: A01:2021 (Broken Access Control)
- **CIS Controls**: 14.6 (Data Integrity)
- **GDPR**: Article 25 (Data Protection by Design)
- **ISO 27001**: A.9.1 (Access Control Policy)

## Migration

### Database Migration

A new database migration is required to:

1. Enable RLS on tenant-specific tables
2. Create RLS policies for each table

```bash
# Generate migration
alembic revision --autogenerate -m "Enable RLS for tenant isolation"

# Apply migration
alembic upgrade head
```

### Application Changes

1. **Update Repositories**: Ensure all repositories respect tenant context
2. **Update Services**: Add tenant validation to all service methods
3. **Update Routers**: Ensure tenant context is passed to services
4. **Add Middleware**: Configure tenant middleware in main.py

## Troubleshooting

### Common Issues

1. **403 Forbidden on all requests**

   - Check that tenant context is being extracted correctly
   - Verify middleware is configured and running
   - Check that user has appropriate memberships

2. **RLS policies blocking all queries**

   - Verify PostgreSQL settings are being set
   - Check RLS policy definitions
   - Test with RLS temporarily disabled

3. **Cross-tenant access not working**

   - Verify tenant hierarchy (congregation belongs to district)
   - Check user's role in the access tenant
   - Verify cross-tenant validation logic

4. **Performance issues**

   - Check for N+1 queries in tenant validation
   - Consider caching tenant memberships
   - Review RLS policy complexity

### Debug Mode

Enable debug logging for tenant operations:

```python
import logging
logging.getLogger('app.tenant').setLevel(logging.DEBUG)
logging.getLogger('app.application.tenant_validation').setLevel(logging.DEBUG)
logging.getLogger('app.adapters.api.middleware.tenant').setLevel(logging.DEBUG)
```

## References

- [OWASP Multi-Tenant Security](https://cheatsheetseries.owasp.org/cheatsheets/Multitenancy_Cheat_Sheet.html)
- [PostgreSQL Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Security Analysis: SEC-020](../../security-analysis.md#sec-020-insufficient-tenant-isolation)
- [Security Analysis: SEC-021](../../security-analysis.md#sec-021-cross-tenant-data-access)
- [OpenSpec Design](../../openspec/changes/improve-tenant-isolation/design.md)
