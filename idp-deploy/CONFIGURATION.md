# NAK Planner IDP Configuration Guide

This directory contains deployment configurations for two identity provider options:
- **Keycloak** (mature, feature-rich, Java-based)
- **Authentik** (modern, Python-based, lighter-weight)

Both are OIDC/OAuth2 compatible and work with the NAK Planner frontend's PKCE flow.

## Quick Comparison

| Feature | Keycloak | Authentik |
|---------|----------|-----------|
| Language | Java | Python/Go |
| Memory Usage | 512MB+ | 256MB+ |
| Startup Time | 30-120s | 30-60s |
| OIDC Support | ✅ Full | ✅ Full |
| PKCE Support | ✅ Yes | ✅ Yes |
| Admin UI | ✅ Comprehensive | ✅ Modern |
| Maturity | ✅ Very Mature | ✅ Growing |
| License | Apache 2.0 | GPL 3.0 / Commercial |
| Docker Hub | quay.io | ghcr.io |

## Deployment Modes

### Development (Both IDPs)

Start quickly with dev-optimized configurations:

```bash
# Keycloak development
cd idp-deploy/keycloak
docker compose up -d
python3 setup_keycloak_realm.py --keycloak-url http://localhost:8080 --admin-password admin_dev_pw

# Authentik development
cd idp-deploy/authentik
docker compose up -d
python3 setup_authentik_oauth2.py --authentik-url http://localhost:9000 --bootstrap-token akadmin:insecure
```

### Production (Both IDPs)

Optimize for performance, security, and reliability:

```bash
# Keycloak production
./deploy_keycloak.sh /opt/keycloak https://auth.example.com your_admin_password

# Authentik production
SECRET_KEY=$(openssl rand -base64 32)
./deploy_authentik.sh /opt/authentik https://auth.example.com "$SECRET_KEY"
```

## OIDC Integration Points

Both IDPs provide these standard endpoints:

### Keycloak Endpoints
```
Discovery: http://localhost:8080/realms/nak-planner/.well-known/openid-configuration
Authorization: http://localhost:8080/realms/nak-planner/protocol/openid-connect/auth
Token: http://localhost:8080/realms/nak-planner/protocol/openid-connect/token
UserInfo: http://localhost:8080/realms/nak-planner/protocol/openid-connect/userinfo
Logout: http://localhost:8080/realms/nak-planner/protocol/openid-connect/logout
JWKS: http://localhost:8080/realms/nak-planner/protocol/openid-connect/certs
```

### Authentik Endpoints
```
Discovery: http://localhost:9000/application/o/.well-known/openid-configuration
Authorization: http://localhost:9000/application/o/authorize/
Token: http://localhost:9000/application/o/token/
UserInfo: http://localhost:9000/application/o/userinfo/
Revoke: http://localhost:9000/application/o/revoke/
JWKS: http://localhost:9000/application/o/discover/keys/
```

## Frontend Configuration

Both IDPs work with the same frontend environment variables:

```env
# .env.local or .env.production
VITE_OIDC_DISCOVERY_URL=<IDP_DISCOVERY_URL>
VITE_OIDC_CLIENT_ID=nak-planner-frontend  # or nak-planner-api
VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback  # adjust for production
```

### Frontend Code (IDP-Agnostic)

The frontend doesn't care which IDP you use:

```typescript
// src/composables/useOIDC.ts - works with both Keycloak and Authentik
import { useOIDC } from '@/composables/useOIDC'

const { login, logout, user, token } = useOIDC()

// PKCE flow is identical for both IDPs
await login()  // Redirects to either Keycloak or Authentik
```

## Directory Structure

