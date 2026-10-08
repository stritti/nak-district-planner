## 1. Keycloak Infrastructure

- [x] 1.1 Create `keycloak-deploy/` directory with standalone structure (docker-compose.yml, .env.example, docs)
- [x] 1.2 Write `keycloak-deploy/docker-compose.yml` with Keycloak service (port 8080), PostgreSQL backend, Traefik labels for `auth.5tritti.de`
- [x] 1.3 Create `keycloak-deploy/.env.example` with `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD`, PostgreSQL credentials, `KC_HOSTNAME_URL`
- [x] 1.4 Deploy Keycloak to VPS and verify `https://auth.5tritti.de/` is reachable
- [x] 1.5 Create Keycloak realm (e.g., "nak-planner") and export realm config to `keycloak-deploy/realm-export.json`
- [x] 1.6 Create Keycloak client (e.g., "nak-planner-api") with:
  - Client type: Confidential
  - Valid Redirect URIs: `https://planner.5tritti.de/auth/callback`
  - Logout URL: `https://planner.5tritti.de/`
  - Export client secret for backend `.env`
- [x] 1.7 Create test user in Keycloak (e.g., `test@example.com` / `test-password`)
- [x] 1.8 Verify JWKS endpoint is reachable: `https://auth.5tritti.de/realms/nak-planner/.well-known/jwks.json`

## 2. Backend: Database & Models

- [ ] 2.1 Create Alembic migration for `user` table with columns:
  - `id` (UUID, PK)
  - `keycloak_sub` (VARCHAR, UNIQUE) — Keycloak user ID
  - `email` (VARCHAR)
  - `display_name` (VARCHAR nullable)
  - `is_active` (BOOLEAN, default true)
  - `created_at` (TIMESTAMP)
  - `updated_at` (TIMESTAMP)
- [ ] 2.2 Create SQLAlchemy model `User` in `app/domain/models/user.py`
- [ ] 2.3 Create SQLAlchemy ORM model `UserORM` in `app/adapters/db/models.py`
- [ ] 2.4 Create repository port `UserRepository` in `app/domain/ports/user_repository.py` with methods:
  - `find_by_keycloak_sub(sub: str) -> User | None`
  - `create_from_token_claims(sub, email, display_name) -> User`
  - `save(user: User) -> None`

## 3. Backend: Keycloak Adapter & JWT Validation

- [ ] 3.1 Install Python dependency: `python-jose[cryptography]`
- [ ] 3.2 Create `KeycloakAdapter` in `app/adapters/auth/keycloak.py` with:
  - Constructor: `__init__(keycloak_url, realm, client_id, client_secret)`
  - Method: `fetch_jwks() -> dict` (caches for 1 hour)
  - Method: `validate_token(token: str) -> dict` (returns token claims: sub, email, name)
  - Custom exception: `KeycloakError` for validation failures
- [ ] 3.3 Write unit tests for `KeycloakAdapter`:
  - Test valid token validation
  - Test expired token rejection
  - Test invalid signature rejection
  - Test JWKS caching
- [ ] 3.4 Create `get_current_user()` FastAPI dependency in `app/adapters/api/deps.py`:
  - Extract Bearer token from Authorization header
  - Validate token via `KeycloakAdapter`
  - Look up or create user via `UserRepository`
  - Return `User` object
  - Raise 401 if token invalid or missing
- [ ] 3.5 Write unit tests for `get_current_user()` dependency:
  - Valid token returns user
  - Invalid token raises 401
  - Missing header raises 401
  - First login creates user auto-magically

## 4. Backend: API Endpoints

- [ ] 4.1 Create `GET /api/v1/auth/me` endpoint:
  - Requires `get_current_user()` dependency
  - Returns current user object (id, email, display_name, etc.)
  - Test with authenticated request
- [ ] 4.2 Update `.env.example` with new Keycloak variables:
  - `KEYCLOAK_URL=https://auth.5tritti.de`
  - `KEYCLOAK_REALM=nak-planner`
  - `KEYCLOAK_CLIENT_ID=nak-planner-api`
  - `KEYCLOAK_CLIENT_SECRET=<from-keycloak>`
