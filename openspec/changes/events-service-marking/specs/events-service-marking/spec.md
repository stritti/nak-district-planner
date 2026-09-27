## ADDED Requirements

### Requirement: Gottesdienst-Kennzeichnung in der Event-API

Das System SHALL jedem Event in der `EventResponse` der Events-API (`GET /api/v1/events`,
`PATCH /api/v1/events/{id}`) ein berechnetes Feld `is_service` vom Typ Boolean
bereitstellen, das genau dann `true` ist, wenn die Kategorie des Events `Gottesdienst`
ist.

#### Scenario: Gottesdienst-Event ist gekennzeichnet

- **WHEN** ein Event mit `category="Gottesdienst"` abgerufen wird
- **THEN** hat das Feld `is_service` den Wert `true`

#### Scenario: Anderes Event ist nicht gekennzeichnet

- **WHEN** ein Event mit einer anderen Kategorie (z. B. `Feiertag`, `Andacht`) oder
  ohne Kategorie abgerufen wird
- **THEN** hat das Feld `is_service` den Wert `false`

### Requirement: Filter nach Gottesdiensten in der Event-API

Das System SHALL die Events-API `GET /api/v1/events` um den optionalen boolean
Query-Parameter `is_service` erweitern.

#### Scenario: Nur Gottesdienste

- **WHEN** `GET /api/v1/events?is_service=true` aufgerufen wird
- **THEN** enthält die Antwort ausschließlich Events mit `is_service=true` und `total`
  bezieht sich auf die gefilterte Menge

#### Scenario: Nur andere Ereignisse

- **WHEN** `GET /api/v1/events?is_service=false` aufgerufen wird
- **THEN** enthält die Antwort ausschließlich Events mit `is_service=false`

#### Scenario: Kein Filter (Rückwärtskompatibilität)

- **WHEN** `GET /api/v1/events` ohne `is_service` aufgerufen wird
- **THEN** ist das Filterverhalten unverändert und umfasst Events beider Ausprägungen

### Requirement: Typ-Filter in der Event-Übersicht

Das System SHALL in der Event-Übersicht (`EventListView.vue`) einen Filter "Typ" mit den
Ausprägungen `Alle`, `Gottesdienste` und `Andere Ereignisse` bereitstellen, der
serverseitig über den Parameter `is_service` filtert und in allen Ansichtsmodi
(Liste, Woche, Monat) wirksam ist.

#### Scenario: Nur Gottesdienste anzeigen

- **WHEN** der Benutzer den Typ-Filter auf `Gottesdienste` setzt
- **THEN** zeigt die Event-Übersicht ausschließlich Events mit `is_service=true`

#### Scenario: Nur andere Ereignisse anzeigen

- **WHEN** der Benutzer den Typ-Filter auf `Andere Ereignisse` setzt
- **THEN** zeigt die Event-Übersicht ausschließlich Events mit `is_service=false`

#### Scenario: Filter zurücksetzen

- **WHEN** der Benutzer den Typ-Filter auf `Alle` setzt
- **THEN** werden wieder alle Events angezeigt

### Requirement: Visuelle Gottesdienst-Kennzeichnung in der Event-Übersicht

Das System SHALL Events mit `is_service=true` in der Event-Übersicht visuell als
"Gottesdienst" kennzeichnen.

#### Scenario: Badge in der Listenansicht

- **WHEN** die Listenansicht (Desktop-Tabelle oder mobile Karte) ein Event mit
  `is_service=true` anzeigt
- **THEN** ist ein "Gottesdienst"-Badge (blau) sichtbar

#### Scenario: Pill-Farbe in Woche/Monat

- **WHEN** die Wochen- oder Monatsansicht ein Event mit `is_service=true` anzeigt
- **THEN** ist die Termin-Pill blau hinterlegt; andere Events sind grau hinterlegt
