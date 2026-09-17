## Aufgaben für Audit-Logging Implementierung

> **Hinweis (2026-09-07):** Dieses `tasks.md` existierte bisher nicht, obwohl das Feature über PR `753a502` ("feat(security): implement audit logging (SEC-009)") bereits implementiert und in `docs/security/audit-logging.md` dokumentiert ist. Nachträglich gegen den Code-Stand erstellt.

### Kernfunktionalität
- [x] `audit_logs` Tabelle in PostgreSQL (`app/adapters/db/orm_models/audit_log.py`)
- [x] Domain-Modell (`app/domain/models/audit_log.py`)
- [x] Repository (`app/adapters/db/repositories/audit_log.py`)
- [x] `AuditService` für Log-Erstellung (`app/application/audit_service.py`)
- [x] `AuditMiddleware` für automatisches Request-Logging (`app/adapters/api/middleware/audit.py`)
- [x] Middleware in `main.py` registriert
- [x] Unveränderlichkeit: keine UPDATE/DELETE-Operationen auf `audit_logs` im Code
- [x] Exemptions für Health-Checks/unkritische Pfade

### Nicht umgesetzt (Lücken gegenüber ursprünglichem Proposal)
- [ ] `@audit_action` Decorator für manuelles Logging *(nicht gefunden — Logging läuft ausschließlich über die Middleware, kein expliziter Decorator im Code)*
- [ ] `AuditAPI` — API-Endpunkte zur Abfrage von Audit-Logs für Superadmins *(nicht gefunden — `docs/security/audit-logging.md` zeigt nur SQL-Query-Beispiele, keine echten API-Routen)*
- [ ] `AuditRetentionService` / Celery Task zur automatischen Log-Bereinigung *(nicht gefunden — Doku beschreibt eine empfohlene Retention-Policy, aber keine automatisierte Umsetzung; Logs werden aktuell unbegrenzt aufbewahrt)*

### Bewertung
Das Kernrisiko (SEC-009: keine Nachvollziehbarkeit schreibender Operationen) ist behoben — alle Requests werden erfasst. Die Compliance-/Betriebs-Erweiterungen (Admin-Abfrage-API, automatisierte Retention) fehlen noch und sollten als eigener kleiner Follow-up erfasst werden, falls Audit-Log-Volumen oder DSGVO-Auskunftsersuchen das relevant machen.
