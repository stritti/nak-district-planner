# Keycloak OIDC Setup Guide

Complete guide for deploying Keycloak as an OIDC Identity Provider for NAK Planner.

## Overview

Keycloak is a mature, open-source identity and access management platform. This setup configures it as an OIDC provider for NAK Planner using the **Public Client with PKCE** flow (recommended for SPAs).

## Quick Start (Development)

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ (for setup script)
- bash (for deployment script)

### Step 1: Start Keycloak
```bash
cd idp-deploy/keycloak
cp .env.example .env

# For development (start-dev mode):
docker compose up -d

# For production (optimized build - requires more resources):
# Modify docker-compose.yml: command: start (instead of start-dev)
# KC_HOSTNAME_STRICT: "true"
# KC_STRICT_HTTPS: "true"
```

### Step 2: Setup Realm & Client
```bash
# Wait for Keycloak to be ready (check logs)
docker compose logs -f keycloak

# In another terminal, run setup script
python3 setup_keycloak_realm.py \
  --keycloak-url http://localhost:8080 \
  --admin-password admin_dev_pw

# This will:
# - Create realm "nak-planner"
# - Create public OIDC client "nak-planner-frontend"
# - Create test user "testuser" / "testpassword123"
# - Export realm config
# - Print OIDC Discovery URL
```

### Step 3: Configure Frontend
Copy the OIDC settings from script output to `services/frontend/.env.local`:

```env
VITE_OIDC_DISCOVERY_URL=http://localhost:8080/realms/nak-planner/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=nak-planner-frontend
VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback
```

### Step 4: Test Login
```bash
cd services/frontend
bun run dev

# Open browser: http://localhost:5173/login
# Click "Login with Keycloak"
# Use credentials: testuser / testpassword123
```

## Detailed Setup

### Environment Variables (.env)

```env
# Database
KEYCLOAK_DB_NAME=keycloak
KEYCLOAK_DB_USER=keycloak
KEYCLOAK_DB_PASSWORD=changeme_in_production

# Admin Account
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=changeme_in_production

# Hostname (used for OIDC discovery)
KC_HOSTNAME=keycloak.localhost

# Logging
KC_LOG_LEVEL=info
```

### Configuration Files

#### docker-compose.yml
- **keycloak**: Main Keycloak service (port 8080)
- **keycloak-db**: PostgreSQL 16 database
- **idp_net**: Internal network for IDP services

#### setup_keycloak_realm.py
Creates:
- Realm: `nak-planner`
- Client: `nak-planner-frontend` (Public, PKCE-enabled)
- User: `testuser` (password: `testpassword123`)

#### deploy_keycloak.sh
VPS deployment orchestration (see "VPS Deployment" section below).

## OIDC Client Configuration

The setup script creates a **Public Client** with these settings:

```text
Client ID: nak-planner-frontend
Access Type: Public (no client secret)
Flow: Authorization Code with PKCE
Redirect URIs:
  - http://localhost:5173/auth/callback
  - https://planner.example.com/auth/callback
Logout URIs:
  - http://localhost:5173
  - https://planner.example.com
```

### Why Public Client with PKCE?

- **Public Client**: No client_secret stored in browser (secure)
- **PKCE** (RFC 7636): Proof Key for Public Clients prevents authorization code interception
- **Frontend Benefits**:
  - No backend required to exchange code
  - Code stored securely in sessionStorage
  - Resilient to CSRF attacks

### OIDC Discovery Endpoint

```text
GET http://localhost:8080/realms/nak-planner/.well-known/openid-configuration
```

Returns:
- `authorization_endpoint`
- `token_endpoint`
- `userinfo_endpoint`
- `revocation_endpoint`
- `jwks_uri` (for token verification)

## Realm Management

### Access Admin Console

```env
http://localhost:8080/admin/
Username: admin
Password: (from .env KC_BOOTSTRAP_ADMIN_PASSWORD)
```

### Manual User Creation

1. Admin Console → Realm "nak-planner" → Users
2. Create User
3. Set Username, Email
4. Credentials tab → Set Password (temporary=false)
5. User Details → Verify Email

### Export/Import Realm

```bash
# Export (done automatically by setup script)
python3 setup_keycloak_realm.py \
  --keycloak-url http://localhost:8080 \
  --admin-password admin_dev_pw

# Import to another Keycloak instance
# Admin Console → Realm Import → Select realm-export.json
```

## Production Deployment (VPS)

