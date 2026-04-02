# Keycloak Deployment Testing Guide

This guide walks you through testing the Keycloak deployment on your VPS. Follow these steps sequentially to verify everything is working correctly.

## Prerequisites Verification

### Step 1: Verify Docker & Compose Plugin
```bash
# Check Docker
docker --version
# Expected: Docker version 20.10+ 

# Check Docker Compose Plugin (built into Docker)
docker compose version
# Expected: Docker Compose version 2.0+

# Verify you can run Docker commands without sudo (optional but recommended)
docker ps
# Should list containers without permission errors
```

**Status:** ✅ / ❌

### Step 2: Verify Python 3 & requests library
```bash
# Check Python 3
python3 --version
# Expected: Python 3.11+

# Test requests library
python3 -c "import requests; print(f'requests {requests.__version__} installed')"
# If not installed, the deploy script will install it automatically
```

**Status:** ✅ / ❌

### Step 3: Verify Traefik Network Exists
```bash
# Check if traefik network exists
docker network ls | grep traefik
# Expected: Should show a 'traefik' network

# If not found, you may need to:
# - Start Traefik first: docker compose -f path/to/traefik/docker compose.yml up -d
# - Or create it manually: docker network create traefik
```

**Status:** ✅ / ❌

---

## Deployment Test (Local Simulation)

Since you may not want to deploy to VPS yet, you can test the scripts locally first. This section assumes you're testing in `/opt/keycloak-test/` or similar.

### Step 4: Copy Files to Test Directory
```bash
# Create test directory
mkdir -p /opt/keycloak-test
cd /opt/keycloak-test

# Copy from repo
cp /path/to/nak-district-planner/keycloak-deploy/* .
# Or if you're in the repo:
cp keycloak-deploy/* /opt/keycloak-test/
```

**Status:** ✅ / ❌

### Step 5: Prepare Test Environment
```bash
# Create .env from template
cp .env.example .env

# View the .env file
cat .env

# Optional: Edit .env for local testing
# KC_HOSTNAME_URL=http://localhost:8080  (if testing without Traefik)
```

**Status:** ✅ / ❌

### Step 6: Run Deployment Script (Test Mode)

**Option A: Full deployment (with Traefik)**
```bash
cd /opt/keycloak-test
chmod +x deploy_keycloak.sh

./deploy_keycloak.sh \
  "$(pwd)" \
  "https://auth.5tritti.de" \
  "MyTestPassword123"

# The script will:
# 1. Check Docker & Docker Compose
# 2. Create directory structure
# 3. Update .env with passwords
# 4. Start containers: docker compose up -d
# 5. Wait for Keycloak to be ready (60-120s on first start)
# 6. Verify Traefik network
# 7. Run setup_keycloak_realm.py
# 8. Output CLIENT_SECRET
```

**Expected Output:**
```
═══════════════════════════════════════════════════════════
Keycloak VPS Deployment
═══════════════════════════════════════════════════════════

✓ Docker is installed
✓ Docker Compose is installed
[Step 2-7 output...]
═══════════════════════════════════════════════════════════
Deployment Complete!
═══════════════════════════════════════════════════════════

Keycloak is now running at: https://auth.5tritti.de
Admin Console: https://auth.5tritti.de/admin/

Next steps:
1. Copy the CLIENT_SECRET from above
2. Add to nak-district-planner/.env:
   KEYCLOAK_URL=https://auth.5tritti.de
   KEYCLOAK_REALM=nak-planner
   KEYCLOAK_CLIENT_ID=nak-planner-api
   KEYCLOAK_CLIENT_SECRET=<copied-secret>
```

**Status:** ✅ / ❌

**If deployment fails:**
- Check logs: `docker compose logs -f keycloak`
- Common issues:
  - Traefik network doesn't exist: Create it with `docker network create traefik`
  - Port already in use: Change `KC_HOSTNAME_URL` in `.env`
  - Keycloak won't start: Wait longer (first start can take 2 minutes), or check health: `curl http://localhost:8080/health`

