## Why

Der NAK Bezirksplaner muss Termine aus bestehenden Gemeindekalendern (Google Calendar, Microsoft 365, CalDAV, ICS-Feeds) einlesen können. Ohne diese Anbindung müssen alle Termine manuell doppelt gepflegt werden — der zentrale Mehrwert des Systems (aggregierte Bezirksübersicht) entfällt.

## What Changes

- Neues Datenbankmodell `CalendarIntegration` mit Feldern `type`, `credentials` (verschlüsselt), `sync_interval`, `capabilities`, `default_category`
- OAuth 2.0-Handshake-Flow für Google und Microsoft (Callback-Endpoint)
- Strategy-Pattern im Backend: gemeinsames `CalendarConnector`-ABC, Implementierungen für GOOGLE, MICROSOFT, CALDAV, ICS
- Verschlüsselung der Credentials (OAuth-Tokens, Passwörter) vor dem Speichern in der DB — Decorator-Pattern am Service-Layer
- REST-Endpunkte: `POST /calendar-integrations`, `GET /calendar-integrations`, `DELETE /calendar-integrations/{id}`, `POST /calendar-integrations/{id}/auth/callback`
- Vue-Frontend: Formular zum Anlegen/Verwalten von Kalender-Integrationen pro Gemeinde

## Capabilities

### New Capabilities

- `calendar-connector`: Abstrakte Schnittstelle und konkrete Provider-Implementierungen (Google, Microsoft, CalDAV, ICS) über das Strategy-Pattern
- `credential-encryption`: Verschlüsselung und Entschlüsselung von OAuth-Tokens und Passwörtern vor dem Persistieren

### Modified Capabilities

<!-- keine bestehenden Specs vorhanden -->

## Impact

- **Backend:** Neues Domain-Modell `CalendarIntegration`, neue Port-Schnittstelle `CalendarConnector` (ABC), neue Adapter-Implementierungen in `adapters/calendar/`
- **Datenbank:** Neue Tabelle `calendar_integration`, Alembic-Migration
- **Abhängigkeiten:** `google-auth-oauthlib`, `msal` (Microsoft), `icalendar`, `cryptography` (Fernet für Credential-Verschlüsselung)
- **Sicherheit:** Credentials dürfen nie im Klartext in der DB liegen; Verschlüsselungsschlüssel kommt aus Umgebungsvariable (`ENCRYPTION_KEY`)
