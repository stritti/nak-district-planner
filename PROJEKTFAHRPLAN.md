# Projektfahrplan: NAK Bezirksplaner

**Version:** 1.0  
**Stand:** 22. Juni 2026  
**Aktuelle Version:** v0.22.0  

---

## 📋 Zusammenfassung

Der **NAK Bezirksplaner** ist eine webbasierte Planungsplattform für Neuapostolische Kirchenbezirke zur zentralen Dienstplanung und Kalenderverwaltung. Dieses Dokument definiert den strategischen Fahrplan mit priorisierten Meilensteinen für die nächsten 6-12 Monate.

---

## 🎯 Strategische Ziele

### 1. **Architektonische Stabilität** (Q3 2026)
- Vollständige Migration auf PlanningSlot/EventInstance-Modell
- Gehärteter Sync-Algorithmus mit Idempotenz-Garantie
- Vollständige RBAC-Abdeckung aller Endpunkte

### 2. **Produktionsreife** (Q4 2026)
- Audit-Logging für Compliance
- Non-Functional Baseline (Sicherheit, Performance)
- Vollständige Testabdeckung

### 3. **Nutzererlebnis** (Q1 2027)
- Konfliktprüfung bei Dienstzuweisungen
- Benachrichtigungssystem
- Mobile-Optimierung

---

## 🗺️ Meilenstein-Übersicht

| Meilenstein | Version | Zeitrahmen | Priorität | Status |
|-------------|---------|------------|-----------|--------|
| **M1: Planning Model Finalisierung** | v0.23.0 | Juli 2026 | 🔴 Critical | 🟡 Teilweise |
| **M2: RBAC Vollständigkeit** | v0.24.0 | August 2026 | 🔴 Critical | 🟡 Teilweise |
| **M3: Sync-Algorithmus Härtung** | v0.25.0 | September 2026 | 🔴 Critical | ❌ Offen |
| **M4: Audit-Logging** | v0.26.0 | Oktober 2026 | 🟠 High | ❌ Offen |
| **M5: Konfliktprüfung** | v0.27.0 | November 2026 | 🟠 High | ❌ Offen |
| **M6: Non-Functional Baseline** | v0.28.0 | Dezember 2026 | 🟡 Medium | ❌ Offen |
| **M7: Benachrichtigungen** | v0.29.0 | Januar 2027 | 🟡 Medium | ❌ Offen |
| **M8: Produktions-Hardening** | v1.0.0 | Februar 2027 | 🟠 High | ❌ Offen |

---

## 📅 Detaillierte Meilensteine

### 🎯 **M1: Planning Model Finalisierung** (v0.23.0)

**Zeitraum:** Juli 2026  
**Verantwortlich:** Backend-Team  
**Risiko:** Hoch (Datenmigration erforderlich)

#### Ziele
- [x] PlanningSeries-Entität implementiert
- [x] PlanningSlot als Aggregate Root
- [x] Event → EventInstance Refactoring
- [x] ServiceAssignment zu PlanningSlot verschoben
- [x] Matrix-Endpoint mit Deviation-Daten
- [ ] **PlanningSeries Slot Generation Service** (3.1)
- [ ] **Frontend: Matrix UI mit Soll/Ist-Anzeige** (5.1)

#### Abhängigkeiten
- Keine Blockierer

#### Erfolgsmetriken
- 100% der neuen Installationen nutzen PlanningSlot-Modell
- Matrix-View zeigt Deviation-Indikatoren korrekt an
- Alle bestehenden Tests passen

---

### 🔒 **M2: RBAC Vollständigkeit** (v0.24.0)

**Zeitraum:** August 2026  
**Verantwortlich:** Security-Team  
**Risiko:** Mittel

