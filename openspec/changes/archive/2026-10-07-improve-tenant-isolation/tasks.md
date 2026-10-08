## Aufgaben für Tenant-Isolation Implementierung

> **Hinweis (2026-09-07):** Diese Liste war seit Erstellung nicht aktualisiert worden (0/60 abgehakt), obwohl ein Großteil bereits über PR `e197af9` ("feat: tenant isolation (SEC-020, SEC-021)") implementiert und in `docs/security/tenant-isolation.md` dokumentiert wurde. Die Checkboxen unten wurden gegen den tatsächlichen Code-Stand verifiziert. Einige Punkte wurden mit anderer Architektur umgesetzt als ursprünglich geplant (siehe Anmerkungen) oder sind bewusst entfallen.

### Phase 1: Infrastruktur (2 Tage)

#### Tenant Context
- [x] TenantContext Klasse implementieren (`app/tenant.py`)
- [x] ContextVars für tenant_id, district_id, user_sub definieren *(zusätzlich: congregation_id, user_roles)*
- [x] Hilfsmethoden für Get/Set/Reset implementieren

#### Tenant Middleware
- [x] TenantMiddleware implementieren (`app/adapters/api/middleware/tenant.py`)
- [x] Extraktion aus JWT Token implementieren
- [x] ~Extraktion aus API Key implementieren~ *(entfällt — die API-Key-Authentifizierung wurde mit der OIDC-Migration entfernt (`phase4b`, Tasks 4.2/4.3); `idp_provisioning_api_key` ist ein ausgehender Webhook-Schlüssel. Befund behoben: `CSRFMiddleware` übersprang die Prüfung allein wegen eines `X-API-Key`-Headers; die Ausnahme ist entfernt, die Security-Doku korrigiert)*
- [x] Kontext für Request-Lifecycle setzen
- [x] Middleware in FastAPI registrieren (`TenantMiddleware` + `TenantValidationMiddleware` in `main.py`)

#### PostgreSQL RLS Setup
- [x] RLS für PlanningSlots, EventInstances, ServiceAssignments, Leaders, CalendarIntegrations, CongregationInvitations und Memberships aktiviert (`app/adapters/db/migrations/rls_policies.py`, angewendet durch Alembic `0014_apply_rls_policies.py`)
- [x] Policies für PlanningSlots und EventInstances erstellt
- [x] Policies für ServiceAssignments Tabelle erstellt
- [x] Policies für CalendarIntegrations Tabelle erstellt
- [x] ~Policies für Districts Tabelle~ *(entfällt — District ist die Root-Tenant-Grenze selbst, Zugriff wird über Membership-Checks in `TenantValidationService` statt RLS gesteuert)*
- [x] ~Policies für Congregations Tabelle~ *(entfällt — analog zu Districts, Zugriff über Membership statt RLS)*
- [x] Policies für Leaders Tabelle erstellt
- [x] ~Policies für ExportTokens Tabelle~ *(entfällt — Export-Zugriff ist absichtlich token-scoped statt membership-scoped, siehe UC-05 in CLAUDE.md)*

#### RLS Middleware
- [x] SQLAlchemy Event Listener für RLS Settings implementieren (`app/adapters/db/session.py::_set_tenant_gucs`)
- [x] Settings für current_tenant_id, current_district_id, current_congregation_id, current_user_sub setzen
- [x] ~Superadmin-Flag setzen~ *(anders gelöst: Policies prüfen `is_superadmin` per Subquery auf die `users`-Tabelle statt über einen eigenen GUC)*

### Phase 2: Tenant-Aware Repositories (3 Tage)

#### Basis-Klasse
- [x] ~TenantAwareRepository Basis-Klasse erstellen~ *(architektonisch anders gelöst: Tenant-Filterung läuft über PostgreSQL RLS + `TenantValidationService`, nicht über eine Repository-Basisklasse)*
- [x] ~Generische list()/get()/save()/delete() Methoden mit Tenant-Filter~ *(entfällt aus demselben Grund — Filterung passiert transparent auf DB-Ebene)*

#### Repository Anpassungen
- [x] ~Repositories von TenantAwareRepository ableiten~ *(entfällt — kein Basisklassen-Pattern verwendet, siehe oben)*

### Phase 3: Tenant Validation Service (2 Tage)

#### Service Implementierung
- [x] TenantValidationService implementieren (`app/application/tenant_validation.py`)
- [x] validate_user_in_district() implementiert *(entspricht validate_district_access())*
- [x] validate_user_in_congregation() implementiert *(entspricht validate_congregation_access())*
- [x] Superadmin-Bypass implementiert
- [x] Audit-Logging Integration für Tenant-Validation-Fehler *(jede 403-Antwort, auch bei GET, als `ACCESS_DENIED` mit geprüftem Tenant; vor der Authentifizierung abgelehnte Requests mit `extra_metadata.claimed_sub`. Migration `0023`. Befund und Fix: Der Audit-Writer schrieb wegen falsch gemappter Status-Enums (`failed` statt `FAILED`) überhaupt keine Einträge)*

