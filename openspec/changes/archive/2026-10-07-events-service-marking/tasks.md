## 1. Backend

- [x] 1.1 Konstante `SERVICE_CATEGORY = "Gottesdienst"` im Events-Router definieren
- [x] 1.2 `EventResponse` um berechnetes Feld `is_service` erweitern
- [x] 1.3 Query-Parameter `is_service` in `GET /api/v1/events` ergänzen
  (Filter vor Pagination, konsistent mit bestehenden Status-Filtern)
- [x] 1.4 Unit-Tests: `is_service`-Feld in Response, Filter `true`/`false`/nicht gesetzt

## 2. Frontend — API

- [x] 2.1 `EventResponse` in `api/events.ts` um `is_service` erweitern
- [x] 2.2 `EventListParams` um `is_service` ergänzen und in `listEvents` serialisieren

## 3. Frontend — Event-Übersicht

- [x] 3.1 Filter-Dropdown "Typ" (`Alle / Gottesdienste / Andere Ereignisse`) in der
  Filter-Leiste ergänzen; an `applyFilters` und `fetchCalendar` anbinden
- [x] 3.2 "Gottesdienst"-Badge (blau) in Desktop-Tabelle und mobiler Karte
- [x] 3.3 `eventPillClass` auf `is_service` umstellen (Woche/Monat)
- [x] 3.4 Feiertags-Zusatzladung und Filter-Weitergabe prüfen (Typ-Filter auch beim
  Feiertag-Nachladen berücksichtigen)
