## Why

Die Produktreife-Analyse hat drei akute P0-Lücken identifiziert, die mit geringem Aufwand geschlossen werden können, aber kritische Sicherheits- und Compliance-Risiken darstellen:

1. **Production Guard fehlt:** Die Anwendung startet mit Default-Secrets in Produktion ohne Validierung.
2. **Permission-Checks lückenhaft:** Nicht alle API-Router prüfen konsistent das erforderliche Rollenniveau.
3. **Cross-Tenant-Zugriff nicht getestet:** Es gibt keine Negativtests, die Mandantengrenzen nachweisen.

Ohne diese Absicherungen können Produktivdaten unbemerkt abfließen oder unberechtigt verändert werden.

## What Changes

- **Production Guard:** `config.py` wird um eine `production_guard()`-Funktion erweitert, die beim Start in `APP_ENV=production` folgende Prüfungen vornimmt:
  - `SECRET_KEY` ist nicht der Default-Wert
  - `OIDC_CLIENT_SECRET` ist nicht leer oder ein Platzhalter
  - Debug-Modus ist deaktiviert
  - CORS-Origins sind nicht `["*"]`
  - OIDC-Redirect-URIs sind auf HTTPS in Produktion
- **Permission-Audit:** Systematische Prüfung aller API-Router auf korrekte Permission-Guards, Schließen aller Lücken, insbesondere:
  - congregation-level scoping für `CONGREGATION_ADMIN`
  - Einheitliches Minimum-Role-Level pro Endpunkt gemäß `docs/roles.md`
  - Negative-Tests für jede geschützte Route (403 bei falscher Rolle)
- **Cross-Tenant-Tests:** API-Tests, die nachweisen:
  - User aus Bezirk A kann keine Daten aus Bezirk B lesen
  - User aus Bezirk A kann keine Daten in Bezirk B schreiben
  - Superadmin kann (explizit) bezirksübergreifend agieren
  - Admin-Sonderrechte sind explizit, nicht zufällig

## Capabilities

### New Capabilities
- `production-guard`: Startup-Validierung der Produktionskonfiguration mit blockierenden Fehlern bei unsicheren Werten.

### Modified Capabilities
- `scoped-membership-enforcement`: Vollständige Abdeckung aller Router mit konsistenten Permission-Guards.
- Testinfrastruktur: Cross-Tenant-Negativtests als verbindlicher CI-Bestandteil.

## Impact

- Backend: `config.py`-Erweiterung, Router-Audit, neue Tests.
- Betrieb: Fehlgeschlagener Produktionsstart bei unsicherer Konfiguration.
- CI: Neue Testkategorie (Cross-Tenant) in `ci.yml`.
- Dokumentation: Production-Config-Checklist in `production-runbook.md`.
