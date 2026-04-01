## ADDED Requirements

### Requirement: Kirchliche Festtage via Gauß-Algorithmus
Das System SHALL Palmsonntag, Ostersonntag, Pfingstsonntag und Entschlafenen-Gottesdienste (erster Sonntag im März, Juli, November) für jedes angefragte Jahr berechnen, ohne externe APIs zu nutzen.

#### Scenario: Ostersonntag 2026
- **WHEN** die Holiday-Service-Funktion für Jahr 2026 aufgerufen wird
- **THEN** wird Ostersonntag korrekt als 5. April 2026 berechnet

#### Scenario: Kirchliche Festtage für alle Bezirke
- **WHEN** der Feiertags-Import für einen Bezirk ohne `state_code` läuft
- **THEN** werden die kirchlichen Festtage trotzdem importiert

### Requirement: Gesetzliche Feiertage via Nager.Date API
Das System SHALL gesetzliche Feiertage über `https://date.nager.at/api/v3/PublicHolidays/{year}/DE` abrufen und nach dem `state_code` des Bezirks filtern. Bundesweite Feiertage gelten für alle Bezirke mit gesetztem `state_code`.

#### Scenario: Import für Bezirk mit state_code=BY
- **WHEN** der Import für einen Bezirk mit `state_code=BY` und Jahr 2026 ausgeführt wird
- **THEN** werden bundesweite Feiertage und Bayern-spezifische Feiertage importiert; Feiertage anderer Bundesländer werden übersprungen

#### Scenario: Import für Bezirk ohne state_code
- **WHEN** der Import für einen Bezirk ohne `state_code` ausgeführt wird
- **THEN** werden keine gesetzlichen Feiertage importiert (nur kirchliche Festtage)

### Requirement: Idempotenter Import mit stabilen UIDs
Das System SHALL importierte Feiertags-Events mit der stabilen UID `feiertag-DE-{district_id}-{datum}-{name-slug}` versehen. Wiederholter Import DARF KEINE Duplikate erzeugen.

#### Scenario: Wiederholter Import desselben Jahres
- **WHEN** der Import für dasselbe Jahr zweimal ausgeführt wird
- **THEN** werden beim zweiten Lauf keine neuen Events angelegt; der Zähler für "unverändert" steigt

#### Scenario: Import-Ergebnis enthält Zähler
- **WHEN** ein Import abgeschlossen wird
- **THEN** enthält die Antwort die Anzahl `created`, `updated` und `unchanged` Events

### Requirement: Automatischer Celery-Beat-Task
Das System SHALL den Task `auto_import_feiertage` jeden 1. des Monats um 03:00 Uhr (Europe/Berlin) ausführen. Ab September wird zusätzlich das Folgejahr importiert.

#### Scenario: Ausführung im August
- **WHEN** der Task am 1. August ausgeführt wird
- **THEN** wird nur das laufende Jahr importiert

#### Scenario: Ausführung im September
- **WHEN** der Task am 1. September ausgeführt wird
- **THEN** werden das laufende Jahr und das Folgejahr importiert

### Requirement: Manueller Import über API
Das System SHALL den Endpoint `POST /api/v1/districts/{id}/import-holidays` mit den Parametern `year` und optionalem `state_code` bereitstellen.

#### Scenario: Manueller Import mit Jahr
- **WHEN** `POST /api/v1/districts/{id}/import-holidays` mit `{ "year": 2026 }` aufgerufen wird
- **THEN** werden Feiertage für 2026 importiert und das Ergebnis (created/updated/unchanged) zurückgegeben
