# Engineering Standards

Dieses Dokument definiert verbindliche Entwicklungsstandards fuer den NAK District Planner.

## 1. Architekturregeln

- Backend folgt Hexagonal Architecture (Domain, Application, Adapters).
- Domain-Modelle enthalten keine Framework-Abhaengigkeiten.
- Zugriff auf externe Systeme nur ueber Ports/Adapter.
- Berechtigungspruefung erfolgt im Application Layer, nicht nur im Router.

## 2. Clean-Code-Regeln

- Kleine, klar abgegrenzte Module mit einer Verantwortung.
- Keine impliziten Seiteneffekte in Service-Methoden.
- Explizite Typen in Python und TypeScript fuer API-nahe Strukturen.
- Konsistente Benennung (Deutsch fuer Fachbegriffe, Englisch fuer technische Begriffe).
- Legacy-Code wird mit TODO + OpenSpec-Referenz markiert statt still erweitert.

## 3. API- und Fehlerhandling

- API-Fehler liefern konsistente HTTP-Statuscodes und strukturierte Payloads.
- Sicherheitsrelevante Fehler enthalten keine sensitiven Details.
- Externe Connector-Fehler werden in domainenahen Ergebnissen zusammengefasst.

## 4. Teststandards

- Unit-Tests fuer Domain- und Kern-Application-Logik.
- Integrationstests fuer DB, API und Sync-Schnittstellen.
- Frontend-Komponententests fuer zentrale Interaktionen.
- E2E-Tests fuer kritische Auth- und Planungsfluesse.

Siehe auch `docs/coverage-strategy.md`.

## 5. Definition of Done (DoD)

Ein Ticket gilt als fertig, wenn:

1. Funktionales Verhalten gemaess Akzeptanzkriterien umgesetzt ist.
2. Relevante Tests hinzugefuegt/angepasst wurden.
3. Lint, Type-Checks und Build erfolgreich sind.
4. Sicherheits- und Rollenregeln eingehalten sind.
5. Betroffene Dokumentation aktualisiert wurde.

## 6. Pull-Request-Checkliste

- [ ] Architekturgrenzen eingehalten (Domain unabhaengig)
- [ ] Rechtepruefung fuer schreibende Operationen vorhanden
- [ ] Tests fuer neues Verhalten enthalten
- [ ] Keine Secrets oder sensible Dumps im Diff
- [ ] Dokumentation aktualisiert (falls fachlich/operativ relevant)
