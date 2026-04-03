## Why

Die aktuelle API-Key-Authentifizierung (`X-API-Key` Header) ist unsicher für einen Multi-Tenant-Betrieb mit mehreren Nutzern und Bezirken. JWT-basierte Authentifizierung mit Keycloak ermöglicht benutzerbasierte Zugriffskontrolle und ist Standard für produktive Web-APIs. Dies ist Voraussetzung für Deployment auf der produktiven Domain 5tritti.de.

## What Changes

- **Keycloak-Stack:** Separate `docker-compose.yml` mit Keycloak 24, PostgreSQL-DB und Traefik-Labels für `https://auth.5tritti.de`
- **JWT-Validierung:** Backend validiert Bearer-Token via Keycloak JWKS (keine lokale Secret-Verwaltung)
- **User-Modell:** Tabelle `user` speichert Keycloak-Sub, Email, Displayname (Auto-Create on first login)
- **Login-Flow:** Frontend leitet zu Keycloak-Login-Seite um, erhält JWT, speichert Token in localStorage
- **Token-Refresh:** Automatische Token-Erneuerung vor Ablauf
- **Logout:** Logout-Endpoint für Keycloak-Session-Beendigung
- **BREAKING:** `X-API-Key`-Header entfällt; stattdessen `Authorization: Bearer <JWT>`
- **Gesicherte Endpunkte:** Alle `/api/v1/`-Routen erfordern gültigen JWT (außer `/api/health`)

## Capabilities

### New Capabilities
- `jwt-auth`: JWT-Validierung via Keycloak JWKS, Keycloak-Adapter mit Token-Caching
- `user-management-basic`: Auto-Create User on first login, GET /auth/me Endpoint
- `auth-flow`: Login-Redirect zu Keycloak, Callback-Handling, Token-Storage, Logout

### Modified Capabilities
- `api-security`: Authentifizierung wechselt von API-Key zu JWT (Breaking Change)

## Impact

**Backend:**
- Neue Tabelle `user` (Alembic-Migration)
- Neue Dependency `get_current_user()` in `adapters/api/deps.py`
- `KeycloakAdapter` in `adapters/auth/keycloak.py` (JWKS-Fetch, Token-Validierung)
- Alle `/api/v1/`-Routen nutzen `get_current_user` statt `verify_api_key`
- Neue Env-Vars: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`

**Frontend:**
- `keycloak-js` Library Integration
- Keycloak-Initialisierung vor App-Mount
- Auth-Store in Pinia (`useAuthStore`)
- Route Guards für unauthentifizierte Requests
- Token-Erneuerung via `onTokenExpired`-Hook

**Infrastruktur:**
- Separate Keycloak-Stack (`keycloak-deploy/docker-compose.yml` oder ähnlich)
- Keycloak nutzt externe PostgreSQL-DB
- Traefik-Labels für `auth.5tritti.de`
- Dokumentation: Setup-Guide, Realm-Export, Env-Template

**Abhängigkeiten:**
- `python-jose[cryptography]` (JWT-Validierung)
- `keycloak-js` (Frontend)
