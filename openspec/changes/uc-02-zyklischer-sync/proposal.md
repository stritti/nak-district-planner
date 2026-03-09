## Why

Einmalig importierte Kalender sind schnell veraltet. Neue, geänderte und gelöschte Termine im externen Kalender müssen automatisch und ohne manuellen Eingriff in das System übernommen werden — sonst ist die Bezirksübersicht unzuverlässig.

## What Changes

- Celery-Task `sync_calendar_integration(integration_id)` für den manuell ausgelösten sowie den zeitgesteuerten Sync
- Celery-Beat-Schedule: alle Integrationen werden alle `sync_interval` Minuten automatisch synchronisiert
- Hash-basierte Deduplizierung: jeder externe Event bekommt einen `content_hash`; Import ist idempotent
- Konfliktlogik: Neu → Create, Geändert (Hash-Diff) → Update, Gelöscht (nicht mehr in Feed) → `status=cancelled` oder Löschen (konfigurierbar per Integration)
- `last_sync_at`-Tracking auf `CalendarIntegration`
- Manueller Sync-Trigger: `POST /calendar-integrations/{id}/sync`

## Capabilities

### New Capabilities

- `calendar-sync`: Celery-Task-Logik für den zyklischen und manuell ausgelösten Kalenderabgleich mit Hash-basierter Deduplizierung

### Modified Capabilities

- `calendar-connector`: Erweiterung um `list_events(from_dt, to_dt)` → Iterable[ExternalEvent] für alle Provider (muss Daten für Hash-Vergleich liefern)

## Impact

- **Backend:** Neuer Celery-Task in `application/tasks/sync_task.py`, erweitertes `CalendarConnector`-ABC
- **Datenbank:** `content_hash`-Spalte auf `events`-Tabelle, `last_sync_at` auf `calendar_integration`
- **Infrastruktur:** Celery Beat benötigt konfigurierten Schedule (redis als Broker/Backend bereits vorhanden)
- **Fehlerbehandlung:** Fehlgeschlagene Syncs werden geloggt und ein Retry-Mechanismus (max. 3 Versuche, exponential backoff) greift