#### Ziele
- [x] Rollenmodell (Role, Membership) implementiert
- [x] JWT mit Memberships erweitert
- [x] Authorization Guards in Planning/CalendarIntegration
- [ ] **RBAC Guards in auth.py Router** (3.5 🔴 CRITICAL)
- [ ] **RBAC Guards in system.py Router** (3.6 🔴 CRITICAL)
- [ ] **Vollständige Router-Abdeckung prüfen** (3.7 🟠 HIGH)
- [ ] **Automatisierter Permission Coverage Test** (3.8 🟡 MEDIUM)
- [ ] **Role Claims Extraktion aus JWT verifizieren** (4.3 🟠 HIGH)

#### Abhängigkeiten
- M1 kann parallel laufen

#### Erfolgsmetriken
- 100% aller Endpunkte haben RBAC-Prüfung
- Permission Coverage Report zeigt 0 Lücken
- Alle Rollen (VIEWER, PLANNER, CONGREGATION_ADMIN, DISTRICT_ADMIN, SUPERADMIN) funktionieren korrekt

---

### 🔄 **M3: Sync-Algorithmus Härtung** (v0.25.0)

**Zeitraum:** September 2026  
**Verantwortlich:** Backend-Team  
**Risiko:** Hoch (Sync-Stabilität kritisch)

#### Ziele

**Phase 3 - Sync Metadata Stabilization:**
- [ ] Sync_state Feld zu EventInstance (1.1)
- [ ] last_synced_hash Feld (1.2)
- [ ] last_internal_modified_at Feld (1.3)
- [ ] last_external_modified_at Feld (1.4)
- [ ] ExternalEventLink Tabelle (2.1)
- [ ] Externe Revision Marker persistieren (2.2)
- [ ] ExternalEventLink mit EventInstance verknüpfen (2.3)

**Phase 4 - Hardened Sync Engine:**
- [ ] State Machine Transition Logik (3.1)
- [ ] Structural vs Soft Field Diffing (3.2)
- [ ] Conflict State Handling (3.3)
- [ ] Payload Hash Vergleich (4.1)
- [ ] Outbound Revision Tracking (4.2)
- [ ] Inbound Revision Guard (4.3)
- [ ] MARK_CANCELLED Behavior (5.1)
- [ ] HARD_DELETE Behavior (5.2)

#### Abhängigkeiten
- M1 sollte abgeschlossen sein

#### Erfolgsmetriken
- 0 Duplikate bei Sync-Vorgängen
- 100% Idempotenz garantiert
- Loop Prevention funktioniert zuverlässig
- Delete Handling in beiden Modi getestet

---

### 📝 **M4: Audit-Logging** (v0.26.0)

**Zeitraum:** Oktober 2026  
**Verantwortlich:** Security-Team  
**Risiko:** Mittel

#### Ziele
- [ ] Audit-Log Tabelle erstellen (1.1)
- [ ] Audit Logging Service implementieren (1.2)
- [ ] Audit Hooks für PlanningSlot Operationen (1.3)
- [ ] Audit Hooks für ServiceAssignment Operationen (1.4)
- [ ] Audit Hooks für CalendarIntegration Operationen (1.5)
- [ ] Audit Hooks für Export Token Operationen (1.6)

#### Abhängigkeiten
- M2 sollte abgeschlossen sein (RBAC für Audit-Endpunkte)

#### Erfolgsmetriken
- Alle schreibenden Operationen werden geloggt
- Performance Impact < 5%
- Audit-Logs sind unveränderlich
- Forensik-Unterstützung funktioniert

---

### ⚠️ **M5: Konfliktprüfung** (v0.27.0)

**Zeitraum:** November 2026  
**Verantwortlich:** Domain-Team  
**Risiko:** Mittel

#### Ziele

