## MODIFIED Requirements

### Requirement: Provider refresh credentials are not exposed to browser JavaScript
The backend SHALL retain provider refresh tokens in a Secure, HttpOnly, SameSite cookie and SHALL NOT return the provider refresh credential in JSON responses to the SPA.

#### Scenario: Authorization code exchange returns a refresh token
- **WHEN** the OIDC provider returns an access token and a refresh token
- **THEN** the backend stores the refresh token in an HttpOnly cookie
- **AND** the JSON response contains no provider refresh credential
- **AND** the frontend receives only a non-secret coordination marker

#### Scenario: Access token is refreshed
- **WHEN** the SPA requests a refresh
- **THEN** the backend reads the provider refresh token from the HttpOnly cookie
- **AND** ignores the coordination marker as a credential
- **AND** stores a rotated refresh token back into the HttpOnly cookie

#### Scenario: Refresh cookie is absent
- **WHEN** a refresh grant is requested without the server-held refresh cookie
- **THEN** the backend rejects the request with HTTP 401

### Requirement: Frontend auth credentials are memory-scoped
The SPA SHALL NOT persist its auth token state in localStorage. Temporary refresh coordination receipts MAY use sessionStorage for the lifetime of one tab.

#### Scenario: Browser localStorage is inspected
- **WHEN** the user is authenticated or refresh coordination has occurred
- **THEN** no access, ID, or provider refresh token is stored in localStorage

### Requirement: Logout clears the server-held refresh credential
The backend SHALL delete the refresh cookie on logout/revocation even if the upstream provider cannot be reached.