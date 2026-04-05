## Warum

Die Analyse des NAK District Planners gegen die OpenSpec-Spezifikationen (April 2026) hat
mehrere Code-Qualitätsprobleme identifiziert, die die Wartbarkeit, Testbarkeit und
Verständlichkeit des Codes beeinträchtigen. Dazu zählen: manuelle Factory-Ketten im
Sync-Service, ungesicherte Google/Microsoft-OAuth-Stubs, ein unstrukturierter Frontend-API-Client,
große monolithische Vue-Komponenten sowie fehlende Typisierung in der Application-Schicht.
Außerdem fehlt ein standardisierter Health-Check-Endpoint für Docker-Umgebungen.

## Was sich ändert

- Connector-Factory im Sync-Service durch ein Dictionary-Registry-Pattern ersetzen.
- Google/Microsoft-Kalender-Stubs mit `NotImplementedError` und UI-Badge „Coming soon" kennzeichnen.
- Zentralen HTTP-Client-Wrapper im Frontend einführen (Auth-Token-Injection, globale Fehlerbehandlung).
- Große Vue-Views in kleinere Unterkomponenten aufteilen (`EventListView`, `CalendarIntegrationsView`,
  `MatrixView`).
- Typisierte Ergebnis-Objekte (`SyncResult`, etc.) statt `dict[str, int]` einführen.
- Konsistentes Dependency-Injection-Muster in FastAPI-Routern etablieren.
- Health-Check-Endpoint `GET /health` einführen.

## Capabilities

### New Capabilities

- `backend-code-quality`: Refactored sync factory, typed result objects, DI patterns, health check
- `frontend-code-quality`: Centralized HTTP client, decomposed view components, OAuth stub UX

### Modified Capabilities

- `calendar-sync` (uc-02): `_get_connector()` nutzt Registry statt `if/elif`-Kette

## Impact

- **Backend:** `sync_service.py` refactored; neuer `GET /health`-Endpoint; Pydantic-Dataclass
  `SyncResult`; alle Router auf konsistentes `Depends()`-Muster umgestellt
- **Frontend:** Neuer `httpClient.ts`-Wrapper; `EventListView.vue`, `CalendarIntegrationsView.vue`,
  `MatrixView.vue` jeweils in Sub-Komponenten aufgeteilt; OAuth-Stubs im UI markiert
- **Abhängigkeiten:** Keine neuen externen Abhängigkeiten