### Prerequisites
- VPS with Docker & Docker Compose
- Domain name (e.g., auth.example.com)
- SSL certificate (Let's Encrypt via Traefik)
- Traefik reverse proxy running

### Step 1: Copy Files to VPS
```bash
# From local machine
scp -r idp-deploy/keycloak user@vps:/opt/keycloak
cd /opt/keycloak
```

### Step 2: Use Automated Deployment Script
```bash
./deploy_keycloak.sh /opt/keycloak \
  https://auth.example.com \
  your_secure_admin_password_here

# Script performs:
# - Validates Docker
# - Updates .env with credentials
# - Starts containers
# - Waits for health checks
# - Runs realm setup
# - Prints configuration summary
```

### Step 3: Configure Traefik

If you already have Traefik running, add labels to docker-compose.yml:

```yaml
services:
  keycloak:
    labels:
      - traefik.enable=true
      - traefik.docker.network=traefik_net
      - traefik.http.routers.keycloak.rule=Host(`auth.example.com`)
      - traefik.http.routers.keycloak.entrypoints=websecure
      - traefik.http.routers.keycloak.tls.certresolver=letsencrypt
      - traefik.http.services.keycloak.loadbalancer.server.port=8080
    networks:
      - traefik_net
```

Then update production docker-compose.yml in root:
```yaml
services:
  keycloak:
    extends:
      file: idp-deploy/keycloak/docker-compose.yml
      service: keycloak
```

### Step 4: Update Frontend Configuration

Add to `services/frontend/.env.production`:
```env
VITE_OIDC_DISCOVERY_URL=https://auth.example.com/realms/nak-planner/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=nak-planner-frontend
VITE_OIDC_REDIRECT_URI=https://planner.example.com/auth/callback
```

## Troubleshooting

### Keycloak container not starting
```bash
# Check logs
docker compose logs -f keycloak

# Common issues:
# 1. Port 8080 already in use
#    Solution: Change port in docker-compose.yml
# 2. Database not ready
#    Solution: Wait longer, check postgres health
# 3. Insufficient memory
#    Solution: Allocate more RAM to Docker
```

### Health check fails
```bash
# Keycloak takes 30-120 seconds to start on first run
docker compose logs keycloak | grep "Started"

# For development (start-dev):
# - Faster startup (~30 seconds)
# - Not optimized for production

# For production (start --optimized):
# - Slower startup (~2 minutes)
# - Optimized performance
```

### Setup script fails to connect
```bash
# Ensure Keycloak HTTP endpoint is responding
curl -v http://localhost:8080/health

# Check Keycloak logs
docker compose logs keycloak

# Keycloak must be fully initialized before setup script runs
# Wait for "Started" message in logs
```

### OIDC Discovery returns 404
```bash
# Verify realm exists
curl -v http://localhost:8080/realms/nak-planner

# Run setup script again
python3 setup_keycloak_realm.py \
  --keycloak-url http://localhost:8080 \
  --admin-password admin_dev_pw
```

### Frontend redirect_uri mismatch
```env
Error: redirect_uri mismatch

Solution:
1. Check frontend URL in browser
2. Ensure it matches VITE_OIDC_REDIRECT_URI
3. Update Keycloak client:
   Admin Console → Realm → Clients → nak-planner-frontend
   → Valid Redirect URIs → Add exact URL from browser
```

## Security Considerations

### Development
- Start with `start-dev` mode (no TLS required)
- Test user credentials in plaintext
- `KC_HOSTNAME_STRICT=false` (allows any hostname)
- `KC_STRICT_HTTPS=false` (allows HTTP)

### Production
- Switch to `start` command with `--optimized`
- Generate strong admin password
- Enable `KC_HOSTNAME_STRICT=true`
- Enable `KC_STRICT_HTTPS=true` (HTTPS only)
- Use strong database password
- Enable audit logging
- Regular backups of database
- Update Keycloak version regularly

### OIDC Security
- PKCE prevents authorization code interception
- No client_secret in browser
- JWT tokens verified via JWKS endpoint
- Token refresh automatic (5 min before expiry)
- Logout revokes tokens

## Monitoring & Maintenance

### Database Backups
```bash
# Backup PostgreSQL
docker compose exec keycloak-db pg_dump -U keycloak keycloak > backup.sql

# Restore from backup
docker compose exec -T keycloak-db psql -U keycloak keycloak < backup.sql
```

### Update Keycloak Version
```bash
# Edit docker-compose.yml
image: quay.io/keycloak/keycloak:26.6  # new version

# Rebuild and restart
docker compose up -d --build

# Database migrations run automatically
```

### Monitor Logs
```bash
docker compose logs -f keycloak

# Filter by level
docker compose logs keycloak | grep "WARN\|ERROR"
```

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OIDC Provider Documentation](https://www.keycloak.org/docs/latest/server_admin/#_oidc_configuration)
- [RFC 7636: PKCE](https://tools.ietf.org/html/rfc7636)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
