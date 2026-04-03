## ADDED Requirements

### Requirement: Keycloak Login Redirect
The frontend SHALL redirect unauthenticated users to Keycloak's login page. After successful login, Keycloak redirects back to the frontend with an authorization code.

#### Scenario: Unauthenticated user visits frontend
- **WHEN** user accesses `https://planner.5tritti.de/` without JWT in localStorage
- **THEN** frontend detects missing token and redirects to `https://auth.5tritti.de/realms/{realm}/protocol/openid-connect/auth?client_id=...&redirect_uri=...&response_type=code`

#### Scenario: User logs in at Keycloak
- **WHEN** user enters credentials at Keycloak login page
- **THEN** Keycloak redirects to `https://planner.5tritti.de/auth/callback?code=...&session_state=...`

### Requirement: OAuth2 Callback Handler
The frontend SHALL implement a callback route that exchanges the authorization code for tokens.

#### Scenario: Callback receives authorization code
- **WHEN** user is redirected to `/auth/callback?code=xxx`
- **THEN** frontend extracts `code` parameter
- **AND** frontend exchanges code for tokens via Keycloak token endpoint

#### Scenario: Tokens stored in localStorage
- **WHEN** callback receives tokens from Keycloak
- **THEN** `access_token`, `refresh_token`, and token metadata stored in localStorage
- **AND** user is redirected to dashboard (`/dashboard` or `/matrix`)

#### Scenario: Invalid callback state
- **WHEN** callback receives invalid/missing code
- **THEN** frontend displays error message and redirects to login

### Requirement: Automatic Token Refresh
The system SHALL automatically refresh the access token before expiration to prevent mid-session logouts.

#### Scenario: Token expires during session
- **WHEN** `access_token` is about to expire (within 5 minutes)
- **THEN** frontend uses `refresh_token` to obtain new `access_token` from Keycloak
- **AND** new token is stored in localStorage

#### Scenario: Refresh fails (e.g., refresh token expired)
- **WHEN** token refresh fails (Keycloak returns 400/401)
- **THEN** frontend clears localStorage
- **AND** redirects user to login page with message "Session expired, please log in again"

### Requirement: Logout Endpoint
The frontend SHALL provide a logout action that clears tokens and logs out from Keycloak.

#### Scenario: User clicks logout button
- **WHEN** user clicks logout
- **THEN** frontend clears localStorage tokens
- **AND** redirects to `https://auth.5tritti.de/realms/{realm}/protocol/openid-connect/logout?redirect_uri=https://planner.5tritti.de/`
- **AND** Keycloak invalidates session
- **AND** user is redirected to login page

#### Scenario: Token cleared on logout
- **WHEN** user logs out
- **THEN** localStorage no longer contains `access_token` or `refresh_token`
