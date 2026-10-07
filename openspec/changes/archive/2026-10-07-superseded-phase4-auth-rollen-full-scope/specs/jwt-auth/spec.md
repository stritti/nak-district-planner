## ADDED Requirements

### Requirement: JWT-Validierung via Keycloak JWKS
Das System SHALL jeden eingehenden API-Request auf einen gültigen Bearer-JWT prüfen. Der Token MUSS via Keycloak JWKS-Endpoint (`{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs`) validiert werden.

#### Scenario: Valider JWT im Authorization-Header
- **WHEN** ein Request mit `Authorization: Bearer <valid_jwt>` eingeht
- **THEN** wird die Anfrage verarbeitet und der authentifizierte Benutzer der Route bekannt gemacht

#### Scenario: Fehlender Authorization-Header
- **WHEN** ein Request auf `/api/v1/` ohne Authorization-Header eingeht
- **THEN** gibt das Backend HTTP 401 zurück

#### Scenario: Abgelaufener JWT
- **WHEN** ein Request mit einem abgelaufenen JWT eingeht
- **THEN** gibt das Backend HTTP 401 mit der Meldung "Token expired" zurück

#### Scenario: JWT von unbekanntem Issuer
- **WHEN** ein Request mit einem JWT eingeht, der nicht von Keycloak ausgestellt wurde
- **THEN** gibt das Backend HTTP 401 zurück

### Requirement: Automatische User-Anlage beim ersten Login
Das System SHALL beim ersten validen JWT-Aufruf eines neuen Keycloak-Benutzers automatisch einen `User`-Datensatz in der lokalen DB anlegen (Keycloak-Sub als Primäridentifikator).

#### Scenario: Erster Login eines neuen Benutzers
- **WHEN** ein JWT mit unbekannter `sub`-Claim eingeht und der Token gültig ist
- **THEN** wird ein neuer `User`-Datensatz mit `keycloak_sub`, `email` und `display_name` angelegt

#### Scenario: Wiederholter Login
- **WHEN** ein JWT mit bekannter `sub`-Claim eingeht
- **THEN** wird der bestehende `User`-Datensatz zurückgegeben, kein neuer Datensatz angelegt

### Requirement: /api/health bleibt ungesichert
Das System SHALL den Endpunkt `GET /api/health` ohne Authentifizierung zugänglich halten.

#### Scenario: Health-Check ohne Token
- **WHEN** `GET /api/health` ohne Authorization-Header aufgerufen wird
- **THEN** gibt der Endpoint HTTP 200 zurück

### Requirement: Breaking Change — API-Key-Authentifizierung entfällt
Das System SHALL den `X-API-Key`-Header-Guard für alle `/api/v1/`-Endpunkte entfernen.

#### Scenario: Request mit X-API-Key-Header
- **WHEN** ein Request mit `X-API-Key`-Header (aber ohne Bearer-JWT) eingeht
- **THEN** gibt das Backend HTTP 401 zurück (der API-Key wird ignoriert)
