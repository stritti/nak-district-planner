## Context

The NAK Planner currently uses a single shared API key (`X-API-Key` header) for all API requests. This is suitable for development but unsustainable for production:
- No per-user identity (audit, authorization impossible)
- Single credential shared across all clients (credential rotation risky)
- No token expiration (credential compromise has indefinite impact)
- Multi-tenant deployment requires user isolation and audit trails

Keycloak is available and already running on `auth.5tritti.de`. The backend runs in Docker with access to external URLs via Traefik.

**Scope:** Implement JWT auth sufficient for MVP deployment. Rollen-based access control deferred to Phase 5.

## Goals / Non-Goals

**Goals:**
- Users authenticate to Keycloak (email/password)
- Backend validates JWT tokens without calling Keycloak per request (JWKS caching)
- User records auto-create on first login
- Frontend redirects unauthenticated users to Keycloak
- Token refresh happens automatically before expiration
- All `/api/v1/` routes require valid JWT (except health check)
- Logout clears tokens and Keycloak session
- Keycloak realm can be re-used by other projects in future

**Non-Goals:**
- Rollen-based route guards (Phase 5: `require_role(...)`)
- User management UI (Phase 5)
- Audit logging (Phase 5: `introduce-non-functional-baseline`)
- Social login / LDAP / SAML (future phases)
- API key fallback for CI/scripts (can be added in Phase 5 if needed)

## Decisions

### Decision 1: Separate Keycloak Docker Compose
**Choice:** Create standalone `keycloak-deploy/docker-compose.yml` (user manages separately)

**Rationale:**
- Keycloak is long-lived infra, shared by multiple projects
- NAK Planner is project-specific
- Decoupling allows Keycloak upgrades without affecting NAK Planner deployments
- Clear ownership and dependency management

**Alternative considered:** Keycloak in `services/backend/docker-compose.yml`
- ❌ Would force Keycloak lifecycle with each project deployment
- ❌ Harder to share with other projects

### Decision 2: JWKS Caching Strategy
**Choice:** Cache JWKS in-memory with 1-hour TTL; lazy refresh on miss

**Rationale:**
- JWKS is stable (public key set changes rarely)
- 1-hour TTL balances freshness (new key rotation detected within 1 hr) with reduction of external calls
- Lazy refresh avoids startup blocking if Keycloak is slow
- Simple to implement; no external cache needed (Redis reserved for Celery)

**Alternative considered:** Every request validates against Keycloak token endpoint
- ❌ Performance: N requests → N Keycloak calls
- ❌ Availability risk: Keycloak downtime breaks all API calls

**Alternative considered:** Store JWKS in Redis
- ❌ Overkill for stable data
- ❌ Adds Redis dependency to auth layer

### Decision 3: User Auto-Creation on First Login
**Choice:** Create `User` record in NAK Planner DB when JWT is first validated

**Rationale:**
- Decouples user identity (Keycloak) from application data (NAK Planner)
- Allows future tenant/role/preference assignment per user
- Idempotent: duplicate login attempts find existing user

**Alternative considered:** Fetch user from Keycloak API per request
- ❌ Performance: N requests → N Keycloak API calls
- ❌ Keycloak becomes hard dependency for every API call

### Decision 4: Token Storage & Refresh
**Choice:** localStorage for tokens; `keycloak-js` library for refresh logic

**Rationale:**
- `keycloak-js` handles OAuth2 redirect flow, token refresh, logout automatically
- localStorage survives page reload (good UX)
- Keycloak-JS refreshes token automatically before expiration
- Standard practice for SPAs

**Alternative considered:** Secure cookies (HttpOnly)
- ❌ Would require backend `/auth/callback` implementation
- ❌ CORS complexity with Keycloak
- ✓ More secure for XSS, but `keycloak-js` doesn't support; defer to Phase 5 hardening

**Alternative considered:** No refresh; force re-login on expiration
- ❌ Poor UX; session timeout mid-workflow

