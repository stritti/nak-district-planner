## Kontext

Der NAK District Planner ist in Phase 1 der Roadmap und hat einen funktionierenden MVP.
Mit zunehmender Komplexität (Planning-Slot-Modell, RBAC, Sync-Algorithmus) werden Code-Qualität
und Testbarkeit wichtiger. Folgende spezifische Probleme wurden in der Analyse identifiziert:

1. `_get_connector()` in `sync_service.py` ist eine `if/elif`-Kette — neue Provider erfordern
   manuelle Erweiterung an mehreren Stellen.
2. `GoogleCalendarConnector` und `MicrosoftGraphCalendarConnector` sind leere Stubs ohne
   Warnung — verwirrend für Nutzer und Entwickler.
3. Frontend-API-Calls fehlt ein zentraler Wrapper: Auth-Header-Injection und globale
   Fehlerbehandlung sind in jedem Store dupliziert.
4. `EventListView.vue` (870 Zeilen), `CalendarIntegrationsView.vue` (852 Zeilen) und
   `MatrixView.vue` (440 Zeilen) sind zu groß für einfache Code-Reviews und Tests.
5. Services geben `dict[str, int]` zurück — kein Type Safety, keine IDE-Unterstützung.
6. Kein standardisierter `GET /health`-Endpoint für Docker Compose Healthchecks.

## Ziele / Nicht-Ziele

**Ziele:**

- Connector-Factory als Dictionary-Registry; einfache Erweiterbarkeit für neue Kalender-Provider.
- OAuth-Stubs klar als „nicht implementiert" kennzeichnen — in Python und in der UI.
- Zentralen `httpClient.ts` mit Axios oder nativem Fetch einführen.
- Große Vue-Views in logische Unterkomponenten aufteilen.
- `SyncResult`-Dataclass einführen.
- Alle FastAPI-Router auf konsistentes `Depends()`-DI-Muster umstellen.
- `GET /health`-Endpoint mit DB- und Redis-Ping.

**Nicht-Ziele:**

- Vollständige Google/Microsoft-OAuth-Implementierung (separates Change-Item).
- Komplette Test-Suite (Grundlage verbessern, aber keine vollständige Abdeckung garantieren).

## Entscheidungen

### 1. Connector-Registry

**Entscheidung:** Ein Modul-Level-Dictionary `_CONNECTOR_MAP: dict[CalendarType, type[CalendarConnector]]`
ersetzt die `if/elif`-Kette. Neue Provider werden durch Eintrag im Dictionary registriert.

### 2. OAuth-Stubs

**Entscheidung:** Stubs werfen `NotImplementedError` mit Klarnamen-Meldung. UI zeigt Badge
„In Kürze verfügbar" und deaktiviert das Formular für Google/Microsoft-Typen.

### 3. Frontend HTTP-Client

**Entscheidung:** `services/api/httpClient.ts` als `axios`-Instanz (oder `ky` / nativer fetch)
mit Interceptors für Auth-Header und globale Fehlerbehandlung. Alle ressourcen-spezifischen
API-Dateien delegieren an diesen Client.

**Alternativ geprüft:** Kein externer HTTP-Client → nativ `fetch` mit Wrapper-Funktion.
Da `axios` bereits transitiv vorhanden ist und Interceptors standardmäßig bietet, wird axios
bevorzugt. Falls nicht vorhanden: nativer `fetch` mit einem einfachen Wrapper.

### 4. View-Decomposition

**Entscheidung:**

```text
EventListView.vue  →  EventFilters.vue + EventTable.vue + EventFormModal.vue
CalendarIntegrationsView.vue  →  IntegrationCard.vue + IntegrationFormModal.vue
MatrixView.vue  →  MatrixFilters.vue + MatrixTable.vue  (AssignmentModal existiert bereits)
```

### 5. SyncResult

**Entscheidung:** Pydantic-Dataclass `SyncResult(created, updated, cancelled, errors)` im
`application/`-Layer. Celery-Task und API-Response nutzen dasselbe Objekt.

### 6. Health-Check

**Entscheidung:** `GET /health` (kein `/api/v1`-Präfix) gibt `{ status, db, redis, version }`
zurück. Docker Compose `healthcheck` referenziert diesen Endpoint.

## Risiken / Trade-offs

- [Axios-Abhängigkeit] Falls `axios` nicht im Frontend vorhanden: nativem `fetch`-Wrapper
  bevorzugen, um Abhängigkeiten minimal zu halten.
- [View-Decomposition] Aufwand je View ~0,5–1 Tag; keine funktionale Änderung, daher risikoarm.

## Migrationsplan

1. Backend: `SyncResult`-Dataclass + Connector-Registry + Health-Endpoint.
2. Backend: Router-DI-Muster standardisieren.
3. Frontend: `httpClient.ts` einführen; API-Stores migrieren.
4. Frontend: View-Komponentenzerlegung (eine View pro Iteration).
5. Frontend: OAuth-Stubs in UI kennzeichnen.
