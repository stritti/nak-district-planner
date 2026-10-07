## MODIFIED Requirements

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

### Requirement: Backend accepts the CSRF token only from the request header
The backend SHALL validate state-changing requests (POST, PUT, PATCH, DELETE) only against the token in the configured CSRF request header. The CSRF cookie SHALL NOT be accepted as a fallback, because browsers attach it to cross-site requests automatically. SameSite remains an additional, not a replacing, control.

#### Scenario: Cookie without header
- **WHEN** a state-changing request carries a valid CSRF cookie but no CSRF header, or an empty header
- **THEN** the backend responds with 403 "CSRF validation failed"

#### Scenario: Tampered header
- **WHEN** the CSRF header contains a token with an invalid signature
- **THEN** the backend responds with 403

#### Scenario: Concurrent rotation
- **WHEN** parallel responses rotate the CSRF cookie and a request sends a previously issued, still unexpired signed token in the header
- **THEN** the request is accepted

### Requirement: Logout clears the server-held refresh credential
The backend SHALL delete the refresh cookie on logout/revocation even if the upstream provider cannot be reached. Upstream revocation failures SHALL be logged for operational visibility.
