## ADDED Requirements

### Requirement: JWT Validation via Keycloak JWKS
The system SHALL validate Bearer tokens against Keycloak's JWKS endpoint. Token validation SHALL check signature, issuer, expiration, and audience without making per-request calls to Keycloak (via JWKS caching with 1-hour TTL).

#### Scenario: Valid token accepted
- **WHEN** request contains `Authorization: Bearer <valid-jwt>`
- **THEN** backend decodes token, verifies signature via JWKS, extracts `sub` (Keycloak user ID) and `email`

#### Scenario: Expired token rejected
- **WHEN** request contains `Authorization: Bearer <expired-jwt>`
- **THEN** backend returns 401 Unauthorized with message "Token expired"

#### Scenario: Invalid signature rejected
- **WHEN** request contains `Authorization: Bearer <tampered-token>`
- **THEN** backend returns 401 Unauthorized with message "Invalid token signature"

#### Scenario: Missing token rejected
- **WHEN** request has no Authorization header
- **THEN** backend returns 401 Unauthorized with message "Authorization header missing"

#### Scenario: JWKS cache refreshes after TTL
- **WHEN** more than 1 hour has passed since last JWKS fetch
- **THEN** next request triggers fresh JWKS fetch from Keycloak

### Requirement: Keycloak-Adapter for Token Validation
The system SHALL provide a `KeycloakAdapter` that:
- Fetches JWKS from `{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/.well-known/jwks.json`
- Caches JWKS for 1 hour
- Uses `python-jose` library to decode and verify JWT
- Extracts claim data without calling Keycloak API per request

#### Scenario: JWKS fetch on startup
- **WHEN** first token validation is requested
- **THEN** `KeycloakAdapter` fetches JWKS and caches it

#### Scenario: Cache hit for subsequent validations
- **WHEN** second token validation is requested within 1 hour
- **THEN** cached JWKS is used (no HTTP call to Keycloak)

#### Scenario: Cache invalidation after TTL
- **WHEN** 1 hour has elapsed since JWKS fetch
- **THEN** next validation triggers a new JWKS fetch

#### Scenario: JWKS fetch failure handling
- **WHEN** Keycloak JWKS endpoint is unreachable
- **THEN** `KeycloakAdapter` raises `KeycloakError` with descriptive message
