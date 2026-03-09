## ADDED Requirements

### Requirement: Matrix-API-Endpoint
Das System SHALL einen Endpoint `GET /api/v1/districts/{id}/matrix` mit optionalen Query-Parametern `from` und `to` (ISO-Datum) bereitstellen, der die Dienstplanungs-Matrix für den angegebenen Zeitraum zurückgibt.

#### Scenario: Matrix für Bezirk im Standardzeitraum
- **WHEN** `GET /api/v1/districts/{id}/matrix` ohne Zeitraum aufgerufen wird
- **THEN** gibt der Endpoint die Matrix für die nächsten 4 Wochen zurück

#### Scenario: Matrix für expliziten Zeitraum
- **WHEN** `GET /api/v1/districts/{id}/matrix?from=2026-04-01&to=2026-04-30` aufgerufen wird
- **THEN** gibt der Endpoint die Matrix für April 2026 zurück

### Requirement: Spalten aus service_times und Feiertagen
Das System SHALL die Spalten der Matrix aus der Union aller `service_times`-Termine der Gemeinden und aller `category=Feiertag`-Events des Bezirks im gewählten Zeitraum berechnen.

#### Scenario: Feiertag ohne regulären Gottesdienst erzeugt Spalte
- **WHEN** ein Feiertag in den Zeitraum fällt, an dem keine Gemeinde laut `service_times` Gottesdienst hat
- **THEN** erscheint der Feiertag als Spalte in der Matrix

#### Scenario: Feiertags-Name im Spaltenkopf
- **WHEN** eine Spalte einem Feiertag entspricht
- **THEN** enthält das Spalten-Objekt den Feiertags-Namen im Feld `holiday_name`

### Requirement: Zell-Status
Das System SHALL den Status jeder Matrixzelle korrekt berechnen.

#### Scenario: Gottesdienst ohne Zuweisung → GAP
- **WHEN** ein Event mit `category=Gottesdienst` für eine Gemeinde am Spaltendatum existiert und kein aktives `ServiceAssignment` vorhanden ist
- **THEN** hat die Zelle den Status `GAP`

#### Scenario: Gottesdienst mit Zuweisung → ASSIGNED
- **WHEN** ein Event mit `category=Gottesdienst` für eine Gemeinde am Spaltendatum existiert und ein `ServiceAssignment` mit `status=ASSIGNED` oder `CONFIRMED` vorhanden ist
- **THEN** hat die Zelle den Status `ASSIGNED` und enthält `leader_name`

#### Scenario: Kein geplanter Gottesdienst → EMPTY
- **WHEN** keine Gottesdienst-Event für eine Gemeinde am Spaltendatum existiert
- **THEN** hat die Zelle den Status `EMPTY`

### Requirement: Frontend-Matrixansicht
Das System SHALL eine Vue-Komponente `MatrixView.vue` bereitstellen, die die Matrix darstellt.

#### Scenario: GAP-Zellen sind rot und klickbar
- **WHEN** der Benutzer die Matrix betrachtet und eine Zelle mit Status `GAP` sieht
- **THEN** ist die Zelle rot eingefärbt und öffnet beim Klick das `AssignLeaderModal`

#### Scenario: ASSIGNED-Zellen sind grün
- **WHEN** der Benutzer die Matrix betrachtet und eine Zelle mit Status `ASSIGNED` sieht
- **THEN** ist die Zelle grün eingefärbt und zeigt den `leader_name`
