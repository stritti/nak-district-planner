# Keycloak OIDC Setup

Keycloak is a mature, open-source identity and access management platform. This directory contains everything needed to deploy and configure Keycloak for NAK Planner.

## Quick Start (5 minutes)

```bash
# 1. Start Keycloak
docker compose up -d

# 2. Wait for it to be ready (check logs)
docker compose logs -f keycloak | grep "Started"

# 3. Setup realm and OIDC client
python3 setup_keycloak_realm.py --keycloak-url http://localhost:8080 \
  --admin-password admin_dev_pw

# 4. Copy OIDC settings from script output to frontend .env.local
# 5. Start frontend and test at http://localhost:5173/login
```

## Files

- **docker-compose.yml** — Production-ready Keycloak + PostgreSQL
- **setup_keycloak_realm.py** — Automated OIDC realm setup
- **deploy_keycloak.sh** — VPS deployment script
- **OIDC-SETUP.md** — Complete guide with troubleshooting
- **.env.example** — Environment configuration template

## Documentation

Start with **OIDC-SETUP.md** for comprehensive guide including:
- Development setup
- Production deployment
- Realm management
- User management
- Troubleshooting

## Configuration

Edit `.env` before starting:

```env
KEYCLOAK_DB_PASSWORD=changeme
KC_BOOTSTRAP_ADMIN_PASSWORD=changeme
KC_HOSTNAME=localhost
```

Generate strong passwords:
```bash
openssl rand -base64 16
```

## Admin Console

Access at: http://localhost:8080/admin/
- Username: admin
- Password: (from .env KC_BOOTSTRAP_ADMIN_PASSWORD)

## OIDC Integration

Once setup is complete, frontend uses:
- Discovery: http://localhost:8080/realms/nak-planner/.well-known/openid-configuration
- Client ID: nak-planner-frontend
- Client Type: Public (PKCE)

## Production

See OIDC-SETUP.md section "Production Deployment (VPS)" for:
- Full deployment guide
- Traefik integration
- SSL certificate setup
- Monitoring

Or run automated script:
```bash
./deploy_keycloak.sh /opt/keycloak https://auth.example.com your_password
```

## Logs

```bash
docker compose logs -f keycloak     # Live logs
docker compose logs keycloak | grep ERROR  # Errors only
```

## Health Check

```bash
curl http://localhost:8080/health/ready
# Should return 200 when ready
```

## Next Steps

1. Review OIDC-SETUP.md for complete guide
2. Run setup script
3. Configure frontend .env.local
4. Test login flow
5. Deploy to production

## Questions?

See troubleshooting in OIDC-SETUP.md
