## ADDED Requirements

### Requirement: Idempotenter Sync via Hash-Vergleich
Das System SHALL jeden externen Event mit einem `content_hash` (SHA-256 über UID, Start, Titel, Beschreibung) versehen. Wiederholte Sync-Läufe für denselben Zeitraum DÜRFEN KEINE Duplikate erzeugen.

#### Scenario: Unveränderter Event wird nicht doppelt angelegt
- **WHEN** ein Sync-Lauf einen Event findet, der bereits in der DB liegt und denselben `content_hash` hat
- **THEN** wird der Event unverändert belassen (kein UPDATE, kein INSERT)

#### Scenario: Geänderter Event wird aktualisiert
- **WHEN** ein Sync-Lauf einen Event findet, der bereits in der DB liegt, aber einen anderen `content_hash` hat
- **THEN** wird der Event aktualisiert und `content_hash` neu gesetzt

#### Scenario: Neuer Event wird angelegt
- **WHEN** ein Sync-Lauf einen Event findet, der noch nicht in der DB liegt
- **THEN** wird ein neuer Event mit `source=EXTERNAL` angelegt

### Requirement: Gelöschte Events werden als cancelled markiert
Das System SHALL externe Events, die nicht mehr im Feed erscheinen, auf `status=cancelled` setzen (Standard). Wenn die Integration `on_delete=delete` konfiguriert hat, SOLL der Event stattdessen gelöscht werden.

#### Scenario: Event nicht mehr im Feed (Standard)
- **WHEN** ein Sync-Lauf einen DB-Event nicht mehr im externen Feed findet und `on_delete=cancel`
- **THEN** wird der Event auf `status=cancelled` gesetzt

#### Scenario: Event nicht mehr im Feed (Hard Delete)
- **WHEN** ein Sync-Lauf einen DB-Event nicht mehr im externen Feed findet und `on_delete=delete`
- **THEN** wird der Event aus der DB gelöscht

### Requirement: Automatischer Sync via Celery Beat
Das System SHALL jede aktive `CalendarIntegration` automatisch gemäß ihrem `sync_interval` (in Minuten) synchronisieren.

#### Scenario: Integration hat sync_interval=60
- **WHEN** 60 Minuten seit dem letzten Sync vergangen sind
- **THEN** wird der Sync-Task für diese Integration automatisch ausgelöst

### Requirement: Manueller Sync-Trigger
Das System SHALL einen API-Endpoint `POST /api/v1/calendar-integrations/{id}/sync` bereitstellen, der einen sofortigen Sync auslöst.

#### Scenario: Manueller Sync-Aufruf
- **WHEN** `POST /api/v1/calendar-integrations/{id}/sync` aufgerufen wird
- **THEN** wird ein Celery-Task in die Queue gestellt und HTTP 202 mit der Task-ID zurückgegeben

### Requirement: Fehlerbehandlung mit Retry
Das System SHALL bei fehlgeschlagenen Sync-Versuchen (Provider-Fehler, Netzwerktimeout) bis zu 3 Mal mit exponentiellem Backoff (60 s, 300 s, 900 s) erneut versuchen.

#### Scenario: Provider antwortet nicht
- **WHEN** der externe Kalender-Provider beim Sync nicht erreichbar ist
- **THEN** wird der Task mit Backoff bis zu 3 Mal wiederholt und der Fehler in `last_sync_error` auf der Integration gespeichert

#### Scenario: Alle Retries erschöpft
- **WHEN** alle 3 Retry-Versuche fehlschlagen
- **THEN** wird der Task als fehlgeschlagen markiert und ein Fehler-Log-Eintrag erzeugt
