## Why

Termine des Bezirks (z. B. Ämterstunden, Bezirksgottesdienste) müssen in Gemeindekalendern sichtbar sein, ohne sie dort separat anlegen zu müssen (UC-04). Mitglieder und Amtsträger sollen Termine als ICS-Feed abonnieren können, ohne sich einzuloggen (UC-05). Gesetzliche und kirchliche Feiertage müssen automatisch im System vorhanden sein, damit die Dienstmatrix korrekte Spalten zeigt (UC-06).

## What Changes

**UC-04 – Event-Verteilung:**
- `applicability`-Feld am Event (Liste von Gemeinde-IDs oder `"all"`)
- Events mit `status=PUBLISHED` + passendem `applicability`-Eintrag erscheinen in der Gemeindeansicht
- Kein physisches Kopieren: virtuelles Einblenden über Filter-Logik im Endpoint `GET /congregations/{id}/events`

**UC-05 – ICS-Export:**
- Neuer öffentlicher Endpoint: `GET /api/v1/export/{token}/calendar.ics` (kein Auth-Header nötig)
- Export-Tokens: `PUBLIC` (nur `visibility=PUBLIC, status=PUBLISHED`, ServiceAssignment-Namen anonymisiert) und `INTERNAL` (inkl. `visibility=INTERNAL`, volle Namen)
- Stabile UIDs: `{district_id}-{event_id}@nak-planner` — ändert sich nie
- CRUD für Export-Tokens: `POST/GET/DELETE /api/v1/export-tokens`

**UC-06 – Feiertags-Import:**
- Quelle 1: Nager.Date API (`https://date.nager.at/api/v3/PublicHolidays/{year}/DE`), gefiltert nach `state_code`
- Quelle 2: NAK-Festtage berechnet (Palmsonntag, Ostersonntag, Pfingstsonntag, Entschlafenen-GD) via Gauß-Algorithmus
- Celery-Beat-Task `auto_import_feiertage`: 1. des Monats 03:00 Uhr (Europe/Berlin)
- Stabiler UID-Schlüssel: `feiertag-DE-{district_id}-{datum}-{name-slug}`
- Manueller Import über UI

## Capabilities

### New Capabilities

- `event-distribution`: Logik zur virtuellen Verteilung von Bezirks-Events in Gemeindeansichten über `applicability`
- `ical-export`: Öffentliche ICS-Feed-Endpoints mit Token-basiertem Zugang (PUBLIC/INTERNAL) und stabilen UIDs
- `holiday-import`: Automatischer und manueller Feiertags-Import aus Nager.Date + NAK-Festtags-Berechnung

### Modified Capabilities

<!-- keine bestehenden Specs vorhanden -->

## Impact

- **Backend:** Neue Endpoints für Export-Tokens und ICS-Feed, neuer Celery-Task `auto_import_feiertage`, Holiday-Service mit Gauß-Algorithmus
- **Datenbank:** Neue Tabelle `export_token`, `applicability` JSONB auf `events`, Alembic-Migration
- **Externe Abhängigkeit:** `httpx` (oder `aiohttp`) für Nager.Date API-Requests, `icalendar` für ICS-Generierung
- **Sicherheit:** Export-Token-Endpoint ist öffentlich erreichbar — Token-Validierung via HMAC-Vergleich; keine User-Daten ohne Token
