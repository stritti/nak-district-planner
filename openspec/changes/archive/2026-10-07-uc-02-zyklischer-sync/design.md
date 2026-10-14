## Context

Celery ist bereits als Worker-Service im Docker-Compose vorhanden (`services/backend/app/celery_app.py`). Redis dient als Broker und Result-Backend. Der `CalendarConnector`-ABC aus UC-01 ist Voraussetzung.

Ziel des Sync-Tasks ist Idempotenz: Mehrfaches Ausführen für denselben Zeitraum darf keine Duplikate erzeugen.

## Goals / Non-Goals

**Goals:**
- Celery-Task `sync_calendar_integration(integration_id: UUID)` mit vollständiger Sync-Logik (Create/Update/Cancel)
- Hash-basierte Deduplizierung via `content_hash` auf dem `events`-Datensatz
- Celery-Beat-Schedule: für jede aktive Integration alle `sync_interval` Minuten
- Retry-Mechanismus: max. 3 Versuche, exponentieller Backoff (60 s, 300 s, 900 s)
- Manueller Sync-Trigger-Endpoint: `POST /api/v1/calendar-integrations/{id}/sync`
- `last_sync_at`-Aktualisierung nach erfolgreichem Lauf

**Non-Goals:**
- Write-Back geänderter Events zum externen Provider
- Realtime-Updates via Webhooks (Webhook-Support ist spätere Phase)
- Parallelisierung mehrerer Integrationen im selben Task

## Decisions

### Hash-Strategie
**Entscheidung:** `content_hash = SHA-256(uid + start_dt.isoformat() + summary + description)`. Nur diese vier Felder bestimmen "hat sich etwas geändert".

Alternativen: Vollständiger JSON-Hash (unstabil bei unwichtigen Feldern), `last_modified` des Providers (nicht alle Provider liefern das zuverlässig).

### Gelöschte Events: Cancel statt Delete
**Entscheidung:** Events, die nicht mehr im externen Feed erscheinen, werden auf `status=cancelled` gesetzt (konfigurierbar per Integration via `on_delete: cancel | delete`). Default: `cancel`.

**Begründung:** Historische ServiceAssignments und Audit-Einträge bleiben erhalten. Hard-Delete nur wenn explizit konfiguriert.

### Celery Beat vs. cron
**Entscheidung:** Celery Beat mit dynamischem Schedule (aus DB-Wert `sync_interval`). Schedule wird beim Start aus DB geladen und kann zur Laufzeit aktualisiert werden.

Risiko: Beat-State liegt im Redis; bei Redis-Neustart ohne Persistence werden Schedules erst beim nächsten App-Start neu geladen → kein Datenverlust, maximal 1 fehlender Sync.

## Risks / Trade-offs

- [Risiko] Externe Provider-API down → Task schlägt fehl → **Mitigation:** Retry + Dead Letter Queue, `last_sync_error` auf Integration speichern
- [Trade-off] Sync-Fenster ist immer "letztes Sync-Datum bis jetzt" — bei sehr langen Ausfällen kann dies zu langen API-Abfragen führen → akzeptiert (NAK-Kalender haben geringe Datenmenge)

## Migration Plan

1. `content_hash`-Spalte auf `events` via Alembic-Migration ergänzen
2. `sync_task.py` implementieren mit Mock-Connector für Unit-Tests
3. Celery-Beat-Config aktivieren
4. Integration-Test mit lokalem ICS-File
5. Rollback: Task kann deaktiviert werden ohne DB-Änderung