---

## Verification Tests

### Step 7: Check Container Status
```bash
cd /opt/keycloak-test

# See all running containers
docker compose ps

# Expected output:
# NAME                      STATUS              PORTS
# keycloak-test-keycloak-1  Up X minutes        8080/tcp
# keycloak-test-db-1        Up X minutes        5432/tcp

# View logs
docker compose logs -f keycloak

# Expected: You should see messages like:
# "Started Keycloak in X seconds"
```

**Status:** ✅ / ❌

### Step 8: Verify Health Checks
```bash
# For local testing without Traefik:
curl http://localhost:8080/health
# Expected: 200 OK, JSON response with status

# For Traefik setup:
curl https://auth.5tritti.de/health
# Expected: 200 OK, JSON response with status
```

**Status:** ✅ / ❌

### Step 9: Verify JWKS Endpoint
```bash
# This is the critical endpoint for JWT validation
curl https://auth.5tritti.de/realms/nak-planner/.well-known/jwks.json

# Expected response:
# {
#   "keys": [
#     {
#       "kid": "...",
#       "kty": "RSA",
#       "alg": "RS256",
#       "use": "sig",
#       "n": "...",
#       "e": "AQAB"
#     }
#   ]
# }
```

**Status:** ✅ / ❌

### Step 10: Verify Realm Configuration
```bash
# Check that realm was created
curl https://auth.5tritti.de/admin/realms/nak-planner \
  -H "Authorization: Bearer $(curl -s -X POST https://auth.5tritti.de/realms/master/protocol/openid-connect/token \
    -d 'client_id=admin-cli&grant_type=password&username=admin&password=MyTestPassword123' \
    | jq -r '.access_token')"

# Expected: 200 OK with realm details
```

**Status:** ✅ / ❌

---

## Capture CLIENT_SECRET

### Step 11: Get CLIENT_SECRET from Script Output

The deploy script prints the CLIENT_SECRET during realm setup. Look for output like:

```
============================================================
CLIENT SECRET (speichere in .env):
============================================================
<CLIENT_SECRET_HERE>
```

If you missed it, you can retrieve it from Keycloak Admin Console:
1. Navigate to: `https://auth.5tritti.de/admin/`
2. Login with: username=`admin`, password=`MyTestPassword123`
3. Select realm: `nak-planner`
4. Go to: Clients → nak-planner-api → Credentials
5. Copy the Secret value

**CLIENT_SECRET:** `_____________________________________`

**Status:** ✅ / ❌

---

## Update Backend Configuration

### Step 12: Add Keycloak Variables to nak-district-planner/.env

Once you have the CLIENT_SECRET, add these variables to your main project's `.env`:

```bash
# Navigate to project root
cd /path/to/nak-district-planner

# Edit .env and add:
KEYCLOAK_URL=https://auth.5tritti.de
KEYCLOAK_REALM=nak-planner
KEYCLOAK_CLIENT_ID=nak-planner-api
KEYCLOAK_CLIENT_SECRET=<paste-secret-from-step-11>
```

**Verify:**
```bash
# Check that variables are set
grep KEYCLOAK .env
```

**Status:** ✅ / ❌

---

## Optional: Test Login Flow

### Step 13: Test Login in Admin Console

1. Open browser: `https://auth.5tritti.de/admin/`
2. Login with credentials:
   - Username: `admin`
   - Password: `MyTestPassword123`
3. Select realm: `nak-planner`
4. Verify you see:
   - Realm name: `nak-planner`
   - Client: `nak-planner-api`
   - User: `test` (created by setup script)

**Status:** ✅ / ❌

### Step 14: Test OAuth Token Endpoint

```bash
# Request a token using test user credentials
curl -X POST https://auth.5tritti.de/realms/nak-planner/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'client_id=nak-planner-api' \
  -d 'client_secret=<CLIENT_SECRET_FROM_STEP_11>' \
  -d 'grant_type=password' \
  -d 'username=test' \
  -d 'password=test-password'

# Expected response:
# {
#   "access_token": "eyJhbGc...",
#   "expires_in": 300,
#   "refresh_expires_in": 1800,
#   "token_type": "Bearer",
#   ...
# }
```

