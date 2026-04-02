## ADDED Requirements

### Requirement: Automatic User Creation on First Login
When a JWT is validated, the system SHALL check if a user with that Keycloak `sub` exists in the database. If not, it SHALL auto-create a user record with the JWT claims.

#### Scenario: User exists in database
- **WHEN** request contains valid JWT with known `sub`
- **THEN** system returns existing `User` object from database

#### Scenario: User does not exist (first login)
- **WHEN** request contains valid JWT with unknown `sub`
- **THEN** system creates new `User` record with `keycloak_sub`, `email`, `display_name` from JWT
- **AND** new user is stored in database
- **AND** next requests use the created user record

#### Scenario: User auto-creation sets correct fields
- **WHEN** new user is created from JWT
- **THEN** user record contains:
  - `keycloak_sub` = JWT `sub` claim
  - `email` = JWT `email` claim
  - `display_name` = JWT `name` or `preferred_username` claim (whichever present)
  - `is_active` = true
  - `created_at` = current timestamp

### Requirement: GET /auth/me Endpoint
The system SHALL provide an authenticated endpoint that returns the current user's profile.

#### Scenario: Authenticated user requests profile
- **WHEN** request is made to `GET /api/v1/auth/me` with valid JWT
- **THEN** system returns 200 with user object:
  ```json
  {
    "id": "uuid",
    "keycloak_sub": "...",
    "email": "...",
    "display_name": "...",
    "is_active": true,
    "created_at": "2026-04-02T..."
  }
  ```

#### Scenario: Unauthenticated request to /auth/me
- **WHEN** request is made to `GET /api/v1/auth/me` without JWT
- **THEN** system returns 401 Unauthorized

### Requirement: get_current_user() FastAPI Dependency
The system SHALL provide a FastAPI dependency that:
- Extracts and validates Bearer token from Authorization header
- Calls `KeycloakAdapter` to validate JWT
- Creates user if needed (first login)
- Returns `User` object for use in route handlers
- Raises 401 if token is invalid or missing

#### Scenario: Valid token dependency injection
- **WHEN** route handler uses `Depends(get_current_user)`
- **THEN** dependency returns authenticated `User` object

#### Scenario: Invalid token raises 401
- **WHEN** route handler uses `Depends(get_current_user)` with invalid token
- **THEN** dependency raises HTTPException with status 401