**Domain Conflict Engine:**
- [ ] Severity Enum (PASS, WARN, BLOCK) (1.1)
- [ ] ConflictResult Dataclass (1.1)
- [ ] no_double_booking Regel (1.2)
- [ ] travel_time_check Regel (1.2)
- [ ] role_requirement_check Regel (1.2)
- [ ] leader_available Regel (1.2)
- [ ] congregation_distance_check Regel (1.2)
- [ ] ConflictService orchestriert alle Regeln (1.3)
- [ ] ConflictContext Dataclass (1.4)
- [ ] Unit-Tests für alle Regeln (1.5-1.6)

**Leader Unavailability:**
- [ ] Domain-Modell LeaderUnavailability (2.1)
- [ ] ORM-Modell (2.2)
- [ ] Alembic Migration (2.3)
- [ ] Repository mit CRUD (2.4)
- [ ] API-Router (2.5)
- [ ] Router in main.py registrieren (2.6)

**Integration:**
- [ ] Conflict Check vor ServiceAssignment (3.1)
- [ ] Conflict Check bei Event-Erstellung (3.2)
- [ ] API-Schema für Conflict-Response (3.3)
- [ ] Feature-Flag CONFLICT_CHECK_ENABLED (3.4)

**Frontend:**
- [ ] ConflictBanner.vue Komponente (4.1)
- [ ] Integration in Matrix-View (4.2)
- [ ] Integration in ServiceAssignment-Dialog (4.3)
- [ ] BLOCK: Submit-Button deaktiviert (4.4)
- [ ] WARN: Bestätigungsmodal (4.5)
- [ ] Pinia-Store für Konfliktstatus (4.6)

**Abwesenheitsverwaltung:**
- [ ] LeaderUnavailabilityForm.vue (5.1)
- [ ] LeaderUnavailabilityList.vue (5.2)
- [ ] API-Integration (5.3)
- [ ] Navigation integrieren (5.4)

**E2E-Tests:**
- [ ] Playwright-Test: Gottesdienst planen → Amtsträger zuweisen (7.1)
- [ ] Playwright-Test: Double-Booking → BLOCK (7.2)
- [ ] Playwright-Test: Wechselzeit-Konflikt → WARN (7.3)
- [ ] Playwright-Test: Abwesenheit → Zuweisung blockiert (7.4)

#### Abhängigkeiten
- M1 sollte abgeschlossen sein (PlanningSlot-Modell)

#### Erfolgsmetriken
- 0 falsche Konflikte (False Positives)
- 100% echte Konflikte erkannt (True Positives)
- Alle E2E-Tests passen
- Benutzer können Konflikte intuitiv auflösen

---

### 🛡️ **M6: Non-Functional Baseline** (v0.28.0)

**Zeitraum:** Dezember 2026  
**Verantwortlich:** DevOps-Team  
**Risiko:** Niedrig

#### Ziele

**Audit Infrastructure:**
- [ ] Audit-Log Service (1.2)
- [ ] Audit Hooks für alle kritischen Operationen (1.3-1.6)

**Security Baseline:**
- [ ] Credential Encryption at Application Layer (2.1)
- [ ] Export Token Entropy Requirement (2.2)
- [ ] Rate Limiting Middleware (2.3)

**Performance Validation:**
- [ ] Matrix Endpoint Benchmark (3.1)
- [ ] Performance Test für Sync Duration (3.2)

**Operational Reliability:**
- [ ] Exponential Backoff Retry für Sync Jobs (4.1)
- [ ] Structured Logs für Sync Failures (4.2)
- [ ] Alert Hook für repeated Sync Failures (4.3)

#### Abhängigkeiten
- M4 (Audit-Logging) sollte abgeschlossen sein

#### Erfolgsmetriken
- 100% Security Baseline Anforderungen erfüllt
- Performance SLOs validiert
- 0 kritische Alerts in Produktion

---

### 📢 **M7: Benachrichtigungssystem** (v0.29.0)

**Zeitraum:** Januar 2027  
**Verantwortlich:** Frontend-Team  
**Risiko:** Niedrig

#### Ziele
- [ ] In-App Notifications (aus tasks.md)
- [ ] Configurable Email Reminders
- [ ] Event-Driven Mail Hooks
- [ ] Toast Notification System (bereits teilweise implementiert)

