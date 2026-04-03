## Why

Der NAK Bezirksplaner ist bisher nur über einen einzelnen gemeinsamen API-Key gesichert — für einen Produktionsbetrieb mit mehreren Bezirken und Benutzern mit unterschiedlichen Verantwortlichkeiten ist das unzureichend. Persönliche Benutzerkonten, granulare Rollen und sofort wirksame Berechtigungsänderungen sind Voraussetzung für einen sicheren Mehrmandanten-Betrieb.

## What Changes

- **Keycloak** als Identity Provider: JWT-Validierung via JWKS im Backend; Passwörter liegen ausschließlich in Keycloak
- Social-Login über Keycloak (Google, Microsoft OAuth2)
- Neues Datenbankmodell: `User` (`keycloak_sub`, `email`, `display_name`, `district_id`, `is_active`) und `UserRole` (`user_id`, `role`, `congregation_id`)
- Rollen: `system_admin`, `district_admin`, `congregation_admin`, `planner`, `viewer`
- Rollen-Speicherung **ausschließlich** in der DB (`UserRole`); JWT enthält nur Identität (`sub`, `email`)
- Redis-Cache für Rollen pro Request (TTL 60 s, aktive Invalidierung bei Rollenänderung)
- FastAPI-Dependency `require_role(...)` ersetzt den bestehenden `verify_api_key`-Guard
- Audit-Log-Tabelle für sicherheitsrelevante Aktionen
- Einladungsworkflow über Keycloak (E-Mail-Einladung, Selbstregistrierung mit Freigabe)
- **BREAKING**: `X-API-Key`-Header entfällt für alle `/api/v1/`-Endpunkte; stattdessen `Authorization: Bearer <JWT>`

## Capabilities

### New Capabilities

- `jwt-auth`: JWT-Validierung via Keycloak JWKS, Bearer-Token-Dependency für FastAPI-Routen
- `role-access-control`: Rollenbasierte Zugriffskontrolle mit DB-gespeicherten Rollen, Redis-Cache und FastAPI-Permission-Guards
- `user-management`: CRUD für Benutzer und Rollenzuweisung; Einladungsworkflow; Benutzer deaktivieren; Audit-Log

### Modified Capabilities

<!-- keine bestehenden Specs vorhanden -->

## Impact

- **Backend:** Neue Tabellen `user`, `user_role`, `audit_log`; neue Adapters `adapters/auth/keycloak.py`; neue Dependencies; Alembic-Migrationen
- **Frontend:** Login-Redirect zu Keycloak, Token-Speicherung (localStorage/Cookie), Auth-Store in Pinia, Route Guards
- **Infrastruktur:** Keycloak-Instanz im Docker-Compose (oder externer Keycloak-Server); neue Umgebungsvariablen (`KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`)
- **Breaking Change**: Bestehende API-Key-Authentifizierung wird entfernt; alle API-Clients müssen auf JWT umgestellt werden
- **Abhängigkeiten:** `python-jose[cryptography]` oder `authlib` für JWT-Validierung
