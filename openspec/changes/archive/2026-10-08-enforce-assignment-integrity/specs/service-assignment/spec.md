## ADDED Requirements

### Requirement: Eine Zuweisung pro Planungseintrag
Das System SHALL höchstens eine Dienstzuweisung pro Planungseintrag speichern und dies durch einen eindeutigen Datenbankindex auf `service_assignments.planning_slot_id` erzwingen.

#### Scenario: Zweite Zuweisung für denselben Planungseintrag
- **WHEN** für einen Planungseintrag bereits eine Zuweisung existiert und eine weitere angelegt wird
- **THEN** antwortet die API mit 409 und es bleibt genau eine Zuweisung bestehen

#### Scenario: Bereinigung bestehender Dubletten
- **WHEN** die Migration auf Daten mit mehreren Zuweisungen pro Planungseintrag läuft
- **THEN** bleibt pro Planungseintrag die Zuweisung mit dem höchsten Status (CONFIRMED vor ASSIGNED vor OPEN), bei Gleichstand die mit verknüpftem Amtsträger und danach die zuletzt geänderte erhalten

#### Scenario: Bereinigte Dubletten bleiben nachvollziehbar
- **WHEN** die Migration Dubletten entfernt
- **THEN** liegen die entfernten Zeilen in einer nur für den Datenbank-Owner lesbaren Archivtabelle, die Anwendungsrolle kann sie nicht lesen und der Downgrade stellt sie wieder her

### Requirement: Serialisierte Zuweisung pro Amtsträger
Das System SHALL Konfliktprüfung und Speichern einer Zuweisung für denselben Amtsträger über einen transaktionsgebundenen Advisory-Lock serialisieren.

#### Scenario: Parallele Zuweisung desselben Amtsträgers
- **WHEN** zwei Requests denselben Amtsträger gleichzeitig zwei zeitgleichen Planungseinträgen zuweisen
- **THEN** wartet der zweite Request auf den Commit des ersten und wird mit 409 `no_double_booking` abgelehnt

### Requirement: Fail-closed Konfliktprüfung
Das System SHALL Planungseinträge ohne EventInstance mit ihrer geplanten Zeit (UTC) und der konfigurierten Standarddauer prüfen, statt sie zu überspringen, und die bestehenden Zuweisungen des Amtsträgers mit einer einzigen, zeitlich begrenzten Abfrage laden.

#### Scenario: Ziel ohne EventInstance
- **WHEN** ein Amtsträger einem Planungseintrag ohne EventInstance zugewiesen wird, der zeitgleich zu einer bestehenden Zuweisung liegt
- **THEN** meldet die Prüfung einen BLOCK-Konflikt `no_double_booking`

#### Scenario: Mehrtägiger Dienst überschneidet sich
- **WHEN** ein Amtsträger einer bestehenden EventInstance zugewiesen ist, die länger als 24 Stunden dauert und Tage vor dem Ziel begonnen hat, aber noch läuft
- **THEN** meldet die Prüfung einen BLOCK-Konflikt `no_double_booking`, weil EventInstances über ihre tatsächliche Überschneidung und nicht über ein festes Rückblickfenster gesucht werden

### Requirement: Referenzen müssen zum Bezirk gehören
Das System SHALL `congregation_id`- und `leader_id`-Werte aus Request-Bodies ablehnen, die unbekannt sind oder zu einem anderen Bezirk gehören, und dafür mit 422 und einer für beide Fälle identischen Meldung antworten.

#### Scenario: Fremde Gemeinde beim Anlegen eines Amtsträgers
- **WHEN** ein Planer einen Amtsträger mit der `congregation_id` einer Gemeinde eines anderen Bezirks anlegt
- **THEN** antwortet die API mit 422 und es wird nichts gespeichert

#### Scenario: Fremder Amtsträger bei der Dienstzuweisung
- **WHEN** eine Zuweisung mit der `leader_id` eines Amtsträgers aus einem anderen Bezirk angelegt wird
- **THEN** antwortet die API mit 422 und es wird keine Zuweisung gespeichert
