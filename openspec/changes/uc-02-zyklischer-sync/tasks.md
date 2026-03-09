## 1. Datenbankschema erweitern

- [x] 1.1 `content_hash` auf `events`-Tabelle → Migration 0002
- [ ] 1.2 `last_sync_error` auf `calendar_integration`-Tabelle → **fehlt!** Nur `last_synced_at` ist implementiert, kein `last_sync_error`-Feld
- [x] 1.3 SQLAlchemy-Modelle entsprechend aktualisiert

## 2. CalendarConnector-ABC erweitern

- [x] 2.1 `fetch_events(credentials, from_dt, to_dt)` im ABC → implementiert als `fetch_events()` (leicht abweichender Name ggü. `list_events()` im Design)
- [x] 2.2 `ICalConnector.fetch_events()` mit Zeitraum-Filterung implementiert
- [x] 2.3 Unit-Tests für `fetch_events()` mit Zeitraum-Fixtures → `tests/unit/test_ical_connector.py`

## 3. Sync-Task implementieren

- [x] 3.1 Celery-Task `sync_calendar_integration(integration_id)` in `application/tasks.py`
- [x] 3.2 Hash-Vergleichs-Logik (SHA-256 über uid + start + end + title) in `sync_service.py`
      ⚠️ **Abweichung:** Hash über 4 Felder: uid, start, end, title (Design spezifiziert: uid, start, summary, description)
- [x] 3.3 Create/Update/Cancel-Logik: NEU → Create (source=EXTERNAL, status=DRAFT), GEÄNDERT → Update, GELÖSCHT/is_cancelled → status=CANCELLED
- [x] 3.4 Retry-Konfiguration: `max_retries=3`, `default_retry_delay=60s`
      ⚠️ **Abweichung:** Backoff-Staffelung (60/300/900s) nicht implementiert — alle Retries mit festem 60s Delay
- [x] 3.5 `last_sync_at` wird nach Sync-Lauf aktualisiert
- [ ] 3.5 `last_sync_error` speichern nach Fehlschlag → fehlt (kein DB-Feld vorhanden, siehe 1.2)

## 4. Unit-Tests

- [x] 4.1 Unit-Tests für `sync_calendar_integration` mit Mock-Connector und -Repository → `tests/unit/test_sync_service.py` (11 Tests)
- [x] 4.2 Idempotenz-Test: zweimaliger Sync desselben Feeds erzeugt keine Duplikate

## 5. Celery Beat konfigurieren

- [x] 5.1 Celery-Beat-Schedule in `celery_app.py`: `sync_all_active_integrations` alle 5 Minuten → prüft `last_synced_at` vs. `sync_interval` pro Integration
      ⚠️ **Abweichung:** Kein dynamischer Per-Integration-Schedule — stattdessen zentraler Polling-Task alle 5 Min, der `sync_interval` pro Integration prüft
- [x] 5.2 Celery-Worker in `docker-compose.yml` konfiguriert

## 6. Manueller Sync-Endpoint

- [x] 6.1 `POST /api/v1/calendar-integrations/{id}/sync` implementiert
      ⚠️ **Abweichung:** Synchrone Ausführung (kein Celery-Task-Dispatch, kein HTTP 202 + Task-ID) — `run_sync()` läuft direkt im Request-Kontext
- [ ] 6.2 Integrations-Test für manuellen Sync-Trigger

## 7. Frontend

- [x] 7.1 "Jetzt synchronisieren"-Button in `CalendarIntegrationsView.vue`
- [ ] 7.2 `last_sync_at` und `last_sync_error` in der Integrationsansicht anzeigen (`last_sync_error` fehlt auch im Backend)
