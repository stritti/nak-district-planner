# Keycloak Deployment - Quick Test Reference

## One-Line Test Summary

Run this to test the entire deployment and get CLIENT_SECRET:

```bash
cd /opt/keycloak-test && \
chmod +x deploy_keycloak.sh && \
./deploy_keycloak.sh "$(pwd)" "https://auth.5tritti.de" "MySecurePassword123"
```

---

## Fast Health Checks (Run After Deployment)

```bash
# 1. Containers running?
docker-compose ps

# 2. Keycloak healthy?
curl https://auth.5tritti.de/health | jq .

# 3. JWKS endpoint working?
curl https://auth.5tritti.de/realms/nak-planner/.well-known/jwks.json | jq .keys[0]

# 4. Can get token?
curl -X POST https://auth.5tritti.de/realms/nak-planner/protocol/openid-connect/token \
  -d 'client_id=nak-planner-api&client_secret=<YOUR_SECRET>&grant_type=password&username=test&password=test-password' \
  | jq .access_token
```

---

## If Something Goes Wrong

### Containers won't start
```bash
docker-compose logs keycloak
docker-compose down -v  # Clean restart
docker-compose up -d
```

### Traefik network missing
```bash
docker network create traefik
docker-compose up -d
```

### Need CLIENT_SECRET again
```bash
# From Admin Console:
# https://auth.5tritti.de/admin → nak-planner → Clients → nak-planner-api → Credentials

# Or from database:
docker exec <db-container> psql -U keycloak keycloak -c "SELECT client_secret FROM client_attributes WHERE name='client.secret';"
```

---

## Success Checklist

- ✅ Containers: `docker-compose ps` shows keycloak + db running
- ✅ Health: `curl https://auth.5tritti.de/health` returns 200
- ✅ JWKS: `curl https://auth.5tritti.de/realms/nak-planner/.well-known/jwks.json` returns keys
- ✅ Token: Can request token with test user credentials
- ✅ Secret: CLIENT_SECRET captured and saved

---

## Next Steps

Once all checks pass, copy CLIENT_SECRET to `nak-district-planner/.env`:

```
KEYCLOAK_URL=https://auth.5tritti.de
KEYCLOAK_REALM=nak-planner
KEYCLOAK_CLIENT_ID=nak-planner-api
KEYCLOAK_CLIENT_SECRET=<paste-here>
```

Then proceed to **Task 2: User table + SQLAlchemy models** in the Backend implementation.

See: `openspec/changes/phase4a-jwt-auth-minimal/tasks.md`
