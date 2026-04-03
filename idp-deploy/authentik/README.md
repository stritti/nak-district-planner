# Authentik OIDC Setup

Authentik is a modern, lightweight identity provider with built-in OIDC/OAuth2 support. This directory contains everything needed to deploy and configure Authentik for NAK Planner.

## Quick Start (5 minutes) — Using Blueprint

```bash
# 1. Start Authentik (server + worker + postgres + redis)
docker compose up -d

# 2. Wait for it to be ready (check logs)
docker compose logs -f authentik | grep "Started"

# 3. Import and apply blueprint
pip install pyyaml requests  # If needed
python3 import_blueprint.py \
  --authentik-url http://localhost:9000 \
  --token akadmin:insecure \
  --blueprint-file blueprint-nak-planner.yaml \
  --apply

# 4. Copy OIDC settings to frontend .env.local:
#    VITE_OIDC_DISCOVERY_URL=http://localhost:9000/application/o/.well-known/openid-configuration
#    VITE_OIDC_CLIENT_ID=nak-planner-frontend
#    VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback

# 5. Start frontend and test at http://localhost:5173/login
#    Login with: testuser / testpassword123
```

## Blueprint vs. Manual Setup

**Using Blueprint (Recommended):**
- Declarative configuration as code
- Version controllable
- Reproducible across environments
- Easy to customize via context overrides
- Single import command

**Manual Setup (Legacy):**
- Step-by-step via admin console
- More control over each step
- Useful for troubleshooting
- See `setup_authentik_oauth2.py` for Python API examples

## Files

- **docker-compose.yml** — Production-ready Authentik with all services
- **blueprint-nak-planner.yaml** — Complete Authentik configuration as code (Blueprint)
- **import_blueprint.py** — Python script to import blueprint programmatically
- **setup_authentik_oauth2.py** — Automated OAuth2 provider setup (legacy, use blueprint instead)
- **deploy_authentik.sh** — VPS deployment script
- **OIDC-SETUP.md** — Complete guide with troubleshooting
- **.env.example** — Environment configuration template

## Documentation

Start with **OIDC-SETUP.md** for comprehensive guide including:
- Development setup
- Production deployment
- Admin console access
- User management
- Troubleshooting

## Configuration

Edit `.env` before starting:

```env
AUTHENTIK_POSTGRES_PASSWORD=changeme
AUTHENTIK_SECRET_KEY=generatewith: openssl rand -base64 32
```

Generate strong secret key:
```bash
openssl rand -base64 32
```

## Admin Console

Access at: http://localhost:9000/if/admin/
- Username: akadmin
- Password: insecure (default, CHANGE IN PRODUCTION)

## OIDC Integration

Once setup is complete, frontend uses:
- Discovery: http://localhost:9000/application/o/.well-known/openid-configuration
- Client ID: nak-planner-frontend
- Client Type: Public (PKCE)

## Services

docker compose starts:
- **authentik** — Main OIDC/OAuth2 provider (port 9000)
- **authentik-worker** — Background job processor
- **authentik-postgres** — PostgreSQL database
- **authentik-redis** — Redis cache

All services must be running for full functionality.

## Production

See OIDC-SETUP.md section "Production Deployment (VPS)" for:
- Full deployment guide
- Traefik integration
- SSL certificate setup
- Monitoring

Or run automated script:
```bash
SECRET_KEY=$(openssl rand -base64 32)
./deploy_authentik.sh /opt/authentik https://auth.example.com "$SECRET_KEY"
```

## Logs

```bash
docker compose logs -f authentik        # Main service
docker compose logs -f authentik-worker # Background jobs
docker compose logs authentik | grep ERROR  # Errors only
```

## Health Check

```bash
curl http://localhost:9000/-/health/live/
# Should return 204 when ready
```

## Blueprint Customization

Override blueprint context values:

```bash
# Custom frontend URL
python3 import_blueprint.py \
  --authentik-url http://localhost:9000 \
  --token akadmin:insecure \
  --blueprint-file blueprint-nak-planner.yaml \
  --context frontend_url http://myapp.example.com \
  --context provider_name "My Custom Provider" \
  --apply

# Multiple redirect URIs are supported in blueprint
```

## Next Steps

1. **Quick Start**: Use Blueprint import (see above)
2. **Review**: See OIDC-SETUP.md for complete guide
3. **Production**: See OIDC-SETUP.md section "Production Deployment"
4. **Troubleshooting**: See OIDC-SETUP.md Troubleshooting section

## Advanced: Blueprint Management

```bash
# List imported blueprints
python3 import_blueprint.py \
  --authentik-url http://localhost:9000 \
  --token akadmin:insecure \
  --list

# Apply blueprint manually (via CLI)
# Usually done automatically, but you can re-apply:
python3 import_blueprint.py \
  --authentik-url http://localhost:9000 \
  --token akadmin:insecure \
  --apply
```

## Blueprint Anatomy

The blueprint creates:

1. **OIDC Provider** — `NAK Planner OIDC` with PKCE support
2. **OAuth2 Application** — Links provider to users
3. **Authorization Flow** — Handles OAuth2 redirect/consent
4. **Test User** — `testuser` / `testpassword123`
5. **Application Group** — `nak-planner-users` for access control
6. **Access Policy** — Allows authenticated users (customizable)

See `blueprint-nak-planner.yaml` for complete configuration.

## Questions?

See troubleshooting in OIDC-SETUP.md
