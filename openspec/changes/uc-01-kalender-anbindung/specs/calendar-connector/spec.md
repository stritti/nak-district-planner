## ADDED Requirements

### Requirement: CalendarConnector-Schnittstelle
Das System SHALL eine abstrakte Schnittstelle `CalendarConnector` (Abstract Base Class) in `domain/ports/calendar_connector.py` bereitstellen, die alle Provider-Implementierungen kontraktuell verpflichten.

#### Scenario: Abstrakte Methoden erzwingen Implementierung
- **WHEN** eine Unterklasse nicht alle abstrakten Methoden implementiert
- **THEN** wirft Python beim Instanziieren einen `TypeError`

### Requirement: ICalConnector-Implementierung
Das System SHALL einen `ICalConnector` in `adapters/calendar/ical_connector.py` bereitstellen, der eine ICS-URL abruft und Events als `ExternalEvent`-Objekte zurückgibt.

#### Scenario: Valide ICS-URL liefert Events
- **WHEN** `list_events(from_dt, to_dt)` mit einer erreichbaren ICS-URL aufgerufen wird
- **THEN** gibt der Connector alle Events im angegebenen Zeitraum als `ExternalEvent`-Liste zurück

#### Scenario: Nicht erreichbare ICS-URL
- **WHEN** die ICS-URL nicht erreichbar ist (Timeout/HTTP-Fehler)
- **THEN** wirft der Connector eine `CalendarConnectorError`-Exception mit aussagekräftiger Fehlermeldung

#### Scenario: Invalides ICS-Format
- **WHEN** die URL erreichbar ist, aber kein valides ICS zurückgibt
- **THEN** wirft der Connector eine `CalendarConnectorError`-Exception

### Requirement: CalendarIntegration-CRUD-API
Das System SHALL REST-Endpunkte für das Anlegen, Lesen und Löschen von `CalendarIntegration`-Datensätzen bereitstellen.

#### Scenario: Integration anlegen
- **WHEN** `POST /api/v1/calendar-integrations` mit gültigen Feldern aufgerufen wird
- **THEN** wird ein neuer `CalendarIntegration`-Datensatz erstellt und mit HTTP 201 zurückgegeben

#### Scenario: Integrations einer Gemeinde auflisten
- **WHEN** `GET /api/v1/congregations/{id}/calendar-integrations` aufgerufen wird
- **THEN** gibt der Endpoint alle Integrationen der Gemeinde zurück; `credentials` ist aus der Antwort ausgeblendet

#### Scenario: Integration löschen
- **WHEN** `DELETE /api/v1/calendar-integrations/{id}` aufgerufen wird
- **THEN** wird die Integration gelöscht und HTTP 204 zurückgegeben
