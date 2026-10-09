# oidc-authentication Specification

## Purpose

Defines provider-agnostic OIDC authentication (Keycloak, Authentik or any compliant IdP configured via `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`): backend token validation through `OIDCAdapter`, the backend token proxy that keeps refresh credentials in an HttpOnly cookie, and the SPA's memory-only session handling with PKCE. Consolidates `phase4b-oidc-auth-idp-agnostic`, `harden-oidc-token-validation` and `server-held-oidc-refresh-token`.

## Requirements

### Requirement: Provider-agnostic OIDC configuration
The backend SHALL derive all provider endpoints from the discovery document at `OIDC_DISCOVERY_URL` and SHALL refuse to start in production (`APP_ENV=production`) with a placeholder discovery URL, client ID or client secret. `GET /api/v1/auth/oidc/discovery` SHALL return the discovery document with the client ID and SHALL replace an upstream `revocation_endpoint` by the backend proxy `/api/v1/auth/oidc/revoke`.

#### Scenario: Placeholder configuration
- **WHEN** the backend starts in production with `OIDC_CLIENT_SECRET` still set to a placeholder
- **THEN** settings validation fails and the application does not start

### Requirement: JWT signature and claim validation
JWT access tokens SHALL be validated against the provider JWKS (RS256 by default) with issuer, expiry (120 s leeway) and audience checks. JWKS SHALL be cached for one hour, refreshed once when a `kid` is unknown, and a stale cache MAY be used when the JWKS endpoint is temporarily unreachable.

#### Scenario: Key rotation
- **WHEN** a token references a `kid` not present in the cached JWKS
- **THEN** the adapter refreshes the JWKS once and validates against the new key

### Requirement: JWT validation fails closed
The backend SHALL classify compact three-segment tokens as JWT-like and SHALL validate them exclusively through cryptographic JWT validation. A JWT validation error MUST NOT trigger UserInfo or Introspection fallback.

#### Scenario: JWT has invalid audience
- **WHEN** a JWT-like access token has an audience that does not match the configured client/audience
- **THEN** authentication fails
- **AND** UserInfo and Introspection are not called as fallback validators

#### Scenario: JWT is expired or has invalid issuer/signature
- **WHEN** cryptographic JWT validation fails for expiration, issuer, signing key or signature reasons
- **THEN** authentication fails closed
- **AND** the token is not reinterpreted as opaque

### Requirement: Opaque token validation is scoped to this application
The backend MAY accept non-JWT (opaque) access tokens, but MUST validate them through RFC 7662 Introspection before authentication succeeds. The introspection response MUST contain `active` as the boolean `true`, a non-empty `sub` and a `client_id` exactly matching the configured OIDC client. A valid UserInfo response alone MUST NOT authenticate a token. Any present issuer, audience or authorized-party claim MUST also pass normal security claim checks. UserInfo MAY enrich a successfully introspected identity, but its subject MUST agree with the introspected subject; identity and security claim mismatches MUST fail closed.

#### Scenario: Valid UserInfo response without introspection
- **WHEN** an opaque token receives a successful UserInfo response but introspection is unavailable
- **THEN** authentication fails

#### Scenario: Introspection belongs to another client
- **WHEN** introspection reports an active token with a missing or different `client_id`
- **THEN** authentication fails before UserInfo is called

#### Scenario: Introspection active flag is not boolean true
- **WHEN** introspection returns `active: "false"` or any other non-boolean-true value
- **THEN** authentication fails

#### Scenario: Resource audience mismatches but authorized party matches
- **WHEN** an opaque introspection result contains an `aud` excluding this application
- **AND** `azp` equals the configured client
- **THEN** authentication fails because `azp` does not replace the resource audience

#### Scenario: UserInfo returns a mismatching security claim or subject
- **WHEN** a client-bound, active opaque token is confirmed by introspection
- **AND** UserInfo returns a different subject or a mismatching issuer, client or audience claim
- **THEN** authentication fails even though introspection was successful

#### Scenario: Valid client-bound introspection with optional UserInfo
- **WHEN** introspection reports a matching client and an active token with a subject
- **THEN** authentication succeeds whether UserInfo supplies matching profile data or is unavailable
- **AND** introspection remains authoritative for security claims

### Requirement: Provider refresh credentials are not exposed to browser JavaScript
The backend SHALL retain provider refresh tokens in a Secure, HttpOnly, SameSite cookie and SHALL NOT return the provider refresh credential or a credential-like placeholder in JSON responses to the SPA.

#### Scenario: Authorization code exchange returns a refresh token
- **WHEN** the OIDC provider returns an access token and a refresh token
- **THEN** the backend stores the refresh token in an HttpOnly cookie
- **AND** the JSON response contains no provider refresh credential
- **AND** the frontend receives only `refresh_session: true` as non-secret session metadata

