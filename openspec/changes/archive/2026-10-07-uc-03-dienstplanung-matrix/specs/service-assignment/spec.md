## ADDED Requirements

### Requirement: ServiceAssignment anlegen
Das System SHALL es erlauben, über `POST /api/v1/service-assignments` eine neue Zuweisung (Event → Dienstleiter) mit Status `ASSIGNED` anzulegen.

#### Scenario: Neue Zuweisung anlegen
- **WHEN** `POST /api/v1/service-assignments` mit `event_id` und `leader_name` aufgerufen wird
- **THEN** wird ein neues `ServiceAssignment` mit `status=ASSIGNED` erstellt und mit HTTP 201 zurückgegeben

#### Scenario: Doppelte Zuweisung für denselben Event
- **WHEN** für einen Event bereits ein `ServiceAssignment` existiert und erneut `POST` aufgerufen wird
- **THEN** gibt der Endpoint HTTP 409 Conflict zurück

### Requirement: ServiceAssignment bearbeiten
Das System SHALL es erlauben, über `PATCH /api/v1/service-assignments/{id}` den Dienstleiter-Namen oder den Status (`OPEN`, `ASSIGNED`, `CONFIRMED`) zu ändern.

#### Scenario: Status auf CONFIRMED setzen
- **WHEN** `PATCH /api/v1/service-assignments/{id}` mit `{ "status": "CONFIRMED" }` aufgerufen wird
- **THEN** wird der Status aktualisiert und HTTP 200 zurückgegeben

#### Scenario: Dienstleiter ändern
- **WHEN** `PATCH /api/v1/service-assignments/{id}` mit `{ "leader_name": "Neuer Name" }` aufgerufen wird
- **THEN** wird `leader_name` aktualisiert und HTTP 200 zurückgegeben

### Requirement: ServiceAssignment löschen
Das System SHALL es erlauben, über `DELETE /api/v1/service-assignments/{id}` eine Zuweisung zu entfernen.

#### Scenario: Zuweisung löschen
- **WHEN** `DELETE /api/v1/service-assignments/{id}` aufgerufen wird
- **THEN** wird die Zuweisung gelöscht und HTTP 204 zurückgegeben
