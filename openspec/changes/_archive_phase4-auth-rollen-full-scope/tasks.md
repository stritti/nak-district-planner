## 1. Infrastruktur & Konfiguration

- [ ] 1.1 Keycloak-Service in `docker-compose.yml` ergänzen (Image: `quay.io/keycloak/keycloak:24`, Port 8080)
- [ ] 1.2 Keycloak-Realm-Konfiguration als JSON exportieren und in `infrastructure/keycloak/realm-export.json` einchecken
- [ ] 1.3 Umgebungsvariablen ergänzen: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`
- [ ] 1.4 `.env.example` aktualisieren

## 2. Datenbankschema

- [ ] 2.1 Alembic-Migration: Tabelle `user` (id, keycloak_sub UNIQUE, email, display_name, district_id, is_active, created_at)
- [ ] 2.2 Alembic-Migration: Tabelle `user_role` (id, user_id FK, role ENUM, congregation_id nullable FK)
- [ ] 2.3 Alembic-Migration: Partielle Unique-Indizes auf `user_role` (bezirksweit + gemeindebezogen)
- [ ] 2.4 Alembic-Migration: Tabelle `audit_log` (id, timestamp, user_id FK, action ENUM, resource_type, resource_id, district_id, congregation_id, details JSONB)
- [ ] 2.5 SQLAlchemy-Modelle für alle drei Tabellen erstellen

## 3. JWT-Authentifizierung (Backend)

- [ ] 3.1 `KeycloakAdapter` in `adapters/auth/keycloak.py` implementieren (JWKS-Fetch, Token-Validierung via `python-jose`)
- [ ] 3.2 JWKS-Cache mit TTL 1 h implementieren
- [ ] 3.3 FastAPI-Dependency `get_current_user()` implementieren (JWT decodieren → User in DB suchen/anlegen)
- [ ] 3.4 Automatische User-Anlage beim ersten Login implementieren
- [ ] 3.5 Unit-Tests für Token-Validierung (valide, abgelaufen, falscher Issuer)

## 4. Rollenbasierte Zugriffskontrolle

- [ ] 4.1 `RoleService` in `application/services/role_service.py` implementieren (Rollen aus DB laden mit Redis-Cache TTL 60 s)
- [ ] 4.2 Cache-Invalidierung bei Rollenänderungen implementieren
- [ ] 4.3 Fallback auf direkten DB-Lookup bei Redis-Ausfall
- [ ] 4.4 FastAPI-Dependency `require_role(role, district_id?, congregation_id?)` implementieren
- [ ] 4.5 Unit-Tests für `require_role` (alle Rollen, Grenzen, deaktivierter User)

## 5. Bestehende Routes migrieren

- [ ] 5.1 `verify_api_key`-Dependency aus allen `/api/v1/`-Routen entfernen
- [ ] 5.2 `require_role(...)`-Dependency auf alle Routen entsprechend Berechtigungsmatrix in `docs/roles.md` anwenden
- [ ] 5.3 `/api/health`-Endpoint bleibt ungesichert (keine Änderung nötig)
- [ ] 5.4 Alle bestehenden Integrations-Tests auf JWT-Auth umstellen (Test-Client mit Mock-JWT)

## 6. Benutzerverwaltungs-Endpoints

- [ ] 6.1 `GET /api/v1/users/me` implementieren
- [ ] 6.2 `GET /api/v1/districts/{id}/users` implementieren (nur district_admin + system_admin)
- [ ] 6.3 `PATCH /api/v1/users/{id}/roles` implementieren (add/remove Rolle, Cache-Invalidierung)
- [ ] 6.4 `PATCH /api/v1/users/{id}` implementieren (is_active, Cache-Invalidierung)
- [ ] 6.5 Audit-Log-Middleware für Rollenvergabe/-entzug und Benutzer-Deaktivierung

## 7. Frontend

- [ ] 7.1 `keycloak-js`-Bibliothek installieren (`bun add keycloak-js`)
- [ ] 7.2 Keycloak-Initialisierung in `main.ts` (Login-Redirect vor App-Mount)
- [ ] 7.3 Pinia-Store `useAuthStore` erstellen (User, Rollen, Token, logout)
- [ ] 7.4 Route Guards in Vue Router: unauthentifizierte Requests → Keycloak-Login-Redirect
- [ ] 7.5 Automatische Token-Erneuerung (Keycloak-JS `onTokenExpired`-Hook)
- [ ] 7.6 Benutzerverwaltungs-UI: Benutzer auflisten, Rollen zuweisen/entziehen (nur für district_admin)
