## Why

Planungssoftware braucht harte Konfliktregeln. Ohne diese bleibt der NAK District Planner ein Datenerfassungssystem – kein verlässlicher Planer. Die Produktreife-Analyse bewertet dies als das zentrale P1-Risiko:

- **Double-Booking:** Ein Amtsträger kann aktuell zeitgleich in mehreren Gemeinden eingeplant werden.
- **Wechselzeiten:** Räumlich getrennte Gemeinden mit direkt aufeinanderfolgenden Terminen werden nicht erkannt.
- **Rollenanforderungen:** Es wird nicht geprüft, ob ein Dienst eine bestimmte Amtsstufe erfordert.
- **Abwesenheiten:** Urlaube und Sperrzeiten werden nicht berücksichtigt.

Hinzu kommen Frontend-Qualitätslücken: unzureichendes Onboarding, fehlende Fehlerzustände und keine E2E-Tests für die kritischen Planungsflows.

## What Changes

- **Domain Conflict Service:** Zentrale Konfliktengine im `domain/planning/`-Paket
  - `conflict_rules.py`: Deklarative Regeln (Double-Booking, Wechselzeiten, Rollenanforderungen)
  - `conflict_service.py`: Orchestrierung der Regeln für Event-Erstellung und ServiceAssignment
  - `conflict_result.py`: Ergebnisobjekt (PASS, WARN, BLOCK) mit menschenlesbaren Nachrichten
- **DB-Migration für Abwesenheiten/Sperrzeiten:** `leader_unavailability`-Tabelle
- **Integration in bestehende Services:** Event-Erstellung und ServiceAssignment rufen Conflict Service auf
- **Frontend-Konfliktanzeige:** Modal/Inline-Anzeige von Konflikten bei der Planung
- **E2E-Tests für Planungsflows:** Playwright-Tests für Matrix-Ansicht, Dienstzuweisung, Konfliktanzeige
- **Frontend-Validierung:** Formular-Validierung, Fehlerzustände, Rollenführung im UI

## Capabilities

### New Capabilities
- `domain-conflict-engine`: Zentrale Prüfengine für Planungskonflikte mit erweiterbaren Regeln.
- `leader-unavailability`: Abwesenheits- und Sperrzeitenverwaltung für Amtsträger.
- `e2e-planning-flows`: Playwright-Tests für die drei kritischen Planungsflows.

### Modified Capabilities
- `service-assignment`: Ruft Conflict Service vor Zuweisung auf.
- `event-creation`: Ruft Conflict Service bei Terminerstellung auf.
- Matrix-UI: Konfliktanzeige in der Matrix-Ansicht und im Zuweisungsdialog.
- Frontend-Formulare: Validierung, Fehleranzeige, rollengeführte Navigation.

## Impact

- Backend: Neues `domain/planning/conflict_*.py`, Integration in Application Services, neue Migration.
- Frontend: Konfliktanzeige-Komponenten, validierte Formulare, verbessertes Onboarding.
- Tests: Neue Unit-Tests für Conflict Service, neue E2E-Tests.
- CI: Playwright-E2E-Tests in CI-Pipeline (bestehend, aber erweitert).
