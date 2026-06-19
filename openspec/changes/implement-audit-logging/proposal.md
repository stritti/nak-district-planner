## Why

Aktuell gibt es **kein Audit-Logging** für schreibende Operationen im NAK District Planner. Dies stellt ein **kritisches Sicherheitsrisiko (SEC-009)** dar, da:

1. **Compliance-Verstoss**: OWASP A09 (Security Logging and Monitoring Failures) und CIS Control 8.1 (Audit Log Management) sind nicht erfüllt
2. **Forensik unmöglich**: Bei Sicherheitsvorfällen können Aktionen nicht nachvollzogen werden
3. **Governance-Anforderung**: Für kirchliche Verwaltung müssen Änderungen an Planungsdaten auditierbar sein
4. **DSGVO-Verstoss**: Betroffene können ihr Recht auf Auskunft nicht wahrnehmen

## What Changes

### Neue Fähigkeiten
- `audit-logging`: Systemweites Audit-Logging für alle schreibenden Operationen
- `audit-query`: Abfrage von Audit-Logs für Compliance-Berichte
- `audit-retention`: Automatische Löschung alter Logs nach Retention Policy

### Geänderte Fähigkeiten
- Alle schreibenden API-Endpunkte emittieren Audit-Logs
- Datenbank-Operationen (CREATE, UPDATE, DELETE) werden geloggt
- Admin-Operationen werden besonders detailliert geloggt

## Capabilities

### New Capabilities
- **audit_log_table**: Datenbanktabelle für Audit-Logs mit Indexen für effiziente Abfragen
- **audit_logging_service**: Service zur Erstellung und Speicherung von Audit-Einträgen
- **audit_middleware**: FastAPI Middleware zur automatischen Erfassung von Requests
- **audit_decorator**: Python Decorator für manuelles Logging von Operationen
- **audit_query_api**: API-Endpunkte zur Abfrage von Audit-Logs (nur für Admins)
- **audit_retention_job**: Celery Task zur regelmäßigen Bereinigung alter Logs

### Modified Capabilities
- **event_creation**: Erstellt Audit-Log bei Event-Erstellung
- **event_modification**: Erstellt Audit-Log bei Event-Änderung
- **event_deletion**: Erstellt Audit-Log bei Event-Löschung
- **service_assignment_operations**: Audit-Logging für alle ServiceAssignment-Änderungen
- **calendar_integration_operations**: Audit-Logging für Kalender-Integrationen
- **export_token_operations**: Audit-Logging für Export-Token
- **user_management**: Audit-Logging für Benutzerverwaltung
- **district_operations**: Audit-Logging für Bezirks-Operationen
- **congregation_operations**: Audit-Logging für Gemeinde-Operationen

## Impact

### Backend
- Neue Tabelle `audit_logs` in der Datenbank
- Neuer Service `AuditLoggingService`
- Middleware für automatisches Request-Logging
- Decorator für manuelles Operation-Logging
- Neue API-Endpunkte für Audit-Log Abfragen
- Celery Task für Log-Retention

### Frontend
- Keine Änderungen (Audit-Logs sind Backend-intern)

### Infrastruktur
- Erhöhte Datenbank-Speichernutzung (geschätzt: ~100MB/Monat für 1000 Nutzer)
- Ggf. separate Log-Datenbank für Skalierung

### Betrieb
- Audit-Logs müssen in Backup-Strategie einbezogen werden
- Log-Retention Policy muss definiert und umgesetzt werden
- Monitoring für Audit-Log System

## Success Criteria

- [ ] Alle schreibenden Operationen werden in Audit-Logs erfasst
- [ ] Audit-Logs enthalten: timestamp, user_sub, action, resource_type, resource_id, changes, status, ip_address
- [ ] Audit-Logs sind unveränderlich (keine UPDATE/DELETE auf audit_logs Tabelle)
- [ ] Audit-Logs können von Superadmins abgefragt werden
- [ ] Log-Retention Policy (z.B. 90 Tage) ist implementiert
- [ ] Performance-Impact < 5% auf API-Response-Zeiten
- [ ] Audit-Logging ist in Staging getestet
- [ ] Dokumentation für Audit-Log Format und Abfragen

## Open Questions

1. Sollten Audit-Logs auch gelöschte Daten enthalten (für Forensik)?
   - **Empfehlung**: Ja, aber verschlüsselt

2. Sollten Audit-Logs in separate Datenbank oder Tabelle?
   - **Empfehlung**: Separate Tabelle, ggf. eigene Schema

3. Sollten Audit-Logs asynchron geschrieben werden?
   - **Empfehlung**: Ja, für Performance

4. Sollten Audit-Logs an externe SIEM-Systeme gesendet werden?
   - **Empfehlung**: Optional, über Konfiguration

5. Wie lange sollen Audit-Logs aufbewahrt werden?
   - **Empfehlung**: 90 Tage (Compliance), 365 Tage (Forensik)