**Status:** ✅ / ❌

### Step 15: Decode Access Token (Optional)

```bash
# Extract access token from Step 14 response
ACCESS_TOKEN="<token_from_step_14>"

# Decode (macOS/Linux)
echo $ACCESS_TOKEN | jq -R 'split(".") | .[1] | @base64d | fromjson'

# Expected payload:
# {
#   "exp": 1234567890,
#   "iat": 1234567600,
#   "sub": "<user_id>",
#   "username": "test",
#   "email": "test@example.com",
#   ...
# }
```

**Status:** ✅ / ❌

---

## Cleanup & Next Steps

### Step 16: Verify Database & Volumes

```bash
# Check database volume
docker volume ls | grep keycloak

# Check database is healthy
docker exec <keycloak_db_container_id> pg_isready -U keycloak
# Expected: "accepting connections"
```

**Status:** ✅ / ❌

### Step 17: Document Results

Fill out this summary:

| Component | Status | Notes |
|-----------|--------|-------|
| Docker & Docker Compose | ✅ / ❌ | |
| Python 3 & requests | ✅ / ❌ | |
| Traefik network | ✅ / ❌ | |
| Deployment script | ✅ / ❌ | |
| Containers running | ✅ / ❌ | |
| Health endpoint | ✅ / ❌ | |
| JWKS endpoint | ✅ / ❌ | |
| Realm created | ✅ / ❌ | |
| CLIENT_SECRET captured | ✅ / ❌ | |
| Backend .env updated | ✅ / ❌ | |
| Token endpoint works | ✅ / ❌ | |

---

## Troubleshooting

### Keycloak won't start
- **Symptom:** Containers start but Keycloak keeps restarting
- **Fix 1:** Check logs: `docker compose logs keycloak`
- **Fix 2:** Increase wait time in script (line 112-113 in `deploy_keycloak.sh`)
- **Fix 3:** Ensure database is healthy: `docker compose logs db`

### Traefik network not found
- **Symptom:** Script fails at Step 7 with "network 'traefik' not found"
- **Fix:** Create network: `docker network create traefik`
- **Or:** Start Traefik first from your main docker compose

### JWKS endpoint returns 404
- **Symptom:** `curl https://auth.5tritti.de/realms/nak-planner/.well-known/jwks.json` returns 404
- **Fix:** Realm may not be created. Check if realm setup script ran successfully
- **Or:** Keycloak may still be starting, wait 30 more seconds

### Admin credentials not working
- **Symptom:** Can't login to admin console with admin/MyTestPassword123
- **Fix:** Check `.env` file: `KEYCLOAK_ADMIN_PASSWORD=MyTestPassword123`
- **Or:** Recreate containers: `docker compose down -v && docker compose up -d`

### CLIENT_SECRET not printed
- **Symptom:** Script completes but no SECRET is shown
- **Fix:** Script may have had an error. Check: `docker compose logs keycloak`
- **Or:** Get it from Admin Console (Step 11 alternative method)

---

## Success Criteria

Deployment is successful when:
- ✅ All containers are running and healthy
- ✅ JWKS endpoint returns valid keys
- ✅ Realm `nak-planner` exists with proper configuration
- ✅ Client `nak-planner-api` is created
- ✅ Test user can obtain OAuth tokens
- ✅ CLIENT_SECRET is captured and added to backend `.env`

**Overall Status:** ✅ Ready for Backend Implementation / ❌ Needs fixes

---

## Next: Backend Implementation

Once all tests pass:
1. Proceed to Task 2: User table + SQLAlchemy models
2. Create Keycloak adapter for JWT validation
3. Implement `get_current_user()` dependency
4. Update API endpoints to use Bearer tokens instead of API keys

See: `openspec/changes/phase4a-jwt-auth-minimal/tasks.md` (Task 2 onwards)
