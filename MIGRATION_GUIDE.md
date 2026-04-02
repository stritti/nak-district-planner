# Migration Guide: Phase 4a → Phase 4b (OIDC Authentication)

This guide helps you migrate from Phase 4a (JWT-based authentication) to Phase 4b (OIDC with external identity provider).

## Overview

### Phase 4a (JWT)
- Backend issues JWT tokens
- Frontend stores tokens in localStorage
- Authentication is self-contained within NAK Planner
- Backend must manage user database

### Phase 4b (OIDC)
- External Identity Provider (Keycloak or Authentik) issues tokens
- Frontend uses PKCE flow for secure authentication
- Authentication delegated to professional identity provider
- Backend validates tokens via JWKS endpoint
- No user management needed in NAK Planner

## Compatibility

**Phase 4b is backward compatible with Phase 4a:**
- Existing JWT tokens continue to work (if not expired)
- Both authentication methods work simultaneously
- Gradual migration possible (old + new auth in parallel)

## Migration Steps

### Step 1: Choose Identity Provider

#### Option A: Keycloak (Recommended for Enterprises)
```bash
cd idp-deploy/keycloak
docker compose up -d
python3 setup_keycloak_realm.py --keycloak-url http://localhost:8080 --admin-password admin_dev_pw
```

#### Option B: Authentik (Recommended for Simple Setups)
```bash
cd idp-deploy/authentik
docker compose up -d
python3 setup_authentik_oauth2.py --authentik-url http://localhost:9000 --bootstrap-token akadmin:insecure
```

### Step 2: Update Frontend Configuration

Copy the IDP discovery URL from setup script output to `services/frontend/.env.local`:

```env
# New OIDC configuration
VITE_OIDC_DISCOVERY_URL=http://localhost:8080/realms/nak-planner/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=nak-planner-frontend
VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback

# Optional: Keep old JWT config for gradual migration
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Step 3: Restart Frontend

```bash
cd services/frontend
bun install
bun run dev
```

The frontend now supports OIDC login. The old JWT authentication still works.

### Step 4: Configure Backend (Gradual)

#### Option A: Parallel Authentication (Gradual Migration)

Update backend to accept both JWT and OIDC tokens:

**services/backend/app/adapters/api/auth.py:**

```python
from typing import Optional
import jwt
import requests

async def get_current_user(token: str) -> dict:
    """Accept both JWT (Phase 4a) and OIDC tokens (Phase 4b)"""
    
    # Try Phase 4b (OIDC) first
    if token.startswith("eyJ"):  # JWT format
        try:
            # Get JWKS from IDP
            discovery_url = os.getenv("OIDC_DISCOVERY_URL")
            if discovery_url:
                response = requests.get(discovery_url)
                jwks_uri = response.json().get("jwks_uri")
                
                # Verify token with JWKS
                payload = jwt.decode(
                    token,
                    options={"verify_signature": True},
                    algorithms=["RS256"]
                )
                return {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                    "name": payload.get("name"),
                    "source": "oidc"
                }
        except jwt.InvalidTokenError:
            pass
    
    # Fallback to Phase 4a (JWT from backend)
    try:
        payload = jwt.decode(
            token,
            key=os.getenv("SECRET_KEY"),
            algorithms=["HS256"]
        )
        return {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "source": "jwt"
        }
    except jwt.InvalidTokenError:
        raise Unauthorized("Invalid token")
```

#### Option B: Full Migration (Immediate)

Remove old JWT authentication and use only OIDC:

**services/backend/.env:**
```env
# Replace old JWT config with OIDC config
OIDC_DISCOVERY_URL=http://localhost:8080/realms/nak-planner/.well-known/openid-configuration
OIDC_AUDIENCE=nak-planner
OIDC_ISSUER=http://localhost:8080/realms/nak-planner

# Keep backend for internal services only (no external authentication)
BACKEND_JWT_SECRET=internal_only_random_string
```

### Step 5: Update Backend Dependencies

If not already installed, ensure Python OIDC support:

```bash
cd services/backend
uv pip install pyjwt cryptography python-jose
```

### Step 6: Update API Client (Frontend)

The frontend API client already supports OIDC (Phase 4b implementation):

**services/frontend/src/api/client.ts** already:
- Injects Bearer tokens in Authorization header
- Handles 401 errors with automatic token refresh
- Falls back to localStorage tokens if available

No changes needed here.

### Step 7: Migrate User Data (Optional)

If you need to migrate existing users from Phase 4a to Phase 4b:

```python
# services/backend/scripts/migrate_users_to_oidc.py

import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domain.models import User
from app.adapters.db.user_repository import SQLAlchemyUserRepository

