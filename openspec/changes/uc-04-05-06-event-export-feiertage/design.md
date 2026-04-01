## Context

UC-04, UC-05 und UC-06 bauen alle auf dem vorhandenen `Event`-Modell auf. Sie teilen sich eine Migration (neues Feld `applicability` auf `events`, neue Tabelle `export_token`) und sind inhaltlich eng verknüpft (Feiertage aus UC-06 erscheinen als Spalten in UC-03 und als Events im ICS-Export aus UC-05).

## Goals / Non-Goals

**Goals:**
- UC-04: `applicability` JSONB-Feld auf `events`; geänderte GET-Events-Endpoints für Gemeindeansicht
- UC-05: `ExportToken`-Modell + `POST/GET/DELETE /api/v1/export-tokens`; öffentlicher `GET /api/v1/export/{token}/calendar.ics`-Endpoint
- UC-06: `HolidayService` mit Nager.Date-Integration und Gauß-Algorithmus; Celery-Beat-Task `auto_import_feiertage`; manueller Import-Endpoint
- Stabile ICS-UIDs für alle exportierten Events

**Non-Goals:**
- Write-Back von Feiertagen in externe Kalender
- Push-Benachrichtigungen bei neuen Feiertagen
- UC-05: Passwortschutz für ICS-Feeds (Token genügt)

## Decisions

### UC-04: Virtuelles Einblenden statt Kopieren
**Entscheidung:** `applicability: ["all"] | ["congregation_id_1", ...]` auf dem Event. Der GET-Endpoint der Gemeindeansicht filtert: eigene Events UNION Bezirks-Events mit `status=PUBLISHED` und passendem `applicability`-Eintrag.

Alternativen: Physisches Kopieren als Kind-Events (Duplikate, Sync-Problem), separate Verteilungs-Tabelle (unnötige Komplexität).

### UC-05: Token-Typ statt zwei Endpoints
**Entscheidung:** Ein Endpoint `/export/{token}/calendar.ics`; der Token-Typ (`PUBLIC`/`INTERNAL`) steuert die Filterlogik. Token selbst ist ein kryptographisch zufälliger String (32 Byte hex), gespeichert als HMAC-Hash in der DB.

**Begründung:** Zwei verschiedene Endpoints würden den Token-Besitz-Check verdoppeln.

### UC-05: Stabile UIDs
**Entscheidung:** UID-Format: `{district_id}-{event_id}@nak-planner`. UUID-basiert, ändert sich nie.

Feiertags-UIDs: `feiertag-DE-{district_id}-{datum}-{name-slug}` (deterministisch aus Inhalt berechnet).

### UC-06: Gauss-Algorithmus in reinem Python
**Entscheidung:** Kein externe Bibliothek für Ostertermin-Berechnung. Anonymer Gregorianischer Algorithmus als reine Funktion in `application/services/holiday_service.py`.

**Begründung:** Keine externe Abhängigkeit, kein Netzwerkaufruf, testbar und stabil.

### UC-06: Nager.Date ohne Cache
**Entscheidung:** Feiertage werden direkt in die `events`-Tabelle importiert (idempotent). Kein separates Caching-Layer.

**Begründung:** Import läuft einmal/Monat; Ergebnis liegt dauerhaft in DB. Redundanter Cache unnötig.

## Risks / Trade-offs

- [Risiko] Nager.Date API nicht erreichbar → Task schlägt fehl → **Mitigation:** Retry, Fehler loggen; kirchliche Festtage (Gauß) funktionieren immer unabhängig
- [Risiko] ICS-Token-URL wird versehentlich öffentlich geteilt → **Mitigation:** Token ist 32-Byte-Random, nicht erratbar; Token löschen/neu erstellen als Rotations-Workflow
- [Trade-off] `applicability="all"` ist ein String-Literal, kein JOIN → performant, aber weniger flexibel als Beziehungstabelle → akzeptiert für MVP

## Migration Plan

1. Alembic-Migration: `applicability` auf `events`, neue Tabelle `export_token`
2. HolidayService + Gauß-Algorithmus implementieren
3. Celery-Beat-Task `auto_import_feiertage` aktivieren
4. ICS-Export-Endpoint implementieren
5. Event-Distribution-Logik in GET-Endpoint integrieren
6. Frontend: Import-UI, Token-Verwaltungs-UI