```
idp-deploy/
├── keycloak/
│   ├── docker-compose.yml          # Dev-optimized
│   ├── .env.example                # Environment template
│   ├── setup_keycloak_realm.py     # OIDC realm setup
│   ├── deploy_keycloak.sh          # Production deployment
│   ├── OIDC-SETUP.md               # Keycloak-specific guide
│   ├── docs/
│   ├── config/
│   └── README.md
│
├── authentik/
│   ├── docker-compose.yml          # Dev-optimized
│   ├── .env.example                # Environment template
│   ├── setup_authentik_oauth2.py   # OAuth2 provider setup
│   ├── deploy_authentik.sh         # Production deployment
│   ├── OIDC-SETUP.md               # Authentik-specific guide
│   └── README.md
│
└── CONFIGURATION.md                # This file
```

## Environment File (.env.example)

Both Keycloak and Authentik come with `.env.example`:

### Keycloak .env.example
```env
# Database
KEYCLOAK_DB_NAME=keycloak
KEYCLOAK_DB_USER=keycloak
KEYCLOAK_DB_PASSWORD=changeme

# Admin
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=changeme

# Hostname
KC_HOSTNAME=localhost
KC_LOG_LEVEL=info
```

### Authentik .env.example
```env
# Database
AUTHENTIK_POSTGRES_NAME=authentik
AUTHENTIK_POSTGRES_USER=authentik
AUTHENTIK_POSTGRES_PASSWORD=changeme

# Secret
AUTHENTIK_SECRET_KEY=changeme

# Hostname
AUTHENTIK_HOSTNAME=localhost:9000
AUTHENTIK_LOG_LEVEL=info
```

## Setup Scripts

### Keycloak Setup
```bash
python3 idp-deploy/keycloak/setup_keycloak_realm.py \
  --keycloak-url http://localhost:8080 \
  --admin-password admin_dev_pw \
  --realm-name nak-planner \
  --client-id nak-planner-frontend \
  --frontend-url http://localhost:5173
```

Creates:
- Realm: `nak-planner`
- Public Client: `nak-planner-frontend` (PKCE-enabled)
- Test User: `testuser` / `testpassword123`

### Authentik Setup
```bash
python3 idp-deploy/authentik/setup_authentik_oauth2.py \
  --authentik-url http://localhost:9000 \
  --bootstrap-token akadmin:insecure \
  --client-id nak-planner-frontend \
  --frontend-url http://localhost:5173
```

Creates:
- OAuth2 OIDC Provider
- Application: `nak-planner`
- Test User: `testuser` / `testpassword123`

## Deployment Scripts

### Keycloak Deployment
```bash
bash idp-deploy/keycloak/deploy_keycloak.sh \
  /opt/keycloak-deploy \
  https://auth.example.com \
  your_secure_password_here
```

Performs:
1. Validates Docker installation
2. Creates directory structure
3. Updates .env with credentials
4. Starts containers
5. Waits for health checks
6. Runs realm setup
7. Prints configuration summary

### Authentik Deployment
```bash
SECRET_KEY=$(openssl rand -base64 32)
bash idp-deploy/authentik/deploy_authentik.sh \
  /opt/authentik \
  https://auth.example.com \
  "$SECRET_KEY"
```

Performs:
1. Validates Docker installation
2. Creates directory structure
3. Updates .env with secret key
4. Starts containers
5. Waits for health checks
6. Runs OAuth2 setup
7. Prints configuration summary

## Switching Between IDPs

The frontend supports both IDPs via the same OIDC Discovery endpoint:

### Switch from Keycloak to Authentik

1. Stop Keycloak:
```bash
cd idp-deploy/keycloak
docker compose down
```

2. Start Authentik:
```bash
cd idp-deploy/authentik
docker compose up -d
python3 setup_authentik_oauth2.py --authentik-url http://localhost:9000 --bootstrap-token akadmin:insecure
```

3. Update frontend .env:
```env
VITE_OIDC_DISCOVERY_URL=http://localhost:9000/application/o/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=nak-planner-frontend
```

4. Restart frontend:
```bash
cd services/frontend
bun run dev
```

5. Test login - should work identically

## Choosing an IDP

