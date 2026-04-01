## 1. Domain-Modell & Datenbank

- [x] 1.1 `CalendarConnector` ABC in `domain/ports/calendar_connector.py` definieren (`list_events`, `get_event`, `write_event`, `authenticate`)
- [x] 1.2 `ExternalEvent`-Dataclass in `domain/models/external_event.py` definieren → implementiert als `RawCalendarEvent` in `domain/models/raw_calendar_event.py`
- [x] 1.3 SQLAlchemy-Modell `CalendarIntegration` in `adapters/db/models.py` ergänzen
- [x] 1.4 Alembic-Migration für `calendar_integration`-Tabelle erstellen und testen → Migration 0002

## 2. Credential-Verschlüsselung

- [x] 2.1 `EncryptionService` implementieren → `application/crypto.py` (Fernet, Key via SHA-256 aus `settings.secret_key`)
      ⚠️ **Abweichung:** Env-Var heißt `SECRET_KEY` (nicht `ENCRYPTION_KEY` wie im Design). Key-Ableitung via SHA-256, nicht direktes Fernet-Key-Format.
- [x] 2.2 Encryption im Service-Layer → Ver-/Entschlüsselung wird direkt im Router und in `sync_service.py` aufgerufen. Kein Decorator-Pattern, sondern explizite Aufrufe.
- [ ] 2.3 Unit-Tests für `crypto.py` / Encryption-Logik schreiben
- [ ] 2.4 `.env.example` mit Hinweis auf `SECRET_KEY` (für Credential-Encryption) ergänzen

## 3. ICalConnector

- [x] 3.1 `ICalConnector` in `adapters/calendar/ical_connector.py` implementieren
- [ ] 3.2 Dedizierte `CalendarConnectorError`-Exception-Klasse definieren und in ICalConnector nutzen (aktuell werden generische Exceptions verwendet)
- [x] 3.3 Unit-Tests für `ICalConnector` → `tests/unit/test_ical_connector.py` (21 Tests, inkl. valide/ungültige ICS, Zeit-Filterung)

## 4. Repository & Service

- [x] 4.1 `CalendarIntegrationRepository` (Port + SQLAlchemy-Implementierung) → `SqlCalendarIntegrationRepository`
- [ ] 4.2 Dedizierter `CalendarIntegrationService` in `application/services/` fehlt — Encryption-Logik liegt aktuell direkt im Router (`adapters/api/routers/calendar_integrations.py`)

## 5. API-Endpunkte

- [x] 5.1 Router `adapters/api/routers/calendar_integrations.py`: `POST /`, `GET /`, `DELETE /{id}`, `PATCH /{id}`
      ⚠️ **Abweichung:** GET-Endpoint hat `district_id`-Query-Filter (nicht congregation-spezifisch wie im Design)
- [x] 5.2 Pydantic-Schemas für Request/Response (Credentials aus Response ausgeblendet)
- [x] 5.3 Router in `main.py` eingebunden
- [ ] 5.4 Integrations-Tests für alle Endpunkte

## 6. Frontend

- [x] 6.1 `CalendarIntegrationsView.vue` mit Formular (Typ-Auswahl, URL-Feld, Sync-Interval, Default Category)
- [ ] 6.2 Pinia-Store `useCalendarIntegrationsStore` fehlt — View nutzt direkt API-Client (`api/calendarIntegrations.ts`)
- [x] 6.3 Route `/admin/calendars` in Vue Router eingebunden
