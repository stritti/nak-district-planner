## ADDED Requirements

### Requirement: OIDC Authorization Flow (Provider-Agnostic)
The frontend SHALL initiate a standard OIDC authorization code flow with any OIDC provider. The flow SHALL include PKCE (Proof Key for Code Exchange) for security, even though frontend is SPA.

#### Scenario: Generate authorization URL
- **WHEN** frontend initializes OIDC authentication
- **THEN** system generates authorization URL with `client_id`, `redirect_uri`, `scope`, `state`, `code_challenge` (PKCE)

#### Scenario: Redirect to provider login
- **WHEN** user clicks "Login"
- **THEN** browser is redirected to provider's `authorization_endpoint` (from discovery)

#### Scenario: User authorizes, provider redirects back
- **WHEN** user logs in and grants permission at provider
- **THEN** provider redirects back to `VITE_OIDC_REDIRECT_URI` with `code` and `state`

#### Scenario: State validation prevents CSRF
- **WHEN** callback receives `state` parameter
- **THEN** frontend verifies `state` matches the stored value (CSRF protection)

#### Scenario: Exchange code for tokens
- **WHEN** frontend receives valid `code` from provider
- **THEN** frontend exchanges code for ID token and access token using `code_verifier` (PKCE)

#### Scenario: Handle failed authorization
- **WHEN** provider redirects with `error=access_denied`
- **THEN** frontend shows user-friendly error and clears auth state

### Requirement: Token Storage and Refresh
The frontend SHALL securely store tokens and automatically refresh the access token before expiration.

#### Scenario: Store tokens in memory (not localStorage)
- **WHEN** tokens are obtained from provider
- **THEN** frontend stores ID token and access token in memory (not localStorage, for security)

#### Scenario: Auto-refresh before expiration
- **WHEN** access token will expire in < 5 minutes
- **THEN** frontend automatically refreshes using refresh token (if available)

#### Scenario: Refresh token endpoint discovery
- **WHEN** system needs to refresh token
- **THEN** uses provider's `token_endpoint` (from discovery) to obtain new access token

#### Scenario: Handle refresh failure
- **WHEN** refresh token is expired or revoked
- **THEN** frontend logs user out and redirects to login

#### Scenario: Logout clears tokens
- **WHEN** user clicks logout
- **THEN** frontend clears all tokens from memory

### Requirement: OIDC Configuration via Discovery
The frontend SHALL use OIDC discovery to obtain provider endpoints, not hardcoded URLs. Configuration is via environment variables only: `VITE_OIDC_DISCOVERY_URL`, `VITE_OIDC_CLIENT_ID`, `VITE_OIDC_REDIRECT_URI`.

#### Scenario: Fetch discovery document
- **WHEN** frontend app initializes
- **THEN** fetches provider's `.well-known/openid-configuration` and extracts `authorization_endpoint`, `token_endpoint`, `revocation_endpoint`

#### Scenario: Discovery document not found
- **WHEN** `VITE_OIDC_DISCOVERY_URL` returns 404
- **THEN** app shows error message "Cannot reach authentication provider" and does not load

#### Scenario: Works with any OIDC provider
- **WHEN** environment variable `VITE_OIDC_DISCOVERY_URL` is changed to different provider
- **THEN** frontend automatically uses new provider's endpoints without code changes

### Requirement: OIDC Composable for Vue 3
The frontend SHALL provide a reusable `useOIDC()` composable that encapsulates all OIDC logic (discovery, login, token handling, refresh).

#### Scenario: Composable provides login function
- **WHEN** component calls `const { login } = useOIDC()`
- **THEN** can call `login()` to initiate authorization flow

#### Scenario: Composable provides logout function
- **WHEN** user is authenticated and calls `logout()`
- **THEN** tokens are cleared and user is logged out

#### Scenario: Composable provides current token
- **WHEN** component calls `const { token } = useOIDC()`
- **THEN** can use token in API requests (always current, refreshed automatically)

#### Scenario: Composable provides user info
- **WHEN** user is authenticated, component calls `const { user } = useOIDC()`
- **THEN** returns object with `sub`, `email`, `preferred_username` from ID token

#### Scenario: Composable handles callback
- **WHEN** app is redirected to callback URL with `code`
- **THEN** composable automatically exchanges code for tokens and redirects to home page

### Requirement: Provider-Agnostic Frontend Configuration
The frontend SHALL NOT include provider-specific logic. All configuration is via environment variables.

#### Scenario: Same build, multiple providers
- **WHEN** same frontend build is deployed with different `VITE_OIDC_DISCOVERY_URL`
- **THEN** frontend works seamlessly with different providers (Keycloak, Authentik, etc.)

#### Scenario: OIDC configuration validation at startup
- **WHEN** frontend initializes
- **THEN** validates that `VITE_OIDC_DISCOVERY_URL` and `VITE_OIDC_CLIENT_ID` are set, fails gracefully if not