### Choose Keycloak if you:
- Need a mature, battle-tested solution
- Require comprehensive admin features
- Have Java infrastructure
- Need SAML support (in addition to OIDC)
- Want extensive customization options

### Choose Authentik if you:
- Prefer Python/modern tech stack
- Have limited server resources
- Want a simpler, faster setup
- Need a modern admin UI
- Prefer lighter-weight deployments

## Network Configuration

Both IDPs create a local network for multi-container coordination:

### Keycloak Network
```yaml
networks:
  idp_net:
    driver: bridge
```

Containers:
- `keycloak`: Main service (8080)
- `keycloak-db`: PostgreSQL database

### Authentik Network
```yaml
networks:
  idp_net:
    driver: bridge
```

Containers:
- `authentik`: Main service (9000)
- `authentik-worker`: Job processor
- `authentik-postgres`: PostgreSQL database
- `authentik-redis`: Redis cache

## Traefik Integration

Both IDPs can be integrated with Traefik reverse proxy for production:

```yaml
# docker-compose.override.yml for production
services:
  keycloak:  # or authentik
    networks:
      - traefik_net
    labels:
      - traefik.enable=true
      - traefik.docker.network=traefik_net
      - traefik.http.routers.idp.rule=Host(`auth.example.com`)
      - traefik.http.routers.idp.entrypoints=websecure
      - traefik.http.routers.idp.tls.certresolver=letsencrypt
```

## Monitoring

### Check Status
```bash
# Keycloak
docker compose -f idp-deploy/keycloak/docker-compose.yml ps
docker compose -f idp-deploy/keycloak/docker-compose.yml logs -f keycloak

# Authentik
docker compose -f idp-deploy/authentik/docker-compose.yml ps
docker compose -f idp-deploy/authentik/docker-compose.yml logs -f authentik
```

### Health Checks
```bash
# Keycloak
curl http://localhost:8080/health/ready

# Authentik
curl http://localhost:9000/-/health/live/
```

### Database Status
```bash
# Keycloak
docker compose -f idp-deploy/keycloak/docker-compose.yml exec keycloak-db psql -U keycloak -c "SELECT version();"

# Authentik
docker compose -f idp-deploy/authentik/docker-compose.yml exec authentik-postgres psql -U authentik -c "SELECT version();"
```

## Backup & Restore

### Keycloak Backup
```bash
cd idp-deploy/keycloak
docker compose exec keycloak-db pg_dump -U keycloak keycloak > backup.sql
docker compose exec keycloak-db pg_restore -U keycloak keycloak < backup.sql
```

### Authentik Backup
```bash
cd idp-deploy/authentik
docker compose exec authentik-postgres pg_dump -U authentik authentik > backup.sql
docker compose exec authentik-postgres pg_restore -U authentik authentik < backup.sql
```

## Troubleshooting

### IDP not responding
```bash
# Check if containers are running
docker compose ps

# Check logs
docker compose logs -f

# Restart services
docker compose restart
```

### Frontend can't reach IDP
```bash
# Ensure VITE_OIDC_DISCOVERY_URL is correct
echo $VITE_OIDC_DISCOVERY_URL

# Test discovery endpoint
curl $VITE_OIDC_DISCOVERY_URL

# Check frontend .env
cat services/frontend/.env.local
```

### User can't login
```bash
# Verify test user exists
# Keycloak: Admin Console → Users
# Authentik: Admin Console → Users

# Check IDP logs
docker compose logs <service> | grep -i error

# Verify redirect URI
# Keycloak: Admin Console → Clients → nak-planner-frontend
# Authentik: Admin Console → Providers → [Provider]
```

## More Information

- **Keycloak Setup**: See `idp-deploy/keycloak/OIDC-SETUP.md`
- **Authentik Setup**: See `idp-deploy/authentik/OIDC-SETUP.md`
- **Frontend OIDC**: See `services/frontend/README.md`
- **Frontend Composables**: See `services/frontend/src/composables/useOIDC.ts`
