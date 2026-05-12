# Authentik OIDC Setup Guide

Complete guide for deploying Authentik as an OIDC Identity Provider for NAK Planner.

## Overview

Authentik is a modern, flexible identity provider with built-in OIDC/OAuth2 support. This setup configures it for NAK Planner using the **Public Client with PKCE** flow.

## Quick Start (Development)

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ (for setup script)
- bash (for deployment script)

### Step 1: Start Authentik
```bash
cd idp-deploy/authentik
cp .env.example .env

# Start services
docker compose up -d

# Wait for Authentik to be ready (~30 seconds)
docker compose logs -f authentik
```

### Step 2: Setup OAuth2 Provider & Application
```bash
# Run setup script (default bootstrap credentials: akadmin:insecure)
python3 setup_authentik_oauth2.py \
  --authentik-url http://localhost:9000 \
  --bootstrap-token akadmin:insecure

# This will:
# - Create OAuth2 OIDC Provider
# - Create application "NAK Planner"
# - Create test user "testuser" / "testpassword123"
# - Print OIDC Discovery URL
```

### Step 3: Configure Frontend
Copy the OIDC settings from script output to `services/frontend/.env.local`:

```env
VITE_OIDC_DISCOVERY_URL=http://localhost:9000/application/o/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=nak-planner-frontend
VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback
```

### Step 4: Test Login
```bash
cd services/frontend
bun run dev

# Open browser: http://localhost:5173/login
# Click "Login with Authentik"
# Use credentials: testuser / testpassword123
```

## Detailed Setup

### Environment Variables (.env)

```env
# Database
AUTHENTIK_POSTGRES_NAME=authentik
AUTHENTIK_POSTGRES_USER=authentik
AUTHENTIK_POSTGRES_PASSWORD=changeme_in_production

# Secret key (generate: openssl rand -base64 32)
AUTHENTIK_SECRET_KEY=your_secret_key_here

# Hostname
AUTHENTIK_HOSTNAME=localhost:9000

# Logging
AUTHENTIK_LOG_LEVEL=info
```

### Configuration Files

#### docker-compose.yml
- **authentik**: Main Authentik server (port 9000)
- **authentik-worker**: Background job processor
- **authentik-postgres**: PostgreSQL 16 database
- **authentik-redis**: Redis cache
- **idp_net**: Internal network

#### setup_authentik_oauth2.py
Creates:
- OAuth2 OIDC Provider (public client, PKCE-enabled)
- Application: "NAK Planner"
- User: `testuser` (password: `testpassword123`)

#### deploy_authentik.sh
VPS deployment orchestration (see "VPS Deployment" section).

## OIDC Configuration

The setup script creates a **Public OAuth2 Client** with:

```text
Client ID: nak-planner-frontend
Client Type: Public (no secret)
Flow: Authorization Code with PKCE
Redirect URIs:
  - http://localhost:5173/auth/callback
  - https://planner.example.com/auth/callback
Logout URIs: (configured in provider)
```

### OIDC Discovery Endpoint

```text
GET http://localhost:9000/application/o/.well-known/openid-configuration
```

Returns standard OpenID Connect discovery endpoints.

## Admin Console

Access Authentik administration:

```text
http://localhost:9000/if/admin/
Username: akadmin
Password: insecure (default, CHANGE IN PRODUCTION)
```

### Change Bootstrap Password

1. Admin Console → Users
2. Select "akadmin"
3. Click "Reset Password"
4. Set new password

## User Management

### Create User via Admin Console
1. Admin Console → Users → Create
2. Set Username, Email, Name
3. Admin Console → Users → [username] → Set Password
4. Save

### Create User via API
```bash
curl -X POST http://localhost:9000/api/v3/core/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "name": "New User",
    "password": "SecurePassword123"
  }'
```

## Production Deployment (VPS)

