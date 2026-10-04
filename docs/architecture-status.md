# Architekturstatus (Ist vs. Ziel)

> **Letztes Update:** 4. Oktober 2026 — RC-2-Haertung

Diese Seite beschreibt den belastbaren Architekturstand und benennt bewusst verbleibende Schulden. Zielbild bleibt `openspec/architecture/overview.md`.

Legende: ✅ umgesetzt · 🟡 teilweise / kontrollierte Schuld · ❌ offen

## 1. Fachliche Kernfaehigkeiten

- Event-/Planungsmodell: ✅
- Dienstplan-Matrix und Draft-Generierung: ✅
- Feiertags- und kirchliche Festtage: ✅
- ICS-Export: ✅
- Event-Verteilung (`applicability`): ✅
- ExternalEventCandidate-Ingestion und Review-Oberflaeche: ✅
- Reminder/Event-Mail-Hooks/Slot-Gap-Scanning: ✅

## 2. Schichten und Dependency Direction

Zielrichtung:

```text
Domain <- Application <- Adapters / Composition
```

- Domain-Modelle und Domain-Ports: ✅
- Adapter fuer HTTP, DB, OIDC, Kalender, Mail und IDP: ✅
- Application-Layer ausschliesslich ueber Ports entkoppelt: 🟡
- Automatischer Architekturtest gegen neue `app.application -> app.adapters`-Abhaengigkeiten: ✅ (RC-2)

### 2.1 Kontrollierte Legacy-Schuld

Mehrere aeltere Application-Module importieren noch konkrete Adapter. RC-2 fuehrt dafuer eine explizite Legacy-Allowlist im Architekturtest ein. Neue Application-Services duerfen diese Grenze nicht mehr ueberschreiten; sie muessen Domain-Ports/Interfaces verwenden und konkrete Adapter an einer Composition Boundary erhalten.

Die Allowlist ist kein Zielzustand und darf fuer neue Features nicht erweitert werden. Nach RC-2 wird sie schrittweise verkleinert, insbesondere fuer Celery-Composition und Reminder-/Sync-Orchestrierung.

## 3. Authentifizierung, Autorisierung und Tenant Isolation

- OIDC Authorization Code + PKCE: ✅
- JWT-Signatur/Issuer/Audience/Expiry: ✅
- Ungueltige JWTs ohne unsicheren UserInfo-/Introspection-Fallback: ✅ im RC-2-Security-Workstream
- Provider-Refresh-Credential ausserhalb JavaScript-persistenter Speicherung: ✅ im RC-2-Security-Workstream
- RBAC/Membership-Guards: ✅
- PostgreSQL RLS als letzte Tenant-Grenze: ✅
- Tenant-Autorisierung auf verifiziertem Principal/RBAC statt unverifiziertem JWT-Decode: ✅ im RC-2-Security-Workstream
- Owner-controlled Superadmin-Bootstrap: ✅
- CSRF-Schutz fuer state-changing Browser-Requests: ✅
- Audit-Logging: ✅
- Rate-Limiting: ✅; sensitive Pfade besitzen im RC-2-Workstream einen lokalen Fallback bei Valkey-Ausfall

## 4. Deployment und Datenbank

- Getrennte Runtime- und Migration-DB-Rollen: ✅
- Dedizierter `migrate`-Deployment-Schritt: ✅
- API-Runtime ohne automatische Schema-Migration: ✅ im RC-2-Deployment-Workstream
- Read-only Schema-Readiness vor Traffic: ✅ im RC-2-Deployment-Workstream
- Migration Graph/FK/Offline-SQL/Roundtrip CI: ✅
- Verschluesselter Backup-/Restore-Drill: ✅
- PostgreSQL RLS-Integrationstests: ✅

## 5. Frontend-Sicherheits- und Testgrenzen

- Access-/ID-Sessiondaten nicht persistent in `localStorage`: ✅ im RC-2-Security-Workstream
- Provider-Refresh-Token serverseitig/HttpOnly: ✅ im RC-2-Security-Workstream
- CSP und Produktions-Network-Boundary gehaertet: ✅ im RC-2-Deployment-Workstream
- Unit-Tests: ✅
- E2E-Tests: ✅
- Coverage ueber reale Production-Sources mit >80% fuer Statements/Branches/Functions/Lines: 🟡 RC-2-Gate; bisherige selektive Allowlist wird ersetzt und fehlende Tests werden ergaenzt

Production-Code darf nicht breit ausgeschlossen werden, um das Coverage-Gate kuenstlich zu erreichen. Bootstrap-only Wiring darf nur mit dokumentierter Begruendung ausserhalb der Messung bleiben; fachliche Startup-Logik gehoert in testbare Module.

## 6. Supply Chain und CI

- Python-/Frontend-Dependency-Audits: ✅
- CodeQL Python + JavaScript/TypeScript: ✅
- Dependency Review: ✅
- MegaLinter: ✅
- reproduzierbare Lockfile-basierte Builds: ✅ im RC-2-Deployment-Workstream
- Container-/Action-Pinning: 🟡 wird im RC-2-Hardening konsolidiert
- aktives `main`-Ruleset mit strict Required Checks und ohne Bypass: ✅
- verpflichtende menschliche Approval: ❌ (Ruleset aktuell 0 Approvals; Governance-Haertung vor finalem 1.0.0 empfohlen)

## 7. Release-Metadaten und Spezifikationen

- Paketversion als zentrale Backend-Version: ✅
- FastAPI-Metadaten verwenden dieselbe Paketversion: ✅ (RC-2)
- OpenSpec fuer neue RC-2-Sicherheits-/Architekturgrenzen: ✅
- erledigte Changes archiviert und Baseline konsolidiert: 🟡 Bestandteil des RC-2-Abschlusses

## 8. Prioritaet nach RC-2

1. Legacy-Adapterimporte aus Application/Celery-Composition entfernen.
2. Application Use Cases konsequent ueber Ports plus expliziten AuthContext/Policies ausfuehren.
3. Ruleset auf mindestens eine Approval, stale-review dismissal und Review-Thread-Resolution haerten.
4. Performance-SLOs als verpflichtendes Release-Gate weiter ausbauen.

## 9. Referenzen

- Zielbild: `openspec/architecture/overview.md`
- Umsetzungsreihenfolge: `openspec/architecture/implementation-roadmap.md`
- Engineering Standards: `docs/engineering-standards.md`
- Security Baseline: `docs/security-baseline.md`
- Production Runbook: `docs/production-runbook.md`
- RBAC-Coverage: `docs/rbac-coverage.md`
- RC-2 Architektur-OpenSpec: `openspec/changes/enforce-architecture-boundary-rc2/`