#### Scenario: Access token is refreshed
- **WHEN** the SPA requests a refresh grant
- **THEN** the request body contains only the refresh grant type
- **AND** the backend reads the provider refresh token from the HttpOnly cookie
- **AND** stores a rotated refresh token back into the HttpOnly cookie
- **AND** returns no provider refresh credential to JavaScript

#### Scenario: Refresh cookie is absent
- **WHEN** a refresh grant is requested without the server-held refresh cookie
- **THEN** the backend rejects the request with HTTP 401

#### Scenario: Provider returns invalid successful JSON
- **WHEN** the provider responds successfully but the token response cannot be parsed as valid JSON
- **THEN** the backend returns HTTP 502 instead of exposing an internal server error

### Requirement: Frontend auth credentials and refresh coordination are memory-scoped
The SPA SHALL NOT persist access, ID, provider refresh, or refresh-coordination token state in localStorage or sessionStorage. Cross-tab refresh coordination SHALL use ephemeral Web Locks and BroadcastChannel state. SessionStorage MAY contain only the short-lived PKCE verifier and OAuth state required during an authorization-code login.

#### Scenario: Browser storage is inspected after authentication or refresh
- **WHEN** the user is authenticated or refresh coordination has occurred
- **THEN** no access token, ID token, provider refresh token, refresh receipt, or rotation chain is stored in localStorage or sessionStorage

#### Scenario: Multiple tabs refresh concurrently
- **WHEN** multiple tabs attempt to refresh the same server-held session
- **THEN** Web Locks serialize the cookie-backed provider refresh operation
- **AND** BroadcastChannel distributes only the short-lived in-memory session result and a non-secret coordination identifier
- **AND** no provider refresh credential is exposed to either mechanism

#### Scenario: Web Locks are unavailable
- **WHEN** the browser cannot safely serialize refresh operations across tabs
- **THEN** the SPA does not issue a potentially concurrent provider refresh
- **AND** retains a still-valid access session only until expiry
- **AND** fails closed when that session expires

### Requirement: Browser session can be restored from the server-held refresh session
The SPA SHALL be able to rebuild its memory-only access session after a page reload by using the HttpOnly refresh cookie without reading that credential in JavaScript.

#### Scenario: Reload with a valid refresh cookie
- **WHEN** no in-memory access token exists after application startup
- **AND** the backend refresh-session cookie is still valid
- **THEN** the SPA bootstraps OIDC discovery so the current CSRF cookie is available
- **AND** requests a refresh grant without a browser-held refresh credential
- **AND** installs the returned access session only after a valid token response and user identity are available

#### Scenario: Reload without a usable refresh session
- **WHEN** discovery bootstrap fails, the cookie is missing or expired, the provider response is malformed, or the refresh request fails
- **THEN** no partial authenticated session is installed

### Requirement: Protected navigation waits for session restoration
A route that requires authentication SHALL NOT decide that a user is logged out until a possible server-held refresh session has been restored or rejected.

#### Scenario: Direct reload of a protected route with a valid refresh session
- **WHEN** the browser loads a protected route with no in-memory access token
- **AND** a valid server-held refresh session exists
- **THEN** the route guard waits for the deduplicated session restore
- **AND** refreshes current-user authorization facts after the bearer is restored
- **AND** allows the requested protected navigation without an intermediate redirect to `/login`

#### Scenario: Protected route restore fails
- **WHEN** a protected route is loaded without an in-memory access token
- **AND** the server-held session cannot be restored
- **THEN** the route guard fails closed and redirects to `/login`
- **AND** does not install partial authentication or privileged authorization facts

### Requirement: Cookie-backed OIDC state changes remain CSRF protected
Every browser POST that uses or mutates the server-held refresh session SHALL submit the current double-submit CSRF token in the configured request header.

#### Scenario: Token exchange, refresh, restore, or revoke is submitted
- **WHEN** the SPA sends a state-changing OIDC request to the backend
- **THEN** it reads the current CSRF cookie at request time
- **AND** sends that value in the CSRF request header
- **AND** does not rely on a value captured before server-side CSRF rotation

### Requirement: Logout clears the server-held refresh credential
The backend SHALL delete the refresh cookie on logout/revocation even if the upstream provider cannot be reached. Upstream revocation failures SHALL be logged for operational visibility.

#### Scenario: Provider revocation fails
- **WHEN** `POST /api/v1/auth/oidc/revoke` is called and the provider revocation endpoint errors or is unreachable
- **THEN** the backend logs a warning without the token value, still deletes the refresh cookie and responds with 204

### Requirement: PKCE authorization code flow in the SPA
The SPA SHALL start login with an authorization request containing `state` and a PKCE `code_challenge`, SHALL verify `state` on callback, and SHALL exchange the code through `POST /api/v1/auth/oidc/token` with the `code_verifier`. The client secret SHALL stay in the backend.

#### Scenario: State mismatch on callback
- **WHEN** the callback `state` differs from the stored value
- **THEN** the code is not exchanged and no session is installed
