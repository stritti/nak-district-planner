## 1. Architekturgrenze

- [x] 1.1 AST-basierten Test fuer `app.application -> app.adapters` einfuehren.
- [x] 1.2 Bestehende Adapter-Imports als explizite Legacy-Allowlist dokumentieren.
- [x] 1.3 Direkte SQLAlchemy-Imports im Application-Layer ebenfalls einfrieren.
- [x] 1.4 Stale-Allowlist-Erkennung ergaenzen, damit technische Schulden nur sinken koennen.

## 2. Release-Metadaten

- [ ] 2.1 FastAPI-Version auf `settings.app_version` als zentrale Paketversion umstellen.
- [ ] 2.2 Regressionstest fuer die FastAPI/OpenAPI-Version ergaenzen.

## 3. RC-2 Dokumentation

- [ ] 3.1 Production Runbook auf aktuellen Superadmin-Bootstrap und Required Checks aktualisieren.
- [ ] 3.2 Architekturstatus um die eingefrorene Application/Adapter-Grenze und den Abbaupfad ergaenzen.
- [ ] 3.3 Security-Status mit den RC-2-Vertrauensgrenzen synchronisieren.
- [ ] 3.4 Abgeschlossene OpenSpec-Changes archivieren; `approved-idp-login-scoped-access` aus dem aktiven Bereich verschieben.

## 4. Verifikation

- [ ] 4.1 Architekturtests inklusive negativer Ausnahmefaelle bestehen.
- [ ] 4.2 Backend-Test-Suite mit Coverage >80 % besteht.
- [ ] 4.3 MegaLinter, Security Scans und Dokumentations-Build bestehen.