### Decision 5: Logout Mechanism
**Choice:** Frontend redirects to Keycloak logout, then to login page

**Rationale:**
- Keycloak invalidates session server-side
- Browser clears localStorage (frontend tokens)
- User cannot access protected routes (no token)
- Simple, no backend logout endpoint needed

**Alternative considered:** Backend logout endpoint
- ❌ Extra complexity; Keycloak doesn't maintain per-app logout state
- ✓ Audit log on logout; defer to Phase 5

### Decision 6: Keycloak Client Configuration
**Choice:** Confidential client with `client_secret` (no public flow)

**Rationale:**
- Backend securely stores `KEYCLOAK_CLIENT_SECRET` in `.env`
- Frontend only stores JWT, not client secret
- More secure than public client
- Standard for SPA + backend architecture

**Client-side:** Frontend uses standard OIDC Authorization Code flow (Keycloak-JS handles it)

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| JWKS endpoint unreachable on startup | KeycloakAdapter raises KeycloakError; deployment fails fast. Manual debugging via Keycloak health check. |
| Token stored in localStorage (XSS vulnerability) | Accepted for MVP. Upgrade to HttpOnly cookies + backend session store in Phase 5 hardening. Recommend CSP headers in Traefik config. |
| Keycloak DB separate from NAK DB | Two databases to manage. Acceptable trade-off for Keycloak reusability. Backup strategy must cover both. |
| Token refresh fails (e.g., network loss) | `keycloak-js` handles; user is logged out. Minimal data loss (in-flight requests fail, state not persisted). |
| Credential rotation (Keycloak client secret change) | Requires `.env` update and backend restart. Document in runbook. Consider short-lived secrets in future. |
| No audit trail for auth events | Acceptable for MVP. Add audit logging in Phase 5 (`introduce-non-functional-baseline`). |

## Migration Plan

**Phase 1: Keycloak Deployment (Day 1)**
1. Create `keycloak-deploy/` directory with standalone `docker-compose.yml`
2. Deploy Keycloak to VPS (manual or automation TBD)
3. Create Keycloak realm, client, user (admin UI or script)
4. Verify `https://auth.5tritti.de/.well-known/openid-configuration` is reachable

**Phase 2: Backend Changes (Days 1–2)**
1. Add `USER` table migration
2. Implement `KeycloakAdapter` with JWKS caching
3. Add `get_current_user()` dependency
4. Replace `verify_api_key` with `get_current_user` on all protected routes
5. Test with curl (Bearer token validation)

**Phase 3: Frontend Changes (Days 2–3)**
1. Install `keycloak-js`
2. Implement Keycloak init and login redirect
3. Implement callback handler
4. Add route guards
5. Test login flow end-to-end

**Phase 4: Testing & Hardening (Day 3–4)**
1. Integration tests for JWT validation
2. E2E tests for login/logout flow
3. Verify token refresh works
4. Load test (concurrent token validations)

**Rollback Strategy:**
- If Phase 2–3 encounters blockers, revert to `verify_api_key` (keep both mechanisms temporarily)
- Keycloak outage: Keep API-Key fallback in `.env` (config option to disable JWT requirement)

## Open Questions

1. **Keycloak Realm Management:** Manual setup via UI, or automated (Terraform/script)?
   - **Impact:** Onboarding time, maintainability
   - **Decision needed:** Before Keycloak deployment

2. **Client Secret Rotation:** How often? Who manages?
   - **Impact:** Security posture
   - **Decision needed:** In Phase 5 (credential management)

3. **Multiple Keycloak Instances:** One realm per project, or multi-tenant realm?
   - **Impact:** Isolation, scaling
   - **Decision needed:** As more projects join

4. **Backward Compatibility:** How long to support `X-API-Key` for legacy clients?
   - **Impact:** Migration burden
   - **Decision needed:** Document in release notes (default: remove after 1 release)
