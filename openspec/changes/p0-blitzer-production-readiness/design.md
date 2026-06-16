## Context

Der NAK District Planner hat eine solide RBAC-Grundlage (`permissions.py`, `Membership`-Modell, Access-Guard). Zwei der drei P0-Lücken aus der Analyse sind bereits strukturell adressiert, aber nicht konsistent ausgerollt:

- Die `approved-idp-login-scoped-access`-Changes haben den `require_membership_access`-Guard und `assert_has_role_in_district`/`assert_has_role_in_congregation` eingeführt.
- Die `introduce-rbac-permissions-model`-Changes haben `Role`-Enum, `Membership`-Entity und Permission-Utilities definiert.
- **Was fehlt:** Systematische Audit-Prüfung, dass *jeder* Router die Guards korrekt setzt, congregation-level scoping, und Tests, die Mandantengrenzen nachweisen.
- **Was komplett fehlt:** Production Guard beim Start.

## Goals / Non-Goals

**Goals:**
- `APP_ENV=production` startet nie mit unsicheren Defaults.
- Jeder geschützte Endpoint hat einen dokumentierten Permission-Guard.
- Jeder geschützte Endpoint hat mindestens einen Negativtest (403 bei falscher Rolle).
- Ein User aus Bezirk A kann keine Daten aus Bezirk B lesen, schreiben, aktualisieren oder löschen (durch Tests nachgewiesen).
- `CONGREGATION_ADMIN` ist auf die eigene Gemeinde beschränkt.

**Non-Goals:**
- Kein neues Rollenmodell – bestehendes RBAC wird nur vervollständigt.
- Kein neuer Policy-Layer – Guards bleiben deklarativ in den Routern/App-Services.
- Kein UI-Override – Backend ist die autoritative Enforcement-Ebene.

## Decisions

### Decision 1: Production Guard als zentrale Startup-Funktion

**Entscheidung:** `config.py` erhält eine `production_guard(settings: Settings)`-Funktion, die im `lifespan`-Event von FastAPI vor dem Start aufgerufen wird.

**Prüfungen:**
| Prüfung | Bedingung | Fehler |
|---------|-----------|--------|
| `SECRET_KEY` | nicht `replace-with-*` / `< 32 Zeichen` | `CRITICAL: Default Secret Key` |
| `OIDC_CLIENT_SECRET` | nicht leer / nicht Platzhalter | `CRITICAL: Default OIDC Secret` |
| `APP_ENV` | `production` + `DEBUG=true` | `CRITICAL: Debug Mode enabled` |
| `CORS_ORIGINS` | `["*"]` | `CRITICAL: CORS wildcard` |
| `OIDC_REDIRECT_URIS` | nicht HTTPS in production | `WARNING: Non-HTTPS redirect` |

**Rationale:** Zentrale Prüfung verhindert, dass beim Hinzufügen neuer Konfigurationswerte die Sicherheitsprüfung vergessen wird. Jede neue Config-Variable mit Sicherheitsrelevanz muss explizit in `production_guard` aufgenommen oder als `SAFE_BY_DEFAULT` markiert werden.

### Decision 2: Router-Audit nach Permission-Matrix aus `docs/roles.md`

**Entscheidung:** Alle Router werden gegen die 185-Zellen-Permission-Matrix aus `docs/roles.md` geprüft. Für jede Route wird dokumentiert:
- Erforderliches Minimum-Role-Level
- Scope-Typ (DISTRICT oder CONGREGATION)
- Ob congregation-level scoping greift

**Vorgehen:**
1. Scanne alle Router-Dateien auf `assert_has_role_in_*`-Aufrufe.
2. Vergleiche mit der Permission-Matrix.
3. Ergänze fehlende Guards.
4. Prüfe congregation-level scoping: `CONGREGATION_ADMIN` darf nur die eigene Gemeinde bearbeiten.

**Rationale:** Systematische Prüfung statt ad-hoc-Ergänzung verhindert erneute Lücken.

### Decision 3: Cross-Tenant-Tests als integrierter Test-Suite

**Entscheidung:** Ein neues Testmodul `tests/integration/test_cross_tenant_isolation.py` mit parametrisierten Tests.

**Testmuster:**
```text
Gegeben: User_A (Bezirk A, Rolle X)
  + User_B (Bezirk B, Rolle X)
  + District A + Congregation A1
  + District B + Congregation B1

Wenn: User_A ruft GET /api/v1/districts/B auf
Dann: 403 FORBIDDEN

Wenn: User_A ruft POST /api/v1/districts/B/events auf
Dann: 403 FORBIDDEN

Wenn: User_A ruft PUT /api/v1/congregations/B1 auf
Dann: 403 FORBIDDEN

Wenn: User_A ruft DELETE /api/v1/events/{event_in_B} auf
Dann: 403 FORBIDDEN
```

**Rationale:** Cross-Tenant-Tests sind der einzige Nachweis, dass Mandantengrenzen *tatsächlich* wirken – Code-Review allein reicht nicht.

## Risks / Trade-offs

- [Berechtigte Cross-Tenant-Operationen werden blockiert] → Superadmin ist explizit ausgenommen. Bei Bedarf kann ein `CROSS_TENANT_SERVICE_ACCOUNT`-Mechanismus ergänzt werden.
- [Production Guard blockiert Deployment] → Fehler sind bewusst hart (CRITICAL), da unsichere Konfiguration ein höheres Risiko darstellt als ein fehlgeschlagener Start.
- [Tests erhöhen CI-Laufzeit] → Cross-Tenant-Tests nutzen dieselbe Test-DB-Infrastruktur wie bestehende Integrationstests.

## Migration Plan

1. `production_guard()` in `config.py` implementieren.
2. Router-Audit durchführen, fehlende Guards ergänzen.
3. `CONGREGATION_ADMIN`-Scoping in allen congregation-bezogenen Endpunkten nachrüsten.
4. Cross-Tenant-Tests schreiben.
5. Bestehende Unit-Tests auf 403-Fälle erweitern.
6. `production-runbook.md` um Config-Checklist ergänzen.

Rollback: Production Guard deaktivieren (`APP_ENV=staging`), Permission-Guards pro Router über Feature-Flag steuerbar. Tests bleiben grün.
