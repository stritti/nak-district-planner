## ADDED Requirements

### Requirement: Credentials werden verschlüsselt gespeichert
Das System SHALL OAuth-Tokens, Passwörter und alle sonstigen Credentials verschlüsselt in der Datenbank speichern. Der Klartext DARF NICHT in der DB persistiert werden.

#### Scenario: Speichern einer Integration mit OAuth-Token
- **WHEN** eine `CalendarIntegration` mit Credentials über die API gespeichert wird
- **THEN** sind die Credentials in der DB-Spalte Fernet-verschlüsselt

#### Scenario: Lesen einer Integration liefert Klartext im Service
- **WHEN** die Anwendung eine Integration aus der DB liest und den Connector aufruft
- **THEN** werden die Credentials vor der Übergabe an den Connector transparent entschlüsselt

### Requirement: Verschlüsselungsschlüssel aus Umgebungsvariable
Das System SHALL den Verschlüsselungsschlüssel ausschließlich aus der Umgebungsvariable `ENCRYPTION_KEY` laden.

#### Scenario: `ENCRYPTION_KEY` nicht gesetzt
- **WHEN** die Anwendung startet und `ENCRYPTION_KEY` fehlt
- **THEN** bricht der Start mit einer klaren Fehlermeldung ab

#### Scenario: `ENCRYPTION_KEY` gesetzt
- **WHEN** die Anwendung startet und `ENCRYPTION_KEY` gesetzt ist
- **THEN** startet die Anwendung ohne Fehler

### Requirement: Credentials nicht in API-Antworten
Das System SHALL sicherstellen, dass Credentials (weder Klartext noch verschlüsselt) in keiner API-Antwort enthalten sind.

#### Scenario: GET auf CalendarIntegration
- **WHEN** `GET /api/v1/calendar-integrations/{id}` aufgerufen wird
- **THEN** enthält die Antwort das Feld `credentials` nicht
