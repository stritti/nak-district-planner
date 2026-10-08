## 1. Tests (rot)

- [x] 1.1 API: Anlegen von GOOGLE/MICROSOFT → 422; Typänderung per PATCH → 422; bestehende GOOGLE-Integration bleibt lesbar
- [x] 1.2 Manueller Sync einer GOOGLE/MICROSOFT-Integration → 409 ohne Connector-Aufruf
- [x] 1.3 `run_sync` verweigert nicht unterstützte Typen; `sync_all_active_integrations` überspringt sie mit Log
- [x] 1.4 Frontend: Typauswahl nur ICS/CalDAV aktiv, Google/Microsoft „geplant“ und deaktiviert; Sync-Button für Bestandsintegrationen deaktiviert

## 2. Umsetzung

- [x] 2.1 `SUPPORTED_CALENDAR_TYPES` und `UnsupportedCalendarTypeError` im Domain-Layer
- [x] 2.2 Router-Prüfung bei Create (422) und Sync (409); `CalendarIntegrationUpdate` mit `extra="forbid"`
- [x] 2.3 Guard in `run_sync`, Filter in `sync_all_active_integrations`, kein Celery-Retry für den Fehler
- [x] 2.4 UI-Anpassung in `CalendarIntegrationsView.vue`
- [x] 2.5 README/Docs aktualisieren; Connector-Code unverändert behalten

## 3. Review-Nacharbeiten (Codex)

- [x] 3.1 Ausgehende Schreibzugriffe (`push_deviation_resolution`, `push_conflict_resolution`) für GOOGLE/MICROSOFT verweigern → 409 statt 502
