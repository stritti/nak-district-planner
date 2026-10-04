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

### Requirement: Frontend auth credentials are memory-scoped
The SPA SHALL NOT persist its auth token state in localStorage. Temporary refresh coordination receipts MAY use sessionStorage for the lifetime of one tab and SHALL NOT contain a provider refresh credential.

#### Scenario: Browser localStorage is inspected
- **WHEN** the user is authenticated or refresh coordination has occurred
- **THEN** no access, ID, or provider refresh token is stored in localStorage

### Requirement: Browser session can be restored from the server-held refresh session
The SPA SHALL be able to rebuild its memory-only access session after a page reload by using the HttpOnly refresh cookie without reading that credential in JavaScript.

#### Scenario: Reload with a valid refresh cookie
- **WHEN** no in-memory access token exists after application startup
- **AND** the backend refresh-session cookie is still valid
- **THEN** the SPA requests a refresh grant without a browser-held refresh credential
- **AND** installs the returned access session only after a valid token response and user identity are available

#### Scenario: Reload without a usable refresh session
- **WHEN** the cookie is missing, expired, the provider response is malformed, or the refresh request fails
- **THEN** no partial authenticated session is installed

### Requirement: Logout clears the server-held refresh credential
The backend SHALL delete the refresh cookie on logout/revocation even if the upstream provider cannot be reached. Upstream revocation failures SHALL be logged for operational visibility.