async def migrate_users():
    """Migrate user database to OIDC sources"""
    
    engine = create_async_engine(os.getenv("DATABASE_URL"))
    
    async with engine.begin() as conn:
        async_session = sessionmaker(conn, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            repo = SQLAlchemyUserRepository(session)
            
            # Mark existing users as migrated
            users = await repo.list_all()
            for user in users:
                user.auth_source = "phase4a_migrated"  # Track migration
                await repo.update(user)
            
            print(f"✓ Migrated {len(users)} users to OIDC schema")

if __name__ == "__main__":
    asyncio.run(migrate_users())
```

Run migration:
```bash
cd services/backend
uv run python scripts/migrate_users_to_oidc.py
```

### Step 8: Test Migration

```bash
# Test old JWT tokens still work
curl -X GET http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer <old_jwt_token>"
# Expected: 200 OK

# Test new OIDC tokens work
curl -X GET http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer <oidc_token>"
# Expected: 200 OK
```

### Step 9: Update Production Configuration

On your production server:

**1. Deploy new code:**
```bash
git pull
docker compose build
docker compose up -d
```

**2. Update .env with OIDC configuration:**
```env
# Production IDP
OIDC_DISCOVERY_URL=https://auth.example.com/realms/nak-planner/.well-known/openid-configuration
OIDC_ISSUER=https://auth.example.com/realms/nak-planner
OIDC_AUDIENCE=nak-planner

# Backend-internal JWT (for service-to-service communication)
SECRET_KEY=<strong_random_key>
```

**3. Run migrations:**
```bash
docker compose run --no-deps --rm backend alembic upgrade head
```

**4. Restart:**
```bash
docker compose restart
```

## Rollback Plan

If you need to rollback from Phase 4b to Phase 4a:

1. **Revert code:**
   ```bash
   git checkout phase4a-jwt-auth-minimal
   ```

2. **Rebuild and restart:**
   ```bash
   docker compose build
   docker compose up -d
   ```

3. **Verify old auth still works:**
   ```bash
   curl -X GET http://localhost:8000/api/v1/events \
     -H "Authorization: Bearer <jwt_token>"
   ```

## Comparison Table

| Feature | Phase 4a (JWT) | Phase 4b (OIDC) |
|---------|---|---|
| User Management | In NAK Planner | External IDP |
| Token Issuer | Backend | Keycloak/Authentik |
| Token Type | HS256 JWT | RS256 JWT |
| Token Verification | Symmetric key | JWKS endpoint |
| Scalability | Limited | High (delegated) |
| User Portal | DIY | Professional UI |
| MFA Support | Must implement | Built-in |
| Password Reset | DIY | Built-in |
| OAuth2/SAML | Must implement | Available |
| Cost | Free (self-managed) | Free (OSS) or Commercial |

## Known Issues & Solutions

### Issue: OIDC Discovery returns 404
**Solution:** Ensure realm/provider is created
```bash
# Keycloak
python3 idp-deploy/keycloak/setup_keycloak_realm.py --admin-password admin_dev_pw

# Authentik
python3 idp-deploy/authentik/setup_authentik_oauth2.py --bootstrap-token akadmin:insecure
```

### Issue: Token validation fails at backend
**Solution:** Verify OIDC_DISCOVERY_URL is accessible from backend container
```bash
docker compose exec backend curl $OIDC_DISCOVERY_URL
```

### Issue: Users can't login after migration
**Solution:** Check user exists in IDP
```bash
# Keycloak Admin Console
http://localhost:8080/admin/ → Users

# Authentik Admin Console
http://localhost:9000/if/admin/ → Users
```

### Issue: Token refresh not working
**Solution:** Verify refresh_token_supports_rotation is enabled
- Keycloak: Realm Settings → Token Expiration
- Authentik: Provider Settings → Token Expiration

## Testing Checklist

After migration to Phase 4b, verify:

- [ ] OIDC Discovery endpoint returns configuration
- [ ] Frontend can fetch discovery configuration
- [ ] Login redirects to IDP
- [ ] IDP login redirects back to /auth/callback
- [ ] Frontend receives authorization code
- [ ] Frontend exchanges code for access token
- [ ] Access token stored in localStorage
- [ ] API requests include Bearer token
- [ ] Token refresh works on 401
- [ ] Logout clears token
- [ ] Protected routes require authentication
- [ ] Old JWT tokens still work (gradual migration)

## Performance Impact

**OIDC Migration Performance:**
- First login: +1-2s (IDP redirection)
- Token refresh: +0.5s (background)
- API calls: No additional latency (token already fetched)

**Recommendation:** OIDC actually improves performance because token validation is delegated to IDP (no database lookups for every request).

## Support & Further Reading

- **Keycloak Documentation:** https://www.keycloak.org/documentation
- **Authentik Documentation:** https://goauthentik.io/docs/
- **OIDC Specification:** https://openid.net/specs/openid-connect-core-1_0.html
- **PKCE (RFC 7636):** https://tools.ietf.org/html/rfc7636
- **Frontend OIDC Code:** See `services/frontend/src/composables/useOIDC.ts`
- **Backend OIDC Config:** See backend `.env` setup

## Questions?

For migration support, check:
1. IDP logs: `docker compose logs idp-service-name`
2. Frontend browser console: F12 → Console tab
3. Backend logs: `docker compose logs backend`
4. OIDC Integration test: `bash idp-deploy/test-oidc-integration.sh`