### Prerequisites
- VPS with Docker & Docker Compose
- Domain name (e.g., auth.example.com)
- SSL certificate (Let's Encrypt via Traefik)
- Traefik reverse proxy running

### Step 1: Copy Files to VPS
```bash
scp -r idp-deploy/authentik user@vps:/opt/authentik
cd /opt/authentik
```

### Step 2: Use Automated Deployment Script
```bash
# Generate secure secret key
SECRET_KEY=$(openssl rand -base64 32)

./deploy_authentik.sh /opt/authentik \
  http://localhost:9000 \
  "$SECRET_KEY"

# Script performs:
# - Validates Docker
# - Updates .env with secret
# - Starts containers
# - Waits for health checks
# - Runs OAuth2 setup
# - Prints configuration
```

### Step 3: Configure Traefik

Add Traefik labels to docker-compose.yml:

```yaml
services:
  authentik:
    labels:
      - traefik.enable=true
      - traefik.docker.network=traefik_net
      - traefik.http.routers.authentik.rule=Host(`auth.example.com`)
      - traefik.http.routers.authentik.entrypoints=websecure
      - traefik.http.routers.authentik.tls.certresolver=letsencrypt
      - traefik.http.services.authentik.loadbalancer.server.port=9000
    networks:
      - traefik_net
```

### Step 4: Update Frontend Configuration

Add to `services/frontend/.env.production`:
```env
VITE_OIDC_DISCOVERY_URL=https://auth.example.com/application/o/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=nak-planner-frontend
VITE_OIDC_REDIRECT_URI=https://planner.example.com/auth/callback
```

## Troubleshooting

### Authentik container not starting
```bash
# Check logs
docker compose logs -f authentik

# Common issues:
# 1. Port 9000 already in use
#    Solution: Change port in docker-compose.yml
# 2. Database migration timeout
#    Solution: Increase startup_period in healthcheck
# 3. Insufficient memory
#    Solution: Allocate more RAM to Docker
```

### Health check fails
```bash
# Authentik takes 30-60 seconds to start
docker compose logs authentik | grep "Starting"

# Manual health check
curl http://localhost:9000/-/health/live/
```

### Setup script fails to connect
```bash
# Ensure HTTP endpoint is responding
curl -v http://localhost:9000

# Check worker logs (required for user creation)
docker compose logs authentik-worker

# Ensure both server and worker are running
docker compose ps
```

### OIDC Discovery returns 404
```bash
# Verify provider was created
curl http://localhost:9000/api/v3/core/providers/

# Run setup script again
python3 setup_authentik_oauth2.py \
  --authentik-url http://localhost:9000 \
  --bootstrap-token akadmin:insecure
```

### Redirect URI mismatch
```env
Error: redirect_uri mismatch

Solution:
1. Check frontend URL in browser
2. Ensure it matches VITE_OIDC_REDIRECT_URI
3. Admin Console → Providers → [Provider Name]
4. Update "Redirect URIs" to exact URL from browser
```

## Security Considerations

### Development
- Default bootstrap credentials (akadmin:insecure)
- HTTP mode (no HTTPS)
- Randomized secret key
- Test user for development

### Production
- Change bootstrap password immediately
- Enable HTTPS (via Traefik)
- Use strong secret key (openssl rand -base64 32)
- Enable database backups
- Update Authentik version regularly
- Monitor logs for suspicious activity
- Implement rate limiting
- Use strong user passwords
- Regular audit log reviews

### OIDC Security
- PKCE prevents authorization code interception
- No client_secret in browser (public client)
- JWT tokens verified via JWKS endpoint
- Token refresh automatic (when needed)
- Session timeout configurable

## Monitoring & Maintenance

### Database Backups
```bash
# Backup PostgreSQL
docker compose exec authentik-postgres pg_dump -U authentik authentik > backup.sql

# Restore from backup
docker compose exec -T authentik-postgres psql -U authentik authentik < backup.sql
```

### Update Authentik Version
```bash
# Edit docker-compose.yml
image: ghcr.io/goauthentik/server:2024.5  # new version

# Rebuild and restart
docker compose up -d --build

# Database migrations run automatically
```

### Monitor Logs
```bash
# Follow all logs
docker compose logs -f

# Follow specific service
docker compose logs -f authentik

# Filter by level
docker compose logs authentik | grep "ERROR\|WARN"
```

### Audit Logs
```bash
# Access via Admin Console
Admin Console → System → Audit Log

# Or via API
curl http://localhost:9000/api/v3/events/events/ \
  -H "Authorization: Bearer $TOKEN"
```

## Redis Caching

Authentik uses Redis for:
- Session storage
- Cache
- Background job queue

Monitor Redis:
```bash
docker compose exec authentik-redis redis-cli
> INFO
> KEYS *
> FLUSHALL  # Clear cache (requires restart of services)
```

## References

- [Authentik Documentation](https://goauthentik.io/docs/)
- [OAuth2 Provider Documentation](https://goauthentik.io/docs/providers/oauth2/)
- [OIDC Provider Documentation](https://goauthentik.io/docs/providers/oidc/)
- [RFC 7636: PKCE](https://tools.ietf.org/html/rfc7636)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
