# Authentik OIDC Setup

Authentik is a modern, lightweight identity provider with built-in OIDC/OAuth2 support. This directory contains everything needed to deploy and configure Authentik for NAK Planner.

## Quick Start (5 minutes)

```bash
# 1. Start Authentik (server + worker + postgres + redis)
docker compose up -d

# 2. Wait for it to be ready (check logs)
docker compose logs -f authentik | grep "Started"

# 3. Setup OAuth2 provider and application
python3 setup_authentik_oauth2.py --authentik-url http://localhost:9000 \
  --bootstrap-token akadmin:insecure

# 4. Copy OIDC settings from script output to frontend .env.local
# 5. Start frontend and test at http://localhost:5173/login
```

## Files

- **docker-compose.yml** — Production-ready Authentik with all services
- **setup_authentik_oauth2.py** — Automated OAuth2 provider setup
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

## Next Steps

1. Review OIDC-SETUP.md for complete guide
2. Run setup script
3. Configure frontend .env.local
4. Test login flow
5. Deploy to production

## Questions?

See troubleshooting in OIDC-SETUP.md