#### Abhängigkeiten
- Keine Blockierer

#### Erfolgsmetriken
- Benutzer erhalten rechtzeitige Benachrichtigungen
- Email Reminders sind konfigurierbar
- In-App Notifications funktionieren zuverlässig

---

### 🚀 **M8: Produktions-Hardening & v1.0.0** (v1.0.0)

**Zeitraum:** Februar 2027  
**Verantwortlich:** Alle Teams  
**Risiko:** Hoch

#### Ziele
- [ ] Alle kritischen Issues geschlossen
- [ ] Vollständige Testabdeckung (> 90%)
- [ ] Produktions-Dokumentation finalisiert
- [ ] Migration Guide für bestehende Installationen
- [ ] Rollback-Strategie definiert

#### Abhängigkeiten
- Alle vorherigen Meilensteine abgeschlossen

#### Erfolgsmetriken
- Stabile v1.0.0 Release
- 0 kritische Bugs
- 100% Dokumentation aktuell
- Produktionsbereit für breite Nutzung

---

## 📊 Ressourcenplanung

### Team-Zusammensetzung (empfohlen)

| Rolle | Verantwortung | Kapazität |
|-------|---------------|-----------|
| Backend Lead | Architektur, Domain Modell | 80% |
| Frontend Lead | UI/UX, Vue-Komponenten | 80% |
| Security Engineer | RBAC, Audit, Security Baseline | 50% |
| DevOps Engineer | CI/CD, Deployment, Monitoring | 30% |
| QA Engineer | Tests, Qualitätssicherung | 50% |

### Zeitaufwand pro Meilenstein

| Meilenstein | Geschätzter Aufwand (Personentage) |
|-------------|------------------------------------|
| M1 | 10-15 |
| M2 | 5-8 |
| M3 | 15-20 |
| M4 | 8-10 |
| M5 | 20-25 |
| M6 | 10-12 |
| M7 | 8-10 |
| M8 | 10-15 |
| **Gesamt** | **86-105 Personentage** |

---

## ⚠️ Risiken & Mitigationsstrategien

### 1. **Datenmigration (M1, M3)**
- **Risiko:** Bestehende Daten könnten bei Migration verloren gehen
- **Mitigation:** 
  - Snapshot vor Migration
  - Rollback-Strategie definieren
  - Migration in Staging testen
  - Feature-Flags für schrittweise Aktivierung

### 2. **RBAC Lücken (M2)**
- **Risiko:** Unautorisierter Zugriff auf Endpunkte
- **Mitigation:**
  - Automatisierter Permission Coverage Test
  - Manuelle Review aller Router
  - Penetration Testing

### 3. **Sync-Algorithmus (M3)**
- **Risiko:** Datenverlust oder Duplikate bei Sync
- **Mitigation:**
  - Idempotenz-Tests
  - Loop Prevention Tests
  - Monitoring für Sync-Fehler
  - Backup-Strategie

### 4. **Performance (M6)**
- **Risiko:** Audit-Logging beeinflusst Performance
- **Mitigation:**
  - Performance Benchmarks
  - Asynchrone Logging-Option
  - Caching für häufige Abfragen

---

## 📈 Erfolgsmetriken (KPIs)

### Technische Metriken
- **Testabdeckung:** > 90% (Unit + Integration)
- **Code Qualität:** 0 kritische CodeQL-Findings
- **Performance:** Matrix-Endpoint < 500ms (p95)
- **Verfügbarkeit:** 99.9% Uptime

### Business Metriken
- **Nutzerzufriedenheit:** > 4.5/5 (Umfragen)
- **Adoption Rate:** > 80% der Bezirke aktiv
- **Support Tickets:** < 5 pro Monat

---

## 🔗 Abhängigkeiten & Externe Faktoren

