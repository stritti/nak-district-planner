## Why

Aktuell gibt es **keine vollständige Tenant-Isolation** (SEC-020, SEC-021). Dies ermöglicht:

1. **Cross-Tenant Data Access**: Nutzer können potenziell auf Daten anderer Tenants zugreifen
2. **Privilege Escalation**: Nutzer können durch Manipulation von IDs auf Daten anderer Bezirke/Gemeinden zugreifen
3. **Compliance-Verstoss**: OWASP A01 (Broken Access Control) ist nicht vollständig erfüllt
4. **Sicherheitsrisiko**: Besonders kritisch für Multi-Tenancy Architektur

## What Changes

### Neue Fähigkeiten
- `tenant-isolation`: Vollständige Tenant-Isolation auf Application- und Datenbank-Ebene
- `tenant-context`: Tenant-Kontext für alle Requests
- `row-level-security`: PostgreSQL RLS für Datenbank-Ebene Isolation
- `tenant-validation`: Automatische Tenant-Validierung für alle Operationen

### Geänderte Fähigkeiten
- Alle Datenbank-Abfragen sind Tenant-spezifisch
- Alle API-Endpunkte validieren Tenant-Zugehörigkeit
- Cross-Tenant Zugriff ist explizit verhindert

## Capabilities

### New Capabilities
- **tenant_context**: Kontextvariable für aktuellen Tenant
- **tenant_middleware**: FastAPI Middleware zur Tenant-Extraktion
- **rls_policies**: PostgreSQL Row-Level Security Policies
- **tenant_validation_service**: Service zur Tenant-Validierung
- **tenant_aware_repositories**: Repositories mit Tenant-Filter

### Modified Capabilities
- **event_repository**: Tenant-spezifische Abfragen
- **district_repository**: Tenant-spezifische Abfragen
- **congregation_repository**: Tenant-spezifische Abfragen
- **service_assignment_repository**: Tenant-spezifische Abfragen
- **all_api_endpoints**: Tenant-Validierung für alle Requests

## Impact

### Backend
- Neue Middleware für Tenant-Kontext
- Neue Service für Tenant-Validierung
- PostgreSQL RLS Policies
- Anpassungen an allen Repositories

### Frontend
- Keine Änderungen

### Infrastruktur
- Keine Änderungen

### Betrieb
- Keine Änderungen

## Success Criteria

- [ ] Alle Datenbank-Abfragen sind Tenant-isoliert
- [ ] Cross-Tenant Zugriff ist unmöglich
- [ ] Tenant-Kontext ist für alle Requests verfügbar
- [ ] PostgreSQL RLS ist für alle Tenant-Tabellen aktiviert
- [ ] Performance-Impact < 2% auf API-Response-Zeiten
- [ ] Tenant-Isolation ist in Staging getestet
- [ ] Dokumentation für Tenant-Isolation

## Open Questions

1. Soll RLS für alle Tabellen oder nur Tenant-spezifische aktiviert werden?
   - **Empfehlung:** Nur Tenant-spezifische Tabellen

2. Soll Tenant-Isolation auf Application- oder Datenbank-Ebene implementiert werden?
   - **Empfehlung:** Beide (Defense in Depth)

3. Wie mit Superadmin umgehen?
   - **Empfehlung:** Superadmin kann alle Tenants sehen (Bypass)

4. Soll Tenant-Isolation für Lese- und Schreiboperationen gelten?
   - **Empfehlung:** Ja, für beide

5. Wie mit Shared Data umgehen (z.B. System-Konfiguration)?
   - **Empfehlung:** Separate Tabellen für Shared Data

