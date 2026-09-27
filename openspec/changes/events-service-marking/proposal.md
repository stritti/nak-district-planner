## Why

Die Anwendung bietet zwei Ansichten auf dieselben Grunddaten: die Event-Übersicht
(`EventListView.vue`) und die Dienstplanungs-Matrix (`MatrixView.vue`, UC-03). Die Matrix
ist eine spezielle Planungsdarstellung für Gottesdienste und die Einteilung der
Dienstleiter — die Gottesdienste sind aber trotzdem Events und erscheinen bereits in
der Event-Übersicht. Dort sind sie jedoch nicht als Gottesdienst erkennbar und lassen
sich nicht gezielt filtern. Nutzer müssen die Kategorie-Spalte manuell lesen und haben
keine Möglichkeit, gezielt nur Gottesdienste (oder nur Nicht-Gottesdienste) anzusehen.

## What Changes

- Events mit `category=Gottesdienst` werden in der Event-Übersicht (Liste, Woche, Monat)
  visuell als Gottesdienst gekennzeichnet (dediziertes Badge, bestehende blaue Pill-Farbe
  wird beibehalten).
- Die Event-Übersicht erhält einen neuen Filter "Typ" mit den Ausprägungen
  `Alle / Gottesdienste / Andere Ereignisse`, der serverseitig filtert.
- Die Events-API (`GET /api/v1/events`) erhält einen neuen Query-Parameter `is_service`
  (boolean). `is_service=true` liefert nur Events mit `category=Gottesdienst`,
  `is_service=false` liefert alle Events mit einer anderen (oder leeren) Kategorie.
- Das `EventResponse`-Schema erhält ein berechnetes Feld `is_service`, damit das Frontend
  die Kennzeichnung nicht aus dem Kategorie-String ableiten muss.

## Capabilities

### New Capabilities

- `events-service-marking`: Kennzeichnung und Filterbarkeit von Gottesdiensten in der
  Event-Übersicht (Liste, Woche, Monat) inkl. API-Parameter `is_service`.

### Modified Capabilities

- (keine bestehenden Specs betroffen; `service-matrix` (UC-03) bleibt unverändert —
  die Matrix-Logik nutzt weiterhin `category=Gottesdienst` direkt.)

## Impact

- **Backend:** `GET /api/v1/events` um Query-Parameter `is_service` erweitert;
  `EventResponse` um berechnetes Feld `is_service` erweitert. Keine DB-Migration nötig
  (Kategorie bleibt der Wahrheitsgehalt, `Gottesdienst` ist die im System bestehende
  Konventionskategorie, vgl. `planning_series_service.py`, `draft_service_generation.py`,
  Matrix-Lücke-Logik `category=Gottesdienst AND ServiceAssignment=NULL`).
- **Frontend:** `EventListView.vue` (Badge in Liste/Karten, Filter-Dropdown "Typ"),
  `api/events.ts` (Param + Response-Feld), week/month-Ansichten nutzen die
  Kennzeichnung für das Pill-Styling.
- **Abhängigkeiten:** Keine neuen externen Abhängigkeiten.
