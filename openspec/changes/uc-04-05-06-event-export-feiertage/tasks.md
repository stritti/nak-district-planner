## 1. Datenbankschema

- [x] 1.1 `applicability` JSONB auf `events`-Tabelle → im Domain-Modell vorhanden (`Event.applicability: list`)
      ⚠️ Alembic-Migration für `applicability`-Spalte prüfen — Feld existiert in Domain/ORM, aber explizite Migration nicht bestätigt
- [x] 1.2 Tabelle `export_token` → Migration 0004
- [x] 1.3 SQLAlchemy-Modelle aktualisiert (`EventORM`, `ExportTokenORM`)

## 2. UC-06 — Feiertags-Import

- [x] 2.1 `feiertage_service.py` in `application/` mit `import_feiertage()` und `import_kirchliche_festtage()`
- [x] 2.2 Gauß-Algorithmus für Ostertermin implementiert (reines Python, keine Bibliothek)
- [x] 2.3 Kirchliche Festtage: Palmsonntag, Ostersonntag, Pfingstsonntag, Entschlafenen-GD (3×/Jahr, 1. Sonntag im März/Juli/November)
- [x] 2.4 Nager.Date API-Integration implementiert (async `httpx`)
- [x] 2.5 Bundesland-Filterung nach `state_code` implementiert
- [x] 2.6 UID-Schema: `feiertag-DE-{district_id}-{datum}-{name-slug}` stabil implementiert
- [x] 2.7 Idempotenz via `content_hash`-Vergleich implementiert
- [x] 2.8 Celery-Beat-Task `auto_import_feiertage` (1. des Monats 03:00 Europe/Berlin, ab Sep. + Folgejahr) implementiert
- [x] 2.9 Manueller Import-Endpoint `POST /api/v1/districts/{id}/feiertage` mit `FeiertageImportRequest` (year, state_code)
- [ ] 2.10 Unit-Tests für Gauß-Algorithmus mit bekannten Osterdaten (2025–2030)
- [ ] 2.11 Unit-Tests für Idempotenz und Bundesland-Filterung

## 3. UC-04 — Event-Verteilung

- [x] 3.1 `applicability`-Feld in Event-Domain-Modell und Pydantic-Schemas vorhanden
- [ ] 3.2 `GET /api/v1/events`-Endpoint schließt Bezirks-Events mit passendem `applicability`-Eintrag in Gemeindeansicht ein → **nicht implementiert!** Der Events-Endpoint hat keinen applicability-basierten Filter
- [ ] 3.3 Nur `status=PUBLISHED` Bezirks-Events werden über applicability eingeblendet → hängt von 3.2 ab
- [ ] 3.4 Integrations-Test: Bezirks-Event mit `applicability=["all"]` erscheint in Gemeindeansicht

## 4. UC-05 — ICS-Export

- [x] 4.1 `ExportToken`-Domain-Modell mit zufälligem urlsafe-Token (secrets.token_urlsafe(32))
- [x] 4.2 `POST/GET/DELETE /api/v1/export-tokens` implementiert
- [x] 4.3 ICS-Generator mit `icalendar`-Bibliothek, VEVENT-Serialisierung implementiert
- [x] 4.4 Filter-Logik für PUBLIC-Token (nur PUBLIC+PUBLISHED, ServiceAssignment-Namen anonymisiert als "[Name anonymisiert]")
- [x] 4.5 Filter-Logik für INTERNAL-Token (inkl. INTERNAL-Events, volle Namen)
- [x] 4.6 Öffentlicher Endpoint `GET /api/v1/export/{token}/calendar.ics` implementiert
      ⚠️ **Abweichung:** UID-Format ist `{event.id}@nak-bezirksplaner` (nicht `{district_id}-{event_id}@nak-planner` wie im Design)
- [ ] 4.7 Unit-Tests für UID-Stabilität, Token-Validierung, Anonymisierung

## 5. Frontend

- [x] 5.1 UI für manuellen Feiertags-Import in Kalender-Integrationsseite vorhanden (POST /districts/{id}/feiertage)
- [ ] 5.2 `applicability`-Auswahl im Event-Erstellungsformular fehlt (kein Event-Erstellungsformular im Frontend vorhanden)
- [x] 5.3 `ExportTokensView.vue` mit Token-CRUD (erstellen, auflisten, löschen)
- [x] 5.4 ICS-Download-Link im Frontend anzeigbar