- [ ] 4.3 Update `app/config.py` (settings) to read Keycloak env vars
- [ ] 4.4 Initialize `KeycloakAdapter` singleton in FastAPI app startup (lifespan)
- [ ] 4.5 Replace `verify_api_key` dependency with `get_current_user` on ALL protected `/api/v1/` routes:
  - `/api/v1/events` (POST, GET)
  - `/api/v1/service-assignments` (POST, PUT, DELETE)
  - `/api/v1/calendar-integrations` (POST, GET, PATCH, DELETE)
  - `/api/v1/districts/{id}/matrix` (GET)
  - etc.
  - Keep `/api/health` unprotected
- [ ] 4.6 Write integration tests for protected routes with mock JWT

## 5. Frontend: Keycloak Integration

- [ ] 5.1 Install `keycloak-js` library in `services/frontend/`: `bun add keycloak-js`
- [ ] 5.2 Create `src/auth/keycloak.ts` module:
  - Initialize Keycloak client with realm, client_id, URL
  - Expose `keycloak` instance for use in app
- [ ] 5.3 Update `src/main.ts` to initialize Keycloak before Vue app mount:
  - `keycloak.init({ onLoad: 'login-required' })` (redirect to login if not authenticated)
  - Mount Vue app only after Keycloak init completes
- [ ] 5.4 Create Pinia store `useAuthStore` in `src/stores/authStore.ts`:
  - State: `user`, `token`, `isAuthenticated`
  - Getters: `currentUser`, `isLoggedIn`
  - Actions: `loadUser()`, `logout()`
- [ ] 5.5 Update `src/main.ts` to load user into auth store after Keycloak init:
  - Call `authStore.loadUser()` with `keycloak.tokenParsed`
- [ ] 5.6 Create route guard in `src/router/index.ts`:
  - Redirect to Keycloak login if route requires auth and user not logged in
  - Allow public routes (login page, health check)
- [ ] 5.7 Implement token refresh hook:
  - Call `keycloak.onTokenExpired(() => keycloak.refreshToken())`
  - This runs automatically before token expires
- [ ] 5.8 Implement logout handler:
  - Create logout button in header/nav
  - On click: `keycloak.logout({ redirectUri: 'https://planner.5tritti.de/login' })`

## 6. Frontend: UI Updates

- [ ] 6.1 Add user profile display in header/nav (from `authStore.currentUser`)
- [ ] 6.2 Add logout button in header/nav
- [ ] 6.3 Create login page component (if not already present) that displays Keycloak login status
- [ ] 6.4 Update API client (`src/api/*.ts`) to automatically include Bearer token in Authorization header:
  - Extract from `keycloak.token` before each request
  - Handle 401 responses by redirecting to login
- [ ] 6.5 Test end-to-end:
  - Visit `https://planner.5tritti.de/`
  - Redirect to `auth.5tritti.de` login page
  - Log in with test user
  - Redirect back to frontend
  - Verify token in localStorage
  - Verify `/api/v1/auth/me` returns user profile
  - Verify protected endpoints work with JWT

## 7. Testing & Documentation

- [ ] 7.1 Write integration tests for full auth flow (see `tests/integration/test_auth_flow.py`):
  - Keycloak token validation
  - User auto-creation
  - Protected route access
  - Logout flow
- [ ] 7.2 Update README with JWT auth setup instructions
- [ ] 7.3 Document Keycloak deployment in `docs/keycloak-setup.md`:
  - How to deploy keycloak-deploy stack
  - How to create realm and client
  - Troubleshooting (JWKS endpoint, token validation)
- [ ] 7.4 Create `.env` from `.env.example` and fill in Keycloak credentials
- [ ] 7.5 Run local tests to verify everything works:
  - `uv run pytest tests/unit/ -v` (unit tests pass)
  - `uv run pytest tests/integration/ -v` (integration tests pass, needs DB)
  - Frontend dev server: `bun run dev` (login flow works)
