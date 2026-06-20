## 1. Production Guard

- [x] 1.1 `production_guard()`-Funktion in `app/config.py` implementieren
  - SECRET_KEY-Längen- und Default-Prüfung
  - OIDC_CLIENT_SECRET-Platzhalter-Prüfung
  - ~DEBUG-Verbot in Production~ *(entfällt — kein globales DEBUG-Flag im Projekt)*
  - ~CORS-Wildcard-Verbot in Production~ *(entfällt — CORS wird durch Reverse Proxy geregelt)*
  - ~OIDC-Redirect-URI-HTTPS-Prüfung~ *(entfällt — Redirect-URI wird nicht in Config geführt)*
- [x] 1.2 `production_guard` im `lifespan`-Event von `main.py` aufrufen (nur bei `APP_ENV=production`)
- [x] 1.3 Unit-Tests für `production_guard()` schreiben:
  - Default-Secrets → Startup blockiert
  - Gültige Konfiguration → Startup ok
  - Entwicklungsmodus → Guard übersprungen
- [x] 1.4 `.env.example` bereinigen: Platzhalter deutlich als solche markieren (z. B. `replace-with-...`)
- [x] 1.5 Secret-Livecycle-Dokumentation in `production-runbook.md` ergänzt

## 2. Permission-Audit

- [x] 2.1 Alle Router-Dateien auf vorhandene `assert_has_role_in_*`-Guards scannen
  - `routers/events.py`
  - `routers/districts.py`
  - `routers/leaders.py`
  - `routers/service_assignments.py`
  - `routers/calendar_integrations.py`
  - `routers/invitations.py`
  - `routers/export.py`
  - `routers/registrations.py`
  - `routers/system.py`
  - `routers/auth.py`
- [x] 2.2 Auditergebnis mit `docs/roles.md` abgleichen, Abweichungen dokumentiert
- [x] 2.3 Fehlende Guards ergänzt (congregation_admin-Scoping in 3 Routern)
- [x] 2.4 `CONGREGATION_ADMIN`-Scoping implementiert:
  - Try/Fallback-Pattern: congregation_admin → district-level role
  - `events.py`: create/update mit congregation-Fallback
  - `calendar_integrations.py`: create/update/delete mit congregation-Fallback
  - `districts.py`: update_congregation mit congregation-Fallback
- [ ] 2.5 Negative-Tests für jede geschützte Route (403 bei falscher Rolle) *— Integrationstest-Aufgabe, wird in Paket C abgedeckt*
- [x] 2.6 Test: `CONGREGATION_ADMIN` kann nur eigene Gemeinde bearbeiten

## 3. Cross-Tenant-Tests

- [x] 3.1 Test-Factory für mandantenfähige Testszenarien erstellt
- [x] 3.2 Cross-Tenant-Read-Tests (6 Tests)
- [x] 3.3 Cross-Tenant-Write-Tests (4 Tests)
- [x] 3.4 Admin-Sonderrechte-Test: Superadmin darf bezirksübergreifend agieren (5 Tests)
- [x] 3.5 Parametrisierte Tests über alle Rollen hinweg (VIEWER, PLANNER, CONGREGATION_ADMIN, DISTRICT_ADMIN — 12 Tests)

## 4. Dokumentation

- [x] 4.1 Production-Runbook um Config-Checkliste ergänzt
- [x] 4.2 Permission-Matrix in `docs/roles.md` mit Status der Router-Abdeckung aktualisiert
- [x] 4.3 Secret-Lifecycle-Dokumentation (Erzeugung, Rotation, Recovery) in `production-runbook.md` ergänzt
