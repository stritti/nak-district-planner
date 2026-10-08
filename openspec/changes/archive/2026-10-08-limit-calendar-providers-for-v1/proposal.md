## Why

Issue #467: Die Google- und Microsoft-Connectoren lesen ein statisch hinterlegtes `access_token`. Es gibt weder OAuth-Flow noch Token-Refresh, daher bricht die Synchronisierung etwa eine Stunde nach der Einrichtung ab. Für Version 1.0 werden offiziell nur ICS und CalDAV unterstützt, damit keine Integration angelegt werden kann, die zwangsläufig ausfällt.

## What Changes

- Domain-Konstante `SUPPORTED_CALENDAR_TYPES = {ICS, CALDAV}` und Fehler `UnsupportedCalendarTypeError`.
- API: Anlegen von `GOOGLE`/`MICROSOFT`-Integrationen → HTTP 422 mit klarer Meldung; der Typ ist bei PATCH nicht änderbar (unbekannte Felder → 422).
- Bestehende `GOOGLE`/`MICROSOFT`-Integrationen bleiben lesbar und bearbeitbar, werden aber von `sync_all_active_integrations` mit Warn-Log übersprungen; `run_sync` verweigert sie (kein Celery-Retry), der manuelle Sync-Endpunkt antwortet mit HTTP 409.
- UI: Typauswahl bietet nur ICS und CalDAV an; Google/Microsoft erscheinen deaktiviert als „geplant“. Bestehende Integrationen zeigen den Hinweis „in Version 1.0 nicht unterstützt“, der Sync-Button ist deaktiviert.
- Connector-Code für Google/Microsoft bleibt erhalten (Backlog nach 1.0); seine Sync-Tests laufen mit explizit freigeschalteten Typen weiter.
- README, `docs/use-cases.md`, CLAUDE.md aktualisiert.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `calendar-connector`: Provider-Umfang für Version 1.0 auf ICS und CalDAV begrenzt.

## Impact

- Backend: Router `calendar_integrations.py`, Schema `CalendarIntegrationUpdate`, `sync_service.run_sync`, `tasks.sync_all_active_integrations`, Domain-Modell/Fehler.
- Frontend: `CalendarIntegrationsView.vue` (+ Test).
- Bestandsdaten: keine Migration; betroffene Integrationen bleiben gespeichert und können gelöscht oder später reaktiviert werden.