#### Decorators
- [x] ~@validate_tenant_district / @validate_tenant_congregation Decorators~ *(anders gelöst: `assert_has_role_in_district()` / `assert_has_role_in_congregation()` als direkte Funktionsaufrufe in den Routern statt Decorators, siehe `app/adapters/auth/permissions.py`)*
- [x] Tenant-Validierung in Routern integriert

### Phase 4: Testing (3 Tage)

#### Unit Tests
- [x] Unit Tests für TenantContext erstellt (`tests/unit/test_tenant_context.py`)
- [x] Unit Tests für TenantMiddleware erstellt (`tests/unit/test_tenant_middleware.py`)
- [x] Unit Tests für TenantValidationService erstellt (`tests/unit/test_tenant_validation.py`)
- [x] Cross-Tenant-Isolation Unit-Tests erstellt (`tests/unit/test_cross_tenant_isolation.py`)
- [x] ~Unit Tests für TenantAwareRepository~ *(entfällt, da Basisklasse nicht existiert)*

#### Integration Tests
- [x] Integration Tests für RLS Policies gegen echte PostgreSQL-Instanz *(`tests/integration/test_rls_postgres.py`, läuft in CI im Job `backend-tests` gegen frisch migriertes PostgreSQL als NOBYPASSRLS-Rolle `nak_app`; Strukturtest verlangt RLS für jede Tabelle mit Tenant-Schlüssel)*
- [x] Integration Tests für Cross-Tenant Zugriff auf DB-Ebene *(Lesen, Einfügen, Update/Delete fremder Zeilen, Verschieben in fremden Bezirk, ohne Identität/Membership, gefälschtes Subject)*
- [x] Integration Tests für Superadmin-Bypass auf DB-Ebene *(Superadmin und System-Worker)*

#### End-to-End Tests
- [x] E2E Tests für Tenant-Isolation *(`tests/integration/test_tenant_isolation_api.py`: kompletter HTTP-Stack gegen PostgreSQL mit RLS als `nak_app`, nur der OIDC-Aufruf ist gemockt)*
- [x] E2E Tests für alle CRUD Operationen *(Leader anlegen/lesen/ändern/löschen im eigenen Bezirk inkl. Audit-Trail; fremder Bezirk 403; fremde Datensätze unter eigenem Pfad und fremde Termine 404, Daten unverändert)*

#### Performance Tests
- [x] Performance Tests für RLS Overhead *(`tests/performance/test_rls_overhead.py`, 5 Bezirke: Slots ohne messbaren Overhead. Befund: `service_assignments` hatte keine Indizes auf den Fremdschlüsseln, die Zuweisungsabfrage der Matrix scannte je nach Statistik alle Bezirke (~240 ms) → Migration `0024`, jetzt ~7 ms. Messwerte statt Schätzungen in `docs/security/tenant-isolation.md`)*
- [x] Performance Tests für Tenant-Validierung *(`validate_user_in_district` p95 ~3–5 ms)*

### Phase 5: Rollout (1 Tag)

#### Vorbereitung
- [x] ~Feature-Flag für Tenant-Isolation~ *(entfällt — Feature ist bereits fest verdrahtet in Produktion, kein Flag gefunden)*
- [x] Dokumentation aktualisiert (`docs/security/tenant-isolation.md`)
- [x] Rollback-Plan erstellen *(Abschnitt „Rollback Plan“ in `docs/security/tenant-isolation.md`)*

#### Deployment
- [x] Staging/Produktion Rollout durchgeführt *(Feature ist laut CHANGELOG in v0.29.3 bereits live)*
- [x] Monitoring für Tenant-Isolation-Fehler einrichten *(OpenTelemetry-Zähler `nak.access.denied` mit Methode und Route-Template, ohne IDs)*
- [x] Fehlerbehandlung explizit getestet *(DB-Ebene und E2E; Befunde: fehlendes RLS auf `external_event_candidates`/`leader_unavailabilities` → `0022`; ungeprüfter JWT-`sub` landete als RLS-Identität in der GUC → nur noch verifizierte Identität)*

#### Nachbereitung
- [x] Monitoring-Dashboard erstellen *(Panels und Audit-Abfrage dokumentiert; ein Dashboard-Export hängt vom eingesetzten Backend ab)*
- [x] Alerting für Tenant-Isolation Fehler konfigurieren *(Beispielregeln `TenantProbing` und `AccessDeniedSpike` in `docs/security/tenant-isolation.md`)*
- [x] Dokumentation finalisiert (`docs/security/tenant-isolation.md`, 546 Zeilen)

---

## Verbleibende Punkte

- Die Alerting-Regeln und Dashboard-Panels sind dokumentiert. Einspielen muss sie der Betrieb im jeweils eingesetzten Monitoring-Backend.
