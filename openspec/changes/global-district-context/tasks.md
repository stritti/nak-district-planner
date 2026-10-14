## 1. Architektur und Spezifikation
- [x] 1.1 Backend-`GET /districts` und bisherigen globalen Store auf Tenant-Zugriff prüfen.
- [x] 1.2 OpenSpec-Proposal, Design und testbare Szenarien anlegen; `frontend-ux` synchronisieren.

## 2. Frontend
- [x] 2.1 Globalen, responsiven Bezirkskontext in der Hauptnavigation integrieren.
- [x] 2.2 Sichtbare Umschaltung auf mehrere vom Backend freigegebene Bezirke begrenzen.
- [x] 2.3 Bezirks-Selects aus Matrixfiltern und Ereignisfiltern entfernen.
- [x] 2.4 Auswahlvalidierung und Schutz gegen alte API-Antworten, Logout und Identitätswechsel ergänzen.

## 3. Tests
- [x] 3.1 Store-Unit-Tests: gültige, fremde und entzogene IDs; Logout und Rennen bei Identitätswechsel.
- [x] 3.2 Component-Unit-Tests: ein/mehrere/keine Bezirke, Sitzung, API-Fehler, Logout.
- [x] 3.3 Bestehende Ereignis- und Matrix-Tests auf globalen Kontext prüfen.
- [x] 3.4 E2E: globaler Wechsel und sichtbare Filterreduktion.
- [x] 3.5 Vollständige CI inkl. Per-File-Coverage-Gate grün verifizieren (Frontend Unit/E2E, Lint und Dokumentation am Commit 7d9b36679).
