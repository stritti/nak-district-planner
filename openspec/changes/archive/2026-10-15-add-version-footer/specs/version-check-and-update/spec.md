## ADDED Requirements

### Requirement: Running versions visible without sign-in
The frontend SHALL show the versions of the running frontend build and of the backend in an unobtrusive footer on every page, including the login page, without requiring authentication.

#### Scenario: Both versions are shown while signed out
- **WHEN** an unauthenticated visitor opens any page
- **THEN** the footer shows `Frontend v<frontend version> · Backend v<backend version>`
- **THEN** the backend version is taken from the public `GET /api/health` response and the frontend version from the build

#### Scenario: Backend version unavailable
- **WHEN** the backend is unreachable or its response carries no version
- **THEN** the footer shows `–` as the backend version and the page keeps working

#### Scenario: Degraded backend
- **WHEN** `GET /api/health` answers 503
- **THEN** the footer still shows the version from the response body

#### Scenario: Version lookup never affects the session
- **WHEN** the version lookup fails
- **THEN** no token refresh, logout or redirect is triggered and an in-flight login is left untouched
