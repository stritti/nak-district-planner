## Context

Die Anwendung ist bisher über einen statischen `X-API-Key`-Header gesichert (`verify_api_key`-Dependency). Phase 4 ersetzt diesen Guard vollständig durch JWT-basierte Authentifizierung via Keycloak und eine rollenbasierte Zugriffskontrolle (RBAC) auf Basis des vollständig ausgearbeiteten Rollenkonzepts in `docs/roles.md`.

Das Rollenkonzept wurde bereits im Detail analysiert und alle Designentscheidungen sind getroffen (siehe `docs/roles.md`, Abschnitt 5).

## Goals / Non-Goals

**Goals:**
- Keycloak als externer Identity Provider; JWT-Validierung via JWKS-Endpoint im Backend
- Datenbankmodelle `User` und `UserRole` (partielle Unique-Indizes für saubere Constraint-Durchsetzung)
- FastAPI-Dependency `require_role(role, district_id?, congregation_id?)` als Ersatz für `verify_api_key`
- Redis-Cache für geladene Rollen (TTL 60 s, aktive Invalidierung bei Änderung)
- CRUD-Endpoints für Benutzerverwaltung und Rollenzuweisung
- Audit-Log-Tabelle für sicherheitsrelevante Aktionen
- Keycloak im Docker-Compose für lokale Entwicklung
- Frontend: Keycloak-JS-Adapter, Auth-Store (Pinia), Route Guards

**Non-Goals:**
- Eigenes Passwort-Management im Backend
- SAML-Support
- Multifaktor-Authentifizierung (Keycloak-Konfiguration, nicht Backend-Code)
- Feinkörnige Feld-Level-Berechtigungen

## Decisions

### DB-only Rollen (keine Rollen im JWT)
**Entscheidung:** Rollen werden ausschließlich in der `UserRole`-Tabelle gespeichert. Das JWT enthält nur `sub` und `email`. Rollen werden per DB-Lookup (mit Redis-Cache) ermittelt.

**Begründung:** Sofortige Wirksamkeit bei Rollenänderungen. Ein entzogenes Recht gilt innerhalb von 60 Sekunden, nicht erst nach Token-Ablauf (15 min). Für einen Kirchenbezirksplaner (nicht hochfrequentes System) ist der Redis-Cache-Overhead vernachlässigbar. (Vollständige Begründung: `docs/roles.md` Abschnitt 4.3)

Alternativen: JWT-Claims mit Rollen (15-min-Lag bei Rollenänderung → Sicherheitsrisiko), Hybrid (zwei Wahrheitsquellen → Komplexität).

### Partielle Unique-Indizes statt UNIQUE-Constraint
**Entscheidung:** Zwei partielle Indizes auf `user_role`:
- `WHERE congregation_id IS NULL` für bezirksweite Rollen
- `WHERE congregation_id IS NOT NULL` für gemeindebezogene Rollen

**Begründung:** PostgreSQL behandelt `NULL ≠ NULL`, daher erlaubt ein einfacher UNIQUE-Constraint mehrere Zeilen mit `congregation_id = NULL`. Partielle Indizes sind die korrekte Lösung.

### `require_role`-Dependency
**Entscheidung:** `require_role(required_role: Role, district_id: UUID | None = None)` als FastAPI-Dependency-Funktion. Gibt den verifizierten `User` zurück oder wirft HTTP 403.

**Begründung:** Konsistentes Muster analog zu bestehendem `verify_api_key`. Gut testbar über `override_dependency`.

### Keycloak im Docker-Compose
**Entscheidung:** Keycloak 24+ als zusätzlicher Service im `docker-compose.yml`. Realm-Konfiguration als exportiertes JSON eingecheckt (`infrastructure/keycloak/realm-export.json`).

**Begründung:** Lokale Entwicklung ohne externen Keycloak-Server. Für Produktion: externer Keycloak via Umgebungsvariablen.

## Risks / Trade-offs

- [Risiko] Keycloak-Ausfall → kein Login möglich → **Mitigation:** Keycloak hat eigenen HA-Modus; für MVP Single-Node akzeptabel
- [Risiko] Key-Rotation bei JWKS → kurzer Validierungsfehler → **Mitigation:** JWKS wird gecacht (TTL 1 h), Keycloak rotiert Keys überlappend
- [Trade-off] Breaking Change: bestehender API-Key-Flow entfällt → alle Clients müssen migriert werden → dokumentierter Migrationspfad, kein paralleler Betrieb beider Auth-Methoden
- [Trade-off] Redis-Abhängigkeit für Rollen-Cache → bei Redis-Ausfall: Fallback auf direkten DB-Lookup (akzeptable Performance-Degradation)

## Migration Plan

1. Alembic-Migrationen: `user`, `user_role`, `audit_log` Tabellen
2. Keycloak-Service in `docker-compose.yml`, Realm-Export einchecken
3. JWT-Validierung implementieren (`adapters/auth/keycloak.py`)
4. `require_role`-Dependency implementieren + Redis-Cache
5. Alle bestehenden `/api/v1/`-Routen von `verify_api_key` auf `require_role` umstellen
6. Benutzer-/Rollenverwaltungs-Endpoints implementieren
7. Audit-Log-Middleware
8. Frontend: Keycloak-JS, Auth-Store, Route Guards
9. Rollback: Feature-Flag `AUTH_MODE=api_key|jwt` für Übergangsphase (optional)
