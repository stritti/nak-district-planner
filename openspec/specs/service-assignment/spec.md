# service-assignment Specification

## Purpose

Keeps service assignments consistent under concurrency and across tenants: one assignment per planning slot, serialized per-leader conflict checks that fail closed, and references that must belong to the district.

## Requirements

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

### Requirement: Minister retirement and visibility lifecycle
Ministers/service leaders SHALL support independent active and frontend-list visibility states and an optional inclusive service end date. Deactivation and hide-from-list operations SHALL retain database rows, IDs and historical references. Default person selection and visible management lists SHALL exclude hidden or deactivated ministers, while authorised historical/administrative views MAY explicitly include them.

#### Scenario: Additional constraints for Minister retirement and visibility lifecycle
- **GIVEN** this requirement is applicable
- **WHEN** the system processes the relevant operation
- **THEN** Restoring visibility and reactivation SHALL require authorised, audited operations.

#### Scenario: Deactivate minister
- **WHEN** an administrator deactivates a minister
- **THEN** that minister is excluded from normal new-assignment choices but existing and historical service assignments retain the same referenced identity

#### Scenario: Hide deactivated minister
- **WHEN** an administrator removes a deactivated minister from visible lists
- **THEN** no database hard delete occurs, historical references remain valid, and the minister can be retrieved with an authorised include-inactive query

### Requirement: Minister service end date affects planning
A minister with an end-of-service date SHALL be eligible for new service assignments only through that local calendar date, inclusive, and only when active and not hidden. Server-side validation SHALL enforce the date and status for event-list, matrix and bulk assignment paths. Earlier assignments SHALL not be silently deleted when the end date changes; future ineligible ones SHALL be flagged for review.

#### Scenario: Additional constraints for Minister service end date affects planning
- **GIVEN** this requirement is applicable
- **WHEN** the system processes the relevant operation
- **THEN** Free-text assignment paths SHALL NOT implicitly bypass an ineligible known leader: an exact matching retired name requires an explicit unlinked guest choice, and MUST NOT silently re-link the retired person.

#### Scenario: Before or on end date
- **WHEN** an active visible minister with an end date of 2026-12-31 is assigned a service on 2026-12-31
- **THEN** date-based eligibility permits the assignment subject to all other conflict rules

#### Scenario: Beyond end date
- **WHEN** a planner attempts to assign that minister to a service dated 2027-01-01
- **THEN** the server rejects the assignment and the planning UI identifies the unavailability

#### Scenario: End date moved earlier
- **WHEN** a minister's end date is changed to precede already planned services
- **THEN** those assignments remain historically referentially intact and are flagged as requiring planner review

#### Scenario: Retired minister matched by name-only entry
- **WHEN** a free-text service-leader entry matches an ineligible existing leader in the same district
- **THEN** the server refuses to treat that name as an eligible linked leader without the explicit independent guest workflow

#### Scenario: Stale client tries inactive minister
- **WHEN** a stale client submits a new service assignment for an inactive or hidden minister
- **THEN** the server rejects it regardless of whether the frontend still shows that person