### Technische Abhängigkeiten
- PostgreSQL 15+
- Redis für Celery
- Docker & Docker Compose
- OIDC Identity Provider (Keycloak/Authentik)

### Externe Services
- Nager.Date API (Feiertags-Import)
- Google Calendar API
- Microsoft Graph API
- CalDAV Server

---

## 📝 Release-Strategie

### Versionierung
- **Semantic Versioning (SemVer)** gemäß `docs/release-process.md`
- **Conventional Commits** für automatische Changelog-Generierung

### Release-Zyklus
1. **Feature Branches:** `feat/*`, `fix/*`, `refactor/*`
2. **Release Branches:** `release/vX.Y.Z` für finale Tests
3. **Main Branch:** Immer stabil, automatische Releases
4. **Hotfixes:** `hotfix/*` für kritische Bugs

### Deployment
- **Staging:** Automatisch nach Merge in main
- **Produktion:** Manuell nach Release
- **Rollback:** Innerhalb von 2 Stunden möglich

---

## 📞 Kommunikation

### Stakeholder
- **Produktowner:** Requirements, Priorisierung
- **Entwicklungsteam:** Umsetzung, technische Entscheidungen
- **Betrieb:** Deployment, Monitoring
- **Nutzer:** Feedback, Akzeptanztests

### Meetings
- **Wöchentlich:** Standup (15 min)
- **Alle 2 Wochen:** Sprint Review & Planning (60 min)
- **Monatlich:** Steering Committee (30 min)

### Dokumentation
- **Technisch:** In `docs/` und `openspec/`
- **Nutzer:** In `docs/` (VitePress)
- **API:** Swagger/OpenAPI Dokumentation

---

## 🎉 Next Steps

### Sofort (Juni 2026)
1. [ ] **M1 finalisieren:** PlanningSeries Slot Generation Service (3.1)
2. [ ] **M1 finalisieren:** Frontend Matrix UI mit Soll/Ist-Anzeige (5.1)
3. [ ] **M2 starten:** RBAC Guards in auth.py und system.py (3.5, 3.6)

### Kurzfristig (Juli 2026)
1. [ ] **M1 abschließen:** Release v0.23.0
2. [ ] **M2 vorantreiben:** Vollständige Router-Abdeckung
3. [ ] **M3 vorbereiten:** Sync Metadata Design finalisieren

### Mittelfristig (August-September 2026)
1. [ ] **M2 abschließen:** Release v0.24.0
2. [ ] **M3 umsetzen:** Sync-Algorithmus Härtung
3. [ ] **M4 starten:** Audit-Logging

---

## 📎 Anhänge

### A. Offene Issues
- [#94](https://github.com/stritti/nak-district-planner/issues/94): PlanningSlot/EventInstance werden beim Löschen von Events nicht mitgelöscht

### B. Wichtige Dokumente
- [README.md](README.md) - Einstieg & Setup
- [docs/architecture-status.md](docs/architecture-status.md) - Aktueller Architekturstand
- [openspec/architecture/implementation-roadmap.md](openspec/architecture/implementation-roadmap.md) - Technische Roadmap
- [docs/release-process.md](docs/release-process.md) - Release-Prozess
- [docs/security-baseline.md](docs/security-baseline.md) - Sicherheitsanforderungen

### C. Verwendete Standards
- **Conventional Commits:** [https://www.conventionalcommits.org](https://www.conventionalcommits.org)
- **Semantic Versioning:** [https://semver.org](https://semver.org)
- **OpenAPI:** [https://swagger.io/specification/](https://swagger.io/specification/)
- **OWASP Top 10:** [https://owasp.org/Top10/](https://owasp.org/Top10/)

---

**Dokumentenhistorie:**
- v1.0 (22.06.2026): Initialversion basierend auf aktuellem Projektstand

---

*Dieser Projektfahrplan wird regelmäßig aktualisiert und an neue Erkenntnisse angepasst.*
