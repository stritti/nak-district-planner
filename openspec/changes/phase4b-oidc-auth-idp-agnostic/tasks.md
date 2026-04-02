## 1. Dependency and Configuration Setup

- [x] 1.1 Add `authlib` and `httpx` to `services/backend/pyproject.toml`
- [x] 1.2 Update `.env.example` with `OIDC_*` variables (remove `KEYCLOAK_*`)
- [x] 1.3 Create `services/backend/app/config.py` with OIDC configuration from env vars
- [x] 1.4 Add `@vueuse/core` to `services/frontend/package.json`
- [x] 1.5 Create frontend `.env.example` with `VITE_OIDC_*` variables

## 2. Backend: OIDCAdapter Implementation

- [x] 2.1 Create `services/backend/app/adapters/auth/oidc.py` with `OIDCAdapter` class
- [x] 2.2 Implement OIDC discovery: fetch `/.well-known/openid-configuration`
- [x] 2.3 Implement JWKS fetching and caching (1-hour TTL)
- [x] 2.4 Implement JWT validation: signature, issuer, expiration, audience claims
- [x] 2.5 Implement error handling: connection errors, invalid tokens, cache miss fallbacks
- [x] 2.6 Write unit tests for OIDCAdapter (mocked OIDC provider)
- [x] 2.7 Add OIDC_ISSUER environment variable validation

## 3. Backend: User Model and get_current_user()

- [ ] 3.1 Create/update `services/backend/app/domain/models/user.py` (sub, email, displayname)
- [ ] 3.2 Create `services/backend/app/adapters/db/models.py` with User ORM model
- [ ] 3.3 Create Alembic migration for user table
- [ ] 3.4 Create `services/backend/app/adapters/db/repositories/user_repository.py`
- [ ] 3.5 Implement `get_current_user()` in `services/backend/app/adapters/api/deps.py`
- [ ] 3.6 Auto-create user on first login (in get_current_user)
- [ ] 3.7 Write tests for user auto-creation and get_current_user()

## 4. Backend: API Endpoint Updates

- [ ] 4.1 Create `GET /api/v1/auth/me` endpoint (returns current user info)
- [ ] 4.2 Update all `/api/v1/` endpoints to use `get_current_user` dependency instead of `verify_api_key`
- [ ] 4.3 Remove old `verify_api_key` function and `X-API-Key` header validation
- [ ] 4.4 Update API documentation/OpenAPI schema (Bearer token instead of API key)
- [ ] 4.5 Write integration tests for protected endpoints with JWT

## 5. Frontend: OIDC Composable

- [ ] 5.1 Create `services/frontend/src/composables/useOIDC.ts`
- [ ] 5.2 Implement OIDC discovery in useOIDC
- [ ] 5.3 Implement authorization URL generation (with PKCE)
- [ ] 5.4 Implement code exchange for tokens
- [ ] 5.5 Implement token refresh logic
- [ ] 5.6 Implement logout functionality
- [ ] 5.7 Export `user`, `token`, `login()`, `logout()` from composable

## 6. Frontend: Auth Callback and Initialization

- [ ] 6.1 Create `/auth/callback` route for OIDC redirect
- [ ] 6.2 Implement callback handler: exchange code for tokens
- [ ] 6.3 Initialize useOIDC in main.ts before app mount (wait for discovery)
- [ ] 6.4 Redirect unauthenticated users to `/auth/callback?... ` or re-login
- [ ] 6.5 Write tests for callback handler

## 7. Frontend: Auth Store (Pinia)

- [ ] 7.1 Create `services/frontend/src/stores/authStore.ts` (Pinia store)
- [ ] 7.2 Store user info, tokens, and authentication status
- [ ] 7.3 Implement auto-refresh timer (refresh token 5 min before expiry)
- [ ] 7.4 Expose `getToken()` for API calls
- [ ] 7.5 Write tests for auth store

## 8. Frontend: API Integration

- [ ] 8.1 Create `services/frontend/src/api/client.ts` with axios/fetch interceptor
- [ ] 8.2 Interceptor adds `Authorization: Bearer <token>` to all API calls
- [ ] 8.3 Handle 401 responses: refresh token or redirect to login
- [ ] 8.4 Update all existing API calls to use new interceptor

## 9. Frontend: Route Guards and UI

- [ ] 9.1 Update router/index.ts with requireAuth guard
- [ ] 9.2 Protect routes that require authentication
- [ ] 9.3 Add login button to navbar (redirect to OIDC provider)
- [ ] 9.4 Add logout button (appears when authenticated)
- [ ] 9.5 Add user menu showing `user.email` and "Logout"
- [ ] 9.6 Show loading state while OIDC discovery is in progress

## 10. IDP Configuration: Keycloak Setup

- [ ] 10.1 Rename `keycloak-deploy/` to `idp-deploy/keycloak/` (preserve existing scripts)
- [ ] 10.2 Update Keycloak docker-compose.yml to use correct hostname
- [ ] 10.3 Update Keycloak setup script to output `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`
- [ ] 10.4 Create `idp-deploy/keycloak/docs/OIDC-SETUP.md` with standard OIDC client configuration
- [ ] 10.5 Test Keycloak integration: backend + frontend with Keycloak IDP

## 11. IDP Configuration: Authentik Setup

- [ ] 11.1 Create `idp-deploy/authentik/docker-compose.yml` (PostgreSQL + Authentik)
- [ ] 11.2 Create `idp-deploy/authentik/setup_authentik_oauth2.py` (Python script to create OIDC app)
- [ ] 11.3 Create `idp-deploy/authentik/deploy_authentik.sh` (orchestration)
- [ ] 11.4 Create `idp-deploy/authentik/docs/OIDC-SETUP.md` with standard OIDC client configuration
- [ ] 11.5 Test Authentik integration: backend + frontend with Authentik IDP

## 12. Documentation and Testing

- [ ] 12.1 Create `idp-deploy/CONFIGURATION.md` with parallel Keycloak/Authentik setup guide
- [ ] 12.2 Update main README.md to reference Phase 4b (OIDC, provider-agnostic)
- [ ] 12.3 Create `.env.example` files for both Keycloak and Authentik deployments
- [ ] 12.4 Write end-to-end test: login → token exchange → API call → logout
- [ ] 12.5 Run full test suite (unit + integration + e2e)
- [ ] 12.6 Document migration from Phase 4a (Keycloak-specific) to Phase 4b (OIDC-agnostic)

## 13. Cleanup and Migration

- [ ] 13.1 Archive Phase 4a `phase4a-jwt-auth-minimal/` (keep for reference)
- [ ] 13.2 Remove Phase 4a-specific code/dependencies if only used in Phase 4a
- [ ] 13.3 Update git history/docs if necessary
- [ ] 13.4 Verify backward compatibility (old Keycloak-specific users can still work during transition)
- [ ] 13.5 Run full test suite one final time
