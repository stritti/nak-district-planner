## ADDED Requirements

### Requirement: OIDC Discovery and Configuration
The system SHALL support any OpenID Connect provider via dynamic discovery. The backend SHALL fetch and parse the provider's `.well-known/openid-configuration` endpoint to discover token, authorization, and JWKS endpoints.

#### Scenario: OIDC discovery succeeds
- **WHEN** backend initializes with `OIDC_DISCOVERY_URL` pointing to a valid OIDC provider
- **THEN** system fetches the discovery document and extracts `token_endpoint`, `authorization_endpoint`, `jwks_uri`

#### Scenario: OIDC discovery fails
- **WHEN** `OIDC_DISCOVERY_URL` returns 404 or invalid JSON
- **THEN** system logs error and fails to start (catch at startup, not runtime)

#### Scenario: Works with Keycloak discovery
- **WHEN** `OIDC_DISCOVERY_URL` points to Keycloak realm (e.g., `https://auth.5tritti.de/realms/nak-planner/.well-known/openid-configuration`)
- **THEN** all endpoints are correctly discovered and token validation works

#### Scenario: Works with Authentik discovery
- **WHEN** `OIDC_DISCOVERY_URL` points to Authentik application (e.g., `https://authentik.internal/application/o/nak-planner/.well-known/openid-configuration`)
- **THEN** all endpoints are correctly discovered and token validation works

### Requirement: JWT Validation via JWKS (Provider-Agnostic)
The system SHALL validate Bearer tokens against the OIDC provider's JWKS endpoint. Validation SHALL check signature, issuer, expiration, and audience claims without making per-request calls to the provider (via JWKS caching with 1-hour TTL).

#### Scenario: Valid token accepted
- **WHEN** request contains `Authorization: Bearer <valid-jwt>`
- **THEN** backend decodes token, verifies signature via JWKS, extracts claims (`sub`, `email`, `iss`)

#### Scenario: Expired token rejected
- **WHEN** request contains `Authorization: Bearer <expired-jwt>`
- **THEN** backend returns 401 Unauthorized with message "Token expired"

#### Scenario: Invalid signature rejected
- **WHEN** request contains `Authorization: Bearer <tampered-token>`
- **THEN** backend returns 401 Unauthorized with message "Invalid token signature"

#### Scenario: Issuer claim mismatch
- **WHEN** token issuer does not match `OIDC_ISSUER` (derived from discovery or configured)
- **THEN** backend returns 401 Unauthorized with message "Invalid token issuer"

#### Scenario: JWKS cache refreshes after TTL
- **WHEN** more than 1 hour has passed since last JWKS fetch
- **THEN** next request triggers fresh JWKS fetch from provider's `jwks_uri`

#### Scenario: JWKS fetch failure with fallback
- **WHEN** JWKS endpoint is unreachable but token is in cache
- **THEN** system uses cached JWKS and validates token
- **WHEN** JWKS endpoint is unreachable AND cache is expired
- **THEN** system returns 503 Service Unavailable (cannot validate)

### Requirement: OIDC Adapter for Token Validation
The system SHALL provide an `OIDCAdapter` that encapsulates all OIDC provider interactions. The adapter SHALL be agnostic to the specific provider and use only standard OIDC endpoints.

#### Scenario: Adapter initialization with discovery
- **WHEN** `OIDCAdapter` is initialized with `OIDC_DISCOVERY_URL` and `OIDC_CLIENT_ID`
- **THEN** adapter performs discovery, fetches JWKS, and is ready to validate tokens

#### Scenario: Token validation uses standard OIDC claims
- **WHEN** adapter validates a token
- **THEN** it extracts `sub` (subject/user ID), `email`, `iat` (issued at), `exp` (expiration) — all standard OIDC claims
- **AND** validation does NOT rely on provider-specific claims (no Keycloak-specific `realm_access`, etc.)

#### Scenario: Adapter handles JWKS key rotation
- **WHEN** OIDC provider rotates JWKS keys
- **THEN** adapter detects `kid` mismatch, refreshes JWKS, and validates token with new keys

### Requirement: Standard OIDC Scopes
The system SHALL request only standard OIDC scopes: `openid`, `profile`, `email`. These scopes MUST be configurable via `OIDC_SCOPES` environment variable (default: `openid profile email`).

#### Scenario: Authorization request includes configured scopes
- **WHEN** frontend redirects to provider's authorization endpoint
- **THEN** request includes scopes from `OIDC_SCOPES`

#### Scenario: ID token includes scope-requested claims
- **WHEN** user authorizes the application with scopes `openid profile email`
- **THEN** returned ID token contains `sub`, `email`, `preferred_username` (from `profile` scope)

### Requirement: Multiple IDPs via Configuration
The system SHALL support deployment against different OIDC providers without code changes. Provider selection is determined solely by environment variables: `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`.

#### Scenario: Swap provider via environment variables
- **WHEN** deployment changes `OIDC_DISCOVERY_URL` from Keycloak to Authentik (different URL, same `CLIENT_ID`/`SECRET`)
- **THEN** system validates tokens from Authentik without code/config changes
- **AND** same backend binary works for both deployments

#### Scenario: Provider-specific configuration isolation
- **WHEN** provider A uses 30-minute token expiry and provider B uses 60 minutes
- **THEN** system correctly validates and refreshes tokens for each (respects provider's `expires_in` claim)

