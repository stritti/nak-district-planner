# Keycloak Deploy

Standalone Keycloak-Stack für NAK Planner und andere Projekte.

**Keycloak** ist ein OpenID Connect / OAuth 2.0 Identity Provider. Dieser Stack ermöglicht:
- JWT-basierte Authentifizierung
- Zentrale Benutzerverwaltung
- Wiederverwendung durch mehrere Projekte
- Integration mit Traefik für TLS + Domain Management

## Quick Start

```bash
cp .env.example .env
# Bearbeite .env mit starken Passwörtern

docker compose up -d
docker compose logs -f keycloak  # Warte auf "is now running"
```

Öffne dann: `https://auth.5tritti.de/admin/`

Siehe [SETUP.md](docs/SETUP.md) für detaillierte Schritte.

## Directory Structure

```
keycloak-deploy/
├── docker-compose.yml          # Keycloak + PostgreSQL
├── .env.example                # Environment template
├── docs/
│   ├── SETUP.md               # Deployment guide
│   └── REALM-MIGRATION.md     # Realm import/export
└── config/
    └── realm-export.json      # (Optional) Realm backup
```

## Integration mit NAK Planner

Nach dem Keycloak-Setup, configure NAK Planner:

```bash
# In nak-district-planner/.env
KEYCLOAK_URL=https://auth.5tritti.de
KEYCLOAK_REALM=nak-planner
KEYCLOAK_CLIENT_ID=nak-planner-api
KEYCLOAK_CLIENT_SECRET=<copied-from-keycloak>
```

Siehe [../../openspec/changes/phase4a-jwt-auth-minimal/](../../openspec/changes/phase4a-jwt-auth-minimal/) für Backend/Frontend-Integration.

## Technische Details

- **Image:** `quay.io/keycloak/keycloak:26.5.6` (Latest)
- **Database:** PostgreSQL 15
- **Port:** 8080 (via Traefik TLS)
- **Auth:** HTTP (internal) + TLS (Traefik)
- **Networks:** `traefik` (public), `backend` (internal)

## Support

Fehler oder Fragen? Siehe:
- [Keycloak Docs](https://www.keycloak.org/documentation)
- [SETUP.md](docs/SETUP.md) Troubleshooting-Section
