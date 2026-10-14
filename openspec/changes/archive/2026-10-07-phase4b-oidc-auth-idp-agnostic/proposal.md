## Why

Phase 4a implementierte JWT-Authentifizierung spezifisch für Keycloak. Damit NAK District Planner flexibel verschiedene Identity Provider (Keycloak, Authentik, Okta, etc.) unterstützen kann und nicht an ein spezifisches System gebunden ist, müssen wir die Implementierung auf Standard OIDC/OAuth2 umstellen. Dies ermöglicht gleichzeitig die Nutzung im produktiven VPN-Umfeld mit Authentik als IDP.

## What Changes

- **OIDC-Standard-Stack:** Backend nutzt `authlib` statt Keycloak-spezifischer Libraries → unterstützt jeden OIDC Provider
- **Frontend IDP-Agnostig:** `vuejs-oauth2` oder `@vueuse/core` statt `keycloak-js` → funktioniert mit jedem OIDC Provider
- **Konfiguration flexibel:** ENV-Variablen für `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` (nicht Keycloak-spezifisch)
- **Mehrere IDPs:** Deployments können Keycloak OR Authentik OR anderen Provider nutzen ohne Code-Änderungen
- **BREAKING:** Alte Keycloak-spezifischen Env-Vars (`KEYCLOAK_URL`, `KEYCLOAK_REALM`) entfallen → neue `OIDC_*` Vars
- **JWT-Validierung identisch:** JWKS-Fetch und Token-Validierung funktioniert identisch für alle OIDC Provider

## Capabilities

### New Capabilities
- `oidc-integration`: Standard OIDC/OAuth2 Integration mit Provider-Discovery, JWKS-Validierung, beliebigem IDP
- `oidc-frontend-auth`: Vue 3 OIDC Login/Logout-Flow mit Standard-OIDC Libraries, Token-Management, Auto-Refresh
- `idp-configuration`: Setup-Guides für Keycloak und Authentik mit identischen Anforderungen

### Modified Capabilities
- `jwt-auth`: Wird zu `oidc-auth` — JWT-Validierung ist identisch, aber Provider-agnostisch
- `user-management-basic`: User-Auto-Create funktioniert mit Standard OIDC Claims (`sub`, `email`)
- `api-security`: Bearer Token Authorization bleibt identisch, nur Quelle ändert sich (beliebiger OIDC Provider)

## Impact

**Backend:**
- Dependencies: `authlib` (statt `python-jose` + Keycloak-spezifisch)
- `OIDCAdapter` (statt `KeycloakAdapter`) in `adapters/auth/oidc.py`
- Env-Vars: `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_SCOPES` (neu)
- User-Model bleibt identisch
- `/auth/me`, `/auth/login-url`, `/auth/logout` Endpoints gleich

**Frontend:**
- Dependencies: `authlib` OIDC Library statt `keycloak-js`
- Initialization: Standard OIDC Discovery Flow
- Env-Vars: `VITE_OIDC_DISCOVERY_URL`, `VITE_OIDC_CLIENT_ID` (neu)

**Infrastruktur:**
- `keycloak-deploy/` wird zu `idp-deploy/` mit Sub-Directories:
  - `keycloak/docker-compose.yml` (Keycloak 26.5.6)
  - `authentik/docker-compose.yml` (Authentik latest)
- Setup-Guides für beide IDPs (identische Client-Config)

**Abhängigkeiten:**
- Backend: `authlib` + `httpx` (statt `python-jose` + Keycloak-specifics)
- Frontend: `@vueuse/core` (OIDC hooks) statt `keycloak-js`
