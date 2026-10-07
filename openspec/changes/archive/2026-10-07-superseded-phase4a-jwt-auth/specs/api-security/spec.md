## REMOVED Requirements

### Requirement: X-API-Key Header Authentication
The system previously required `X-API-Key` header for API authentication. This requirement is **removed**.

**Reason**: API-Key-based auth is not suitable for multi-tenant, multi-user systems. JWT-based auth provides user identity, expiration, and audit capabilities.

**Migration**: Replace all `X-API-Key` usages with `Authorization: Bearer <JWT>` header. Keycloak manages token issuance and refresh.

## ADDED Requirements

### Requirement: Bearer Token Authentication
All `/api/v1/` endpoints (except `/api/health`) SHALL require a valid Bearer token in the `Authorization` header.

#### Scenario: Valid JWT in Authorization header
- **WHEN** request includes `Authorization: Bearer <valid-jwt>`
- **THEN** endpoint processes request with authenticated user context

#### Scenario: Missing Authorization header
- **WHEN** request is made without Authorization header
- **THEN** endpoint returns 401 Unauthorized with message "Authorization header missing"

#### Scenario: Invalid token format
- **WHEN** request includes `Authorization: InvalidFormat <token>`
- **THEN** endpoint returns 401 Unauthorized with message "Invalid authorization format. Use 'Bearer <token>'"

#### Scenario: Health endpoint remains public
- **WHEN** request is made to `GET /api/health` without Authorization header
- **THEN** endpoint returns 200 OK (no authentication required)

### Requirement: All Authenticated Routes Use get_current_user()
All protected `/api/v1/` routes SHALL use the `get_current_user()` dependency to authenticate requests and extract user identity.

#### Scenario: Route with authenticated dependency
- **WHEN** route is defined with `Depends(get_current_user)`
- **THEN** only authenticated users with valid JWT can access the route
- **AND** route handler receives `User` object with `keycloak_sub`, `email`, etc.

#### Scenario: User context available in route handler
- **WHEN** authenticated request is processed
- **THEN** route handler can access user ID, email, and other user data from the `User` object
