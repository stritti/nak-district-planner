## ADDED Requirements

### Requirement: Benutzerprofil lesen
Das System SHALL einen Endpoint `GET /api/v1/users/me` bereitstellen, der das eigene Profil und die eigenen Rollen zurückgibt.

#### Scenario: Eigenes Profil abrufen
- **WHEN** `GET /api/v1/users/me` mit gültigem JWT aufgerufen wird
- **THEN** gibt der Endpoint `id`, `email`, `display_name`, `district_id` und die eigenen Rollen zurück

### Requirement: Benutzer im Bezirk auflisten
Das System SHALL `district_admin` und `system_admin` erlauben, alle Benutzer eines Bezirks über `GET /api/v1/districts/{id}/users` aufzulisten.

#### Scenario: district_admin listet Benutzer seines Bezirks
- **WHEN** `GET /api/v1/districts/{id}/users` mit `district_admin`-Berechtigung aufgerufen wird
- **THEN** gibt der Endpoint alle Benutzer des Bezirks zurück

#### Scenario: Benutzer ohne Berechtigung
- **WHEN** ein `viewer` `GET /api/v1/districts/{id}/users` aufruft
- **THEN** gibt das Backend HTTP 403 zurück

### Requirement: Rollen zuweisen und entziehen
Das System SHALL `district_admin` und `system_admin` erlauben, Rollen über `PATCH /api/v1/users/{id}/roles` zuzuweisen oder zu entziehen.

#### Scenario: Rolle zuweisen
- **WHEN** `PATCH /api/v1/users/{id}/roles` mit `{ "action": "add", "role": "planner" }` aufgerufen wird
- **THEN** wird die Rolle angelegt, der Redis-Cache invalidiert und HTTP 200 zurückgegeben

#### Scenario: Bereits vorhandene Rolle
- **WHEN** dieselbe Rolle erneut zugewiesen wird
- **THEN** gibt das Backend HTTP 409 zurück

#### Scenario: Rolle entziehen
- **WHEN** `PATCH /api/v1/users/{id}/roles` mit `{ "action": "remove", "role": "planner" }` aufgerufen wird
- **THEN** wird die Rolle gelöscht, der Redis-Cache invalidiert und HTTP 200 zurückgegeben

### Requirement: Benutzer deaktivieren
Das System SHALL `district_admin` und `system_admin` erlauben, Benutzer über `PATCH /api/v1/users/{id}` mit `{ "is_active": false }` zu deaktivieren.

#### Scenario: Benutzer deaktivieren
- **WHEN** `PATCH /api/v1/users/{id}` mit `{ "is_active": false }` aufgerufen wird
- **THEN** wird `is_active=false` gesetzt; bestehende `ServiceAssignment`-Einträge bleiben erhalten; Redis-Cache wird invalidiert

#### Scenario: Login nach Deaktivierung
- **WHEN** ein deaktivierter Benutzer einen API-Request sendet
- **THEN** gibt das Backend HTTP 403 zurück

### Requirement: Audit-Log für sicherheitsrelevante Aktionen
Das System SHALL sicherheitsrelevante Aktionen (Rollenvergabe/-entzug, Benutzer deaktiviert, Login) in einer `AuditLog`-Tabelle festhalten.

#### Scenario: Rollenvergabe wird geloggt
- **WHEN** einem Benutzer eine Rolle zugewiesen wird
- **THEN** wird ein `AuditLog`-Eintrag mit `action=ROLE_ASSIGNED`, `user_id`, `resource_type`, `resource_id` und Timestamp angelegt

#### Scenario: Benutzer-Deaktivierung wird geloggt
- **WHEN** ein Benutzer deaktiviert wird
- **THEN** wird ein `AuditLog`-Eintrag mit `action=USER_DEACTIVATED` angelegt
