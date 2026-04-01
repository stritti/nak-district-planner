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
