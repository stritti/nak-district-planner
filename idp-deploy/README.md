# Identity Provider Deployments

This directory contains production-ready configurations for two OpenID Connect (OIDC) identity providers: **Keycloak** and **Authentik**.

Choose one based on your infrastructure preferences:

## Quick Comparison

| Aspect | Keycloak | Authentik |
|--------|----------|-----------|
| **Tech** | Java | Python/Go |
| **Memory** | 512MB+ | 256MB+ |
| **Startup** | 30-120s | 30-60s |
| **Maturity** | Very mature | Growing |
| **Best For** | Enterprises | Simple setups |

## Choose Your IDP

### Option A: Keycloak (Recommended for Enterprise)

Keycloak is a mature, feature-rich identity management platform.

**Quick Start:**
```bash
cd keycloak
docker compose up -d
python3 setup_keycloak_realm.py --keycloak-url http://localhost:8080 --admin-password admin_dev_pw
```

**Documentation:** See `keycloak/OIDC-SETUP.md`

### Option B: Authentik (Recommended for Simple Setups)

Authentik is a modern, lightweight authentication platform.

**Quick Start:**
```bash
cd authentik
docker compose up -d
python3 setup_authentik_oauth2.py --authentik-url http://localhost:9000 --bootstrap-token akadmin:insecure
```

**Documentation:** See `authentik/OIDC-SETUP.md`

## Directory Structure

```text
idp-deploy/
├── keycloak/
│   ├── docker-compose.yml              # Container configuration
│   ├── .env.example                    # Environment template
│   ├── setup_keycloak_realm.py         # Automated setup
│   ├── deploy_keycloak.sh              # VPS deployment script
│   ├── OIDC-SETUP.md                   # Complete guide
│   ├── README.md                       # Keycloak-specific README
│   └── docs/                           # Additional documentation
│
├── authentik/
│   ├── docker-compose.yml              # Container configuration
│   ├── .env.example                    # Environment template
│   ├── setup_authentik_oauth2.py       # Automated setup
│   ├── deploy_authentik.sh             # VPS deployment script
│   ├── OIDC-SETUP.md                   # Complete guide
│   └── README.md                       # Authentik-specific README
│
├── CONFIGURATION.md                    # IDP comparison & setup
├── test-oidc-integration.sh            # Integration test script
└── README.md                           # This file
```

## What You'll Need

### For Development
- Docker & Docker Compose
- Python 3.11+ (for setup scripts)
- bash (for deployment scripts)
- Frontend: bun (or npm)

### For Production
- VPS with Docker & Docker Compose
- Domain name (e.g., auth.example.com)
- SSL certificate (Let's Encrypt)
- 512MB+ RAM (Keycloak) or 256MB+ RAM (Authentik)

## Setup Steps

### 1. Choose an IDP
Both Keycloak and Authentik are included. Pick one:
- **Keycloak**: More features, heavier
- **Authentik**: Simpler, lighter

### 2. Configure Environment
```bash
# For Keycloak
cd keycloak
cp .env.example .env
# Edit .env and set passwords

# For Authentik
cd authentik
cp .env.example .env
# Edit .env and set secret key
```

### 3. Start IDP
```bash
docker compose up -d
```

### 4. Run Setup Script
```bash
# For Keycloak
python3 setup_keycloak_realm.py --keycloak-url http://localhost:8080 --admin-password admin_dev_pw

# For Authentik
python3 setup_authentik_oauth2.py --authentik-url http://localhost:9000 --bootstrap-token akadmin:insecure
```

### 5. Configure Frontend
Copy OIDC settings from script output to `services/frontend/.env.local`:

```env
VITE_OIDC_DISCOVERY_URL=<discovery_url_from_script>
VITE_OIDC_CLIENT_ID=nak-planner-frontend
VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback
```

### 6. Start Frontend
```bash
cd services/frontend
bun run dev
```

### 7. Test Login
Open <http://localhost:5173/login> and test the OIDC flow.

## Production Deployment

### Keycloak Production
```bash
bash keycloak/deploy_keycloak.sh /opt/keycloak https://auth.example.com your_admin_password
```

### Authentik Production
```bash
SECRET_KEY=$(openssl rand -base64 32)
bash authentik/deploy_authentik.sh /opt/authentik https://auth.example.com "$SECRET_KEY"
```

## Validation

Test OIDC integration:
```bash
bash test-oidc-integration.sh keycloak    # or authentik
```

Expected output:
```text
✓ IDP is healthy
✓ Discovery configuration found
✓ JWKS endpoint functional
✓ All checks passed
```

## Common Issues

### IDP not starting
```bash
# Check logs
docker compose logs -f keycloak    # or authentik

# Ensure ports are free
lsof -i :8080    # Keycloak
lsof -i :9000    # Authentik
```

### OIDC discovery fails
```bash
# Verify IDP is healthy
curl http://localhost:8080/health/ready       # Keycloak
curl http://localhost:9000/-/health/live/     # Authentik
```

### Login redirect fails
```bash
# Check frontend .env.local
cat services/frontend/.env.local

# Ensure VITE_OIDC_REDIRECT_URI matches browser URL
# If frontend on different port/domain, update setup script with correct URL
```

## Documentation

- **CONFIGURATION.md** — IDP comparison, endpoint reference, Traefik integration
- **keycloak/OIDC-SETUP.md** — Keycloak complete setup guide
- **authentik/OIDC-SETUP.md** — Authentik complete setup guide
- **../MIGRATION_GUIDE.md** — Phase 4a → 4b migration path

## Switching Between IDPs

Want to try the other IDP?

```bash
# Stop current IDP
cd keycloak   # or authentik
docker compose down

# Start new IDP
cd ../authentik   # or ../keycloak
docker compose up -d
python3 setup_*.py ...

# Update frontend .env.local with new OIDC settings
# Restart frontend
```

The OIDC flow is identical for both, so no code changes needed.

## Next Steps

1. **Choose IDP** — Keycloak or Authentik
2. **Follow setup guide** — keycloak/OIDC-SETUP.md or authentik/OIDC-SETUP.md
3. **Test locally** — Run E2E tests with `test-oidc-integration.sh`
4. **Deploy to production** — Use deployment scripts or docker compose

## Support

For help with specific IDP:
- **Keycloak:** See `keycloak/OIDC-SETUP.md` troubleshooting section
- **Authentik:** See `authentik/OIDC-SETUP.md` troubleshooting section

For OIDC implementation details:
- See `../docs/security-baseline.md`
- See `../docs/documentation-map.md`
- See `../MIGRATION_GUIDE.md` (Phase 4a -> 4b migration)
