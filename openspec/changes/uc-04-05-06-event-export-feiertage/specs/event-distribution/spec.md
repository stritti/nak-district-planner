## ADDED Requirements

### Requirement: Bezirks-Events mit applicability-Feld
Das System SHALL ein `applicability`-Feld (JSONB) auf `events` unterstützen. Mögliche Werte: `["all"]` (für alle Gemeinden des Bezirks) oder eine Liste von Gemeinde-UUIDs.

#### Scenario: Event mit applicability="all" erscheint in allen Gemeindeansichten
- **WHEN** ein Bezirks-Event `applicability=["all"]` und `status=PUBLISHED` hat
- **THEN** erscheint das Event in der Terminsicht jeder Gemeinde des Bezirks

#### Scenario: Event mit spezifischen Gemeinden
- **WHEN** ein Bezirks-Event `applicability=["congregation_id_1", "congregation_id_2"]` hat
- **THEN** erscheint das Event nur in den Ansichten dieser zwei Gemeinden

#### Scenario: Event mit applicability=[] oder ohne Feld
- **WHEN** ein Bezirks-Event kein `applicability`-Feld hat oder eine leere Liste
- **THEN** erscheint das Event nicht in Gemeindeansichten

### Requirement: Nur PUBLISHED-Events werden delegiert
Das System SHALL sicherstellen, dass nur Events mit `status=PUBLISHED` über `applicability` in Gemeindeansichten erscheinen.

#### Scenario: DRAFT-Event wird nicht delegiert
- **WHEN** ein Bezirks-Event `applicability=["all"]` und `status=DRAFT` hat
- **THEN** erscheint das Event nicht in Gemeindeansichten

### Requirement: Kein physisches Kopieren
Das System SHALL Events NICHT physisch duplizieren. Die Gemeindeansicht kombiniert eigene Events mit gefilterten Bezirks-Events zur Abfragezeit.

#### Scenario: Änderung am Bezirks-Event
- **WHEN** ein Bezirks-Event mit `applicability` geändert wird
- **THEN** sehen alle betroffenen Gemeinden sofort den geänderten Stand (kein manuelles Re-Sync nötig)

### Requirement: Pflege der Verteilung über PATCH /api/v1/events/{id}
Das System SHALL `applicability` über `PATCH /api/v1/events/{id}` (Rolle PLANNER im Bezirk) pflegbar machen und dabei die Verteilungsregeln im Domänenmodell (`PlanningSlot.distribute_to`) durchsetzen.

#### Scenario: Gültige Gemeindeauswahl
- **WHEN** ein Planer für ein Bezirks-Event Gemeinde-IDs des eigenen Bezirks übermittelt
- **THEN** speichert das System die IDs kanonisch, ohne Duplikate und in Eingabereihenfolge

#### Scenario: Fremde oder ungültige Gemeinde
- **WHEN** eine ID keiner Gemeinde des Bezirks entspricht oder keine UUID ist
- **THEN** antwortet das System mit 400 und lässt die bestehende Verteilung unverändert

#### Scenario: "all" kombiniert mit einzelnen Gemeinden
- **WHEN** `applicability` sowohl `"all"` als auch einzelne Gemeinde-IDs enthält
- **THEN** antwortet das System mit 400, da die Auswahl mehrdeutig ist

#### Scenario: Gemeinde-Event wird nicht verteilt
- **WHEN** ein Event einer Gemeinde zugeordnet ist oder wird
- **THEN** lehnt das System eine nicht-leere Verteilung ab bzw. entfernt eine bestehende Verteilung
