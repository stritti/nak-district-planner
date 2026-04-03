## ADDED Requirements

### Requirement: Rollenbasierte Zugriffskontrolle via FastAPI-Dependency
Das System SHALL eine FastAPI-Dependency `require_role(required_role, district_id?, congregation_id?)` bereitstellen, die den authentifizierten Benutzer auf die erforderliche Rolle prüft und bei Verletzung HTTP 403 zurückgibt.

#### Scenario: Benutzer hat die erforderliche Rolle
- **WHEN** eine Route mit `require_role(Role.district_admin)` aufgerufen wird und der JWT-Benutzer `district_admin` in der DB hat
- **THEN** wird die Anfrage verarbeitet und der `User` zurückgegeben

#### Scenario: Benutzer hat nicht die erforderliche Rolle
- **WHEN** eine Route mit `require_role(Role.district_admin)` aufgerufen wird und der JWT-Benutzer nur `viewer` hat
- **THEN** gibt das Backend HTTP 403 zurück

#### Scenario: Deaktivierter Benutzer
- **WHEN** ein JWT eines Benutzers eingeht, dessen `is_active=false` in der DB ist
- **THEN** gibt das Backend HTTP 403 zurück

### Requirement: Rollen aus DB mit Redis-Cache
Das System SHALL Benutzerrollen per DB-Lookup ermitteln und das Ergebnis pro Benutzer in Redis für 60 Sekunden cachen.

#### Scenario: Erste Anfrage nach Rollenänderung
- **WHEN** eine Rollenänderung durchgeführt wird
- **THEN** wird der Redis-Cache-Key `roles:{user_id}` aktiv invalidiert

#### Scenario: Redis nicht verfügbar
- **WHEN** Redis nicht erreichbar ist
- **THEN** fällt das System auf direkten DB-Lookup zurück ohne Fehler für den Endnutzer

### Requirement: Fünf-Rollen-Modell
Das System SHALL die Rollen `system_admin`, `district_admin`, `congregation_admin`, `planner` und `viewer` unterstützen, wie in `docs/roles.md` definiert.

#### Scenario: system_admin hat Zugriff auf alle Bezirke
- **WHEN** ein Benutzer mit `system_admin`-Rolle eine Bezirks-Ressource aufruft
- **THEN** wird die Anfrage unabhängig von `district_id` genehmigt

#### Scenario: district_admin ist auf seinen Bezirk beschränkt
- **WHEN** ein `district_admin` einen Endpoint eines anderen Bezirks aufruft
- **THEN** gibt das Backend HTTP 403 zurück

#### Scenario: congregation_admin ist auf seine Gemeinde beschränkt
- **WHEN** ein `congregation_admin` eine Ressource einer anderen Gemeinde schreiben will
- **THEN** gibt das Backend HTTP 403 zurück
