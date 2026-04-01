## ADDED Requirements

### Requirement: Öffentlicher ICS-Export-Endpoint
Das System SHALL den Endpoint `GET /api/v1/export/{token}/calendar.ics` ohne Authentifizierungsheader bereitstellen. Der Token steuert Filterlogik und Anonymisierung.

#### Scenario: Valider PUBLIC-Token liefert anonymisierten Feed
- **WHEN** `GET /api/v1/export/{token}/calendar.ics` mit einem PUBLIC-Token aufgerufen wird
- **THEN** gibt der Endpoint eine ICS-Datei zurück, die nur Events mit `visibility=PUBLIC` und `status=PUBLISHED` enthält; ServiceAssignment-Namen erscheinen als "Dienstleiter"

#### Scenario: Valider INTERNAL-Token liefert vollständigen Feed
- **WHEN** `GET /api/v1/export/{token}/calendar.ics` mit einem INTERNAL-Token aufgerufen wird
- **THEN** gibt der Endpoint eine ICS-Datei zurück, die Events mit `visibility=INTERNAL` und volle `leader_name`-Werte enthält

#### Scenario: Unbekannter oder ungültiger Token
- **WHEN** `GET /api/v1/export/{token}/calendar.ics` mit einem unbekannten Token aufgerufen wird
- **THEN** gibt der Endpoint HTTP 404 zurück (kein Hinweis, ob Token existiert)

### Requirement: Stabile UIDs im ICS-Feed
Das System SHALL für jeden exportierten Event eine stabile UID generieren, die sich über die Zeit nicht ändert.

#### Scenario: UID bei wiederholtem Export
- **WHEN** derselbe Event zu zwei verschiedenen Zeitpunkten exportiert wird
- **THEN** hat der VEVENT-Block in beiden ICS-Antworten dieselbe `UID`-Zeile

#### Scenario: UID-Format für reguläre Events
- **WHEN** ein reguläres Event exportiert wird
- **THEN** hat die UID das Format `{district_id}-{event_id}@nak-planner`

### Requirement: Export-Token-CRUD
Das System SHALL REST-Endpunkte für die Verwaltung von Export-Tokens bereitstellen: `POST /api/v1/export-tokens`, `GET /api/v1/export-tokens`, `DELETE /api/v1/export-tokens/{id}`.

#### Scenario: Token erstellen
- **WHEN** `POST /api/v1/export-tokens` mit `{ "type": "PUBLIC", "congregation_id": "..." }` aufgerufen wird
- **THEN** wird ein neuer Token mit zufälligem 32-Byte-Hex-Wert erstellt und der Token-Wert genau einmal in der Antwort zurückgegeben (danach nicht mehr lesbar)

#### Scenario: Token löschen
- **WHEN** `DELETE /api/v1/export-tokens/{id}` aufgerufen wird
- **THEN** wird der Token ungültig gemacht und HTTP 204 zurückgegeben; weitere Anfragen mit diesem Token erhalten HTTP 404
