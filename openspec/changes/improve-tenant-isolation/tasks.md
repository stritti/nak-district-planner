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
- [ ] Extraktion aus API Key implementieren *(kein API-Key-basierter Tenant-Kontext gefunden — API-Key-Auth trägt aktuell keinen Tenant-Kontext in die Middleware)*
- [x] Kontext für Request-Lifecycle setzen
- [x] Middleware in FastAPI registrieren (`TenantMiddleware` + `TenantValidationMiddleware` in `main.py`)

#### PostgreSQL RLS Setup
- [x] RLS für Events, ServiceAssignments, Leaders, CalendarIntegrations, CongregationInvitations, Memberships aktiviert (`app/adapters/db/migrations/rls_policies.py`, angewendet durch Alembic `0014_apply_rls_policies.py`)
- [x] Policies für Events Tabelle erstellt
- [x] Policies für ServiceAssignments Tabelle erstellt
- [x] Policies für CalendarIntegrations Tabelle erstellt
- [ ] ~Policies für Districts Tabelle~ *(entfällt — District ist die Root-Tenant-Grenze selbst, Zugriff wird über Membership-Checks in `TenantValidationService` statt RLS gesteuert)*
- [ ] ~Policies für Congregations Tabelle~ *(entfällt — analog zu Districts, Zugriff über Membership statt RLS)*
- [x] Policies für Leaders Tabelle erstellt
- [ ] ~Policies für ExportTokens Tabelle~ *(entfällt — Export-Zugriff ist absichtlich token-scoped statt membership-scoped, siehe UC-05 in CLAUDE.md)*

#### RLS Middleware
- [x] SQLAlchemy Event Listener für RLS Settings implementieren (`app/adapters/db/session.py::_set_tenant_gucs`)
- [x] Settings für current_tenant_id, current_district_id, current_congregation_id, current_user_sub setzen
- [x] ~Superadmin-Flag setzen~ *(anders gelöst: Policies prüfen `is_superadmin` per Subquery auf die `users`-Tabelle statt über einen eigenen GUC)*

### Phase 2: Tenant-Aware Repositories (3 Tage)

#### Basis-Klasse
- [ ] ~TenantAwareRepository Basis-Klasse erstellen~ *(architektonisch anders gelöst: Tenant-Filterung läuft über PostgreSQL RLS + `TenantValidationService`, nicht über eine Repository-Basisklasse)*
- [ ] ~Generische list()/get()/save()/delete() Methoden mit Tenant-Filter~ *(entfällt aus demselben Grund — Filterung passiert transparent auf DB-Ebene)*

#### Repository Anpassungen
- [ ] ~Repositories von TenantAwareRepository ableiten~ *(entfällt — kein Basisklassen-Pattern verwendet, siehe oben)*

### Phase 3: Tenant Validation Service (2 Tage)

#### Service Implementierung
- [x] TenantValidationService implementieren (`app/application/tenant_validation.py`)
- [x] validate_user_in_district() implementiert *(entspricht validate_district_access())*
- [x] validate_user_in_congregation() implementiert *(entspricht validate_congregation_access())*
- [x] Superadmin-Bypass implementiert
- [ ] Audit-Logging Integration für Tenant-Validation-Fehler *(nicht explizit gefunden — verifizieren, ob Verstöße im Audit-Log landen)*

#### Decorators
- [x] ~@validate_tenant_district / @validate_tenant_congregation Decorators~ *(anders gelöst: `assert_has_role_in_district()` / `assert_has_role_in_congregation()` als direkte Funktionsaufrufe in den Routern statt Decorators, siehe `app/adapters/auth/permissions.py`)*
- [x] Tenant-Validierung in Routern integriert

### Phase 4: Testing (3 Tage)

#### Unit Tests
- [x] Unit Tests für TenantContext erstellt (`tests/unit/test_tenant_context.py`)
- [x] Unit Tests für TenantMiddleware erstellt (`tests/unit/test_tenant_middleware.py`)
- [x] Unit Tests für TenantValidationService erstellt (`tests/unit/test_tenant_validation.py`)
- [x] Cross-Tenant-Isolation Unit-Tests erstellt (`tests/unit/test_cross_tenant_isolation.py`)
- [ ] ~Unit Tests für TenantAwareRepository~ *(entfällt, da Basisklasse nicht existiert)*

#### Integration Tests
- [ ] Integration Tests für RLS Policies gegen echte PostgreSQL-Instanz *(nicht gefunden — bestehende Tests laufen gegen Mocks, nicht gegen eine DB mit aktiven RLS-Policies)*
- [ ] Integration Tests für Cross-Tenant Zugriff auf DB-Ebene *(gleiche Lücke)*
- [ ] Integration Tests für Superadmin-Bypass auf DB-Ebene

#### End-to-End Tests
- [ ] E2E Tests für Tenant-Isolation *(nicht gefunden)*
- [ ] E2E Tests für alle CRUD Operationen *(nicht gefunden)*

#### Performance Tests
- [ ] Performance Tests für RLS Overhead *(nicht gefunden — Benchmark-Zahlen in `docs/security/tenant-isolation.md` scheinen Schätzungen, keine Testresultate)*
- [ ] Performance Tests für Tenant-Validierung *(nicht gefunden)*

### Phase 5: Rollout (1 Tag)

#### Vorbereitung
- [ ] ~Feature-Flag für Tenant-Isolation~ *(entfällt — Feature ist bereits fest verdrahtet in Produktion, kein Flag gefunden)*
- [x] Dokumentation aktualisiert (`docs/security/tenant-isolation.md`)
- [ ] Rollback-Plan erstellen *(nicht gefunden)*

#### Deployment
- [x] Staging/Produktion Rollout durchgeführt *(Feature ist laut CHANGELOG in v0.29.3 bereits live)*
- [ ] Monitoring für Tenant-Isolation-Fehler einrichten *(kein dediziertes Monitoring/Alerting gefunden)*
- [ ] Fehlerbehandlung explizit getestet *(offen — siehe Integration/E2E-Lücken oben)*

#### Nachbereitung
- [ ] Monitoring-Dashboard erstellen
- [ ] Alerting für Tenant-Isolation Fehler konfigurieren
- [x] Dokumentation finalisiert (`docs/security/tenant-isolation.md`, 546 Zeilen)

---

## Verbleibende echte Lücken (Zusammenfassung)

1. **RLS-Integrationstests fehlen** — aktuelle Tests laufen gegen Mocks, nicht gegen eine PostgreSQL-Instanz mit aktiven Policies. Das ist die größte Lücke, da RLS die letzte Verteidigungslinie ist und ungetestet bleibt.
2. **API-Key-Requests tragen keinen Tenant-Kontext** in der Middleware.
3. **Kein Monitoring/Alerting** für Tenant-Isolation-Verstöße.
4. **Kein Rollback-Plan** dokumentiert, falls RLS-Policies in Produktion Probleme verursachen.
