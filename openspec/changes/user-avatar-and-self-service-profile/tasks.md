## 1. Spezifikation und Schnittstellen
- [x] 1.1 Istzustand von AppNav, OIDC-Identität, Benutzer-Repository, Profil-Endpoint und Frontend-UX prüfen.
- [x] 1.2 OpenSpec-Proposal, Architekturentscheidung und prüfbare Delta-Requirements für Avatar und Self-Service-Profil dokumentieren.
- [ ] 1.3 Beim Umsetzen die Implementierung mit allen OpenSpec-Anforderungen abgleichen und die Baseline-Specs beim Abschluss der Änderung aktualisieren.

## 2. Backend und Datenbank
- [ ] 2.1 Profil-Override-Migration mit FK, eigenen RLS-Policies und DML-Rechten auf das eigene `sub` erstellen; sicherer Downgrade.
- [ ] 2.2 Profil-Repository und Service von OIDC-Stammdaten und RBAC trennen.
- [ ] 2.3 `GET /api/v1/profile/me` mit wirksamen Fallbacks für fehlende Claims und Pending-Accounts implementieren.
- [ ] 2.4 `PUT /api/v1/profile/me` atomar, strikt validiert und subjectgebunden implementieren; `null` als Reset.
- [ ] 2.5 Unveränderlichkeit der Identitäts- und Berechtigungsfelder, Datenschutz und providerunabhängigen Konto-Link prüfen.

## 3. Frontend
- [ ] 3.1 Reine Initialen-/Avatar-Komponente (Unicode, Fallback, Kontrast, ohne Bilder) bauen.
- [ ] 3.2 `AppNav` um kompakten Avatar-Auslöser und zugängliches Dropdown mit Profil und Logout erweitern.
- [ ] 3.3 Geschützte `/account`-Route und Self-Service-Formular mit Validierung, Speichern, Fehler- und Reset-Zustand erstellen.
- [ ] 3.4 Profilzustand nach Save neu laden und sauber nach Logout, Sessionwechsel oder verzögerten Antworten leeren.
- [ ] 3.5 Optional konfigurierten Konto-Link nur aus vertrauenswürdiger Betreiberkonfiguration anzeigen.

## 4. Tests und Qualitätsgates
- [ ] 4.1 Backend-Unit-Tests: PUT/GET, Namens-Override und Reset, Provider-Fallback, Pending, `401`/`422`, DB-Fehler/Rollback, Subject-Spoofing.
- [ ] 4.2 PostgreSQL-RLS-Integrationstests: Benutzer A darf B weder lesen noch schreiben; INSERT/UPDATE/DELETE fail-closed, fehlende Context-Variable.
- [ ] 4.3 Frontend-Unit-Tests: Initialen inklusive Unicode und fehlender Claims; responsives, zugängliches Menü; Speicher-/Netzwerkfehler; stale responses und Logout.
- [ ] 4.4 E2E: Profilbearbeitung, persistente Darstellung nach Reload, Reset, Konto-Link mit/ohne Konfiguration, Keyboard, Mobil und Pending Approval.
- [ ] 4.5 OpenSpec strikt validieren; Lint, Build, Backend-/Frontend-Tests, RLS, E2E und CI vollständig prüfen. Coverage >80 % in betroffenen Production-Dateien; bestehendes Gate nicht abschwächen.
