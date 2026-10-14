## Warum

Der ursprüngliche Change „code-quality“ (April 2026) bündelte Backend- und Frontend-Aufräumarbeiten. Die Backend-Punkte sind inzwischen umgesetzt und in den Baseline-Specs beschrieben (Connector-Registry und Sync-Ergebnis in `calendar-connector`/`calendar-sync`, `GET /health` in `production-deployment`). Die Annahmen „Google/Microsoft sind `NotImplementedError`-Stubs“ und „Health-Check prüft Redis“ treffen nicht mehr zu: beide Provider-Adapter implementieren Fetches, und der Cache-/Rate-Limit-Dienst ist Valkey. Der zentrale API-Client existiert als `src/api/client.ts` (`apiFetch`).

Offen bleibt die Zerlegung großer Vue-Views: `LeadersAdminView.vue` (~1.400 Zeilen), `EventListView.vue` (~1.050), `CalendarIntegrationsView.vue` (~860) und `DistrictsAdminView.vue` (~800) mischen Filter, Tabellen, Formulare und Modals in einer Datei. `MatrixView.vue` ist bereits in `MatrixFilters.vue` und `MatrixTable.vue` zerlegt.

## Was sich ändert

- Neuzuschnitt (2026-10-07, #475): Scope ist ausschließlich die **Frontend-View-Zerlegung**.
- `EventListView.vue`, `CalendarIntegrationsView.vue`, `LeadersAdminView.vue` und `DistrictsAdminView.vue` delegieren Filter, Listen/Tabellen und Formular-Modals an fokussierte Unterkomponenten.
- Verhalten, Routen und API-Aufrufe bleiben unverändert; bestehende Tests müssen weiter bestehen.

## Nicht-Ziele

- Keine neuen Backend-Anforderungen (Registry, Health-Check, typisierte Sync-Ergebnisse sind erledigt).
- Kein neuer HTTP-Client; `apiFetch` bleibt der zentrale Client.

## Capabilities

### New Capabilities

- `frontend-view-decomposition`: Große Views sind in fokussierte Unterkomponenten zerlegt.

## Impact

- **Frontend:** neue Komponenten unter `src/components/`; die genannten Views werden kleiner.
- **Backend:** keine Änderungen.
