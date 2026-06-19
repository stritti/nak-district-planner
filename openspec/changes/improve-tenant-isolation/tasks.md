## Aufgaben für Tenant-Isolation Implementierung

### Phase 1: Infrastruktur (2 Tage)

#### Tenant Context
- [ ] TenantContext Klasse implementieren (`app/tenant.py`)
- [ ] ContextVars für tenant_id, district_id, user_sub definieren
- [ ] Hilfsmethoden für Get/Set/Reset implementieren

#### Tenant Middleware
- [ ] TenantMiddleware implementieren (`app/adapters/api/middleware/tenant.py`)
- [ ] Extraktion aus JWT Token implementieren
- [ ] Extraktion aus API Key implementieren
- [ ] Kontext für Request-Lifecycle setzen
- [ ] Middleware in FastAPI registrieren

#### PostgreSQL RLS Setup
- [ ] RLS für alle Tenant-Tabellen aktivieren
- [ ] Policies für Events Tabelle erstellen
- [ ] Policies für ServiceAssignments Tabelle erstellen
- [ ] Policies für CalendarIntegrations Tabelle erstellen
- [ ] Policies für Districts Tabelle erstellen
- [ ] Policies für Congregations Tabelle erstellen
- [ ] Policies für Leaders Tabelle erstellen
- [ ] Policies für ExportTokens Tabelle erstellen

#### RLS Middleware
- [ ] SQLAlchemy Event Listener für RLS Settings implementieren
- [ ] Settings für current_tenant_id, current_district_id, current_user_sub setzen
- [ ] Superadmin-Flag setzen

### Phase 2: Tenant-Aware Repositories (3 Tage)

#### Basis-Klasse
- [ ] TenantAwareRepository Basis-Klasse erstellen
- [ ] Generische list() Methode mit Tenant-Filter implementieren
- [ ] Generische get() Methode mit Tenant-Filter implementieren
- [ ] Generische save() Methode mit Tenant-Validierung implementieren
- [ ] Generische delete() Methode mit Tenant-Validierung implementieren

#### Repository Anpassungen
- [ ] SqlEventRepository von TenantAwareRepository ableiten
- [ ] SqlDistrictRepository von TenantAwareRepository ableiten
- [ ] SqlCongregationRepository von TenantAwareRepository ableiten
- [ ] SqlServiceAssignmentRepository von TenantAwareRepository ableiten
- [ ] SqlCalendarIntegrationRepository von TenantAwareRepository ableiten
- [ ] SqlLeaderRepository von TenantAwareRepository ableiten
- [ ] SqlExportTokenRepository von TenantAwareRepository ableiten

### Phase 3: Tenant Validation Service (2 Tage)

#### Service Implementierung
- [ ] TenantValidationService implementieren
- [ ] validate_district_access() Methode implementieren
- [ ] validate_congregation_access() Methode implementieren
- [ ] Superadmin-Bypass implementieren
- [ ] Audit-Logging Integration hinzufügen

#### Decorators
- [ ] @validate_tenant_district Decorator implementieren
- [ ] @validate_tenant_congregation Decorator implementieren
- [ ] Decorators in Router integrieren

### Phase 4: Testing (3 Tage)

#### Unit Tests
- [ ] Unit Tests für TenantContext erstellen
- [ ] Unit Tests für TenantMiddleware erstellen
- [ ] Unit Tests für TenantValidationService erstellen
- [ ] Unit Tests für TenantAwareRepository erstellen

#### Integration Tests
- [ ] Integration Tests für RLS Policies erstellen
- [ ] Integration Tests für Cross-Tenant Zugriff erstellen
- [ ] Integration Tests für Superadmin-Bypass erstellen

#### End-to-End Tests
- [ ] E2E Tests für Tenant-Isolation erstellen
- [ ] E2E Tests für alle CRUD Operationen erstellen

#### Performance Tests
- [ ] Performance Tests für RLS Overhead erstellen
- [ ] Performance Tests für Tenant-Validierung erstellen

### Phase 5: Rollout (1 Tag)

#### Vorbereitung
- [ ] Feature-Flag für Tenant-Isolation hinzufügen
- [ ] Dokumentation aktualisieren
- [ ] Rollback-Plan erstellen

#### Deployment
- [ ] Staging Deployment durchführen
- [ ] Monitoring einrichten
- [ ] Fehlerbehandlung testen
- [ ] Produktion Rollout durchführen

#### Nachbereitung
- [ ] Monitoring-Dashboard erstellen
- [ ] Alerting für Tenant-Isolation Fehler konfigurieren
- [ ] Dokumentation finalisieren

