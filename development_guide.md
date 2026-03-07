# Entwicklungs-Leitfaden & Roadmap

## Phase 1: Docker & Backend Core (MVP)

Erstelle docker-compose.yml mit Postgres und Redis.

Initialisiere FastAPI mit SQLAlchemy Modellen für District, Congregation und Event.

Implementiere POST /events und GET /events mit Filtern für District/Congregation.

## Phase 2: Kalender-Schnittstellen

Implementiere CalendarConnector Interface.

Erstelle iCalConnector (Read-only) als ersten Adapter.

Erstelle Celery-Task für den Sync-Loop.

## Phase 3: Frontend (Vue 3)

Setup Vue 3 mit Tailwind und Pinia.

Erstelle Dashboard mit einer Listenansicht der Termine.

Implementiere die Matrix-Planungsansicht (Grid-Layout).

Phase 4: Auth & Sicherheit

JWT-basierte Authentifizierung.

Verschlüsselung von API-Keys in der Datenbank (Service-Layer Decorator).

Wichtige Hinweise für den Agenten:

Nutze Pydantic v2 für alle Schemas.

Nutze Tailwind-Klassen direkt (kein Custom CSS wenn möglich).

Achte auf mobile Ansicht (Responsive Design) für die Matrix-Ansicht (horizontales Scrolling erlauben).

Schreibe Unit-Tests für die Sync-Logik (Mocking der externen APIs).