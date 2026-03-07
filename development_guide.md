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

## Phase 3+: Feiertags-Import (✅ implementiert)

### Überblick

Feiertage werden als Events mit `category="Feiertag"` im System gespeichert und in der Dienstmatrix als Spalten-Marker angezeigt.

### Datenbank-Migrationen

- **0006** — `calendar_integrations.default_category VARCHAR(255) NULL`: Kategorie für importierte Events pro Integration.
- **0007** — `districts.state_code VARCHAR(2) NULL`: Bundesland-Kürzel für automatischen Feiertags-Import.

Migration ausführen: `cd services/backend && uv run alembic upgrade head`

### Backend-Komponenten

**`app/application/feiertage_service.py`**
- `import_feiertage(district_id, year, state_code, session)`: Gesetzliche Feiertage via Nager.Date API. Filtert nationale + bundeslandspezifische Feiertage.
- `import_kirchliche_festtage(district_id, year, session)`: Berechnet Palmsonntag (Ostern−7), Ostersonntag (Ostern), Pfingstsonntag (Ostern+49) via Gauss-Algorithmus — kein HTTP-Call.
- `_easter_sunday(year)`: Anonymer Gregorianischer Algorithmus.
- Idempotenz: `external_uid = feiertag-DE-{district_id}-{datum}-{slug}`, Content-Hash-Vergleich.

**`app/application/tasks.py`** — Celery-Beat-Task `auto_import_feiertage`:
- Läuft jeden 1. des Monats um 03:00 Uhr (crontab).
- Ab September: importiert laufendes + folgendes Jahr.
- Gesetzliche Feiertage nur für Bezirke mit `state_code`; kirchliche Festtage für alle.

**`app/adapters/api/routers/districts.py`**
- `POST /api/v1/districts/{id}/feiertage` — Manueller Import (year, state_code optional).
- `GET /api/v1/districts/{id}/feiertage/states` — Liste aller Bundesland-Codes.

### Matrix-Integration

Die Spalten der Matrix (`sorted_dates`) werden aus zwei Quellen aufgebaut:
1. Congregation `service_times`-Zeitplan.
2. Datumsangaben aller `category="Feiertag"`-Events des Bezirks.

Kirchliche Festtage erscheinen dadurch immer als Spalten, auch wenn sie nicht im regulären Zeitplan liegen. Im Spaltenkopf werden Feiertags-Namen grau/kursiv angezeigt.

### CalendarIntegration: default_category

Über das Feld `default_category` an einer CalendarIntegration kann eine Kategorie für alle beim Sync neu erstellten Events gesetzt werden (z.B. `"Feiertag"` für einen öffentlichen Feiertags-ICS-Feed).

### Celery Worker starten (lokal)

```bash
cd services/backend
uv run celery -A app.celery_app.celery worker -B --loglevel=info
```

`-B` aktiviert den Beat-Scheduler im selben Prozess (nur für Entwicklung; in Produktion separat).

## Phase 4: Auth & Sicherheit

JWT-basierte Authentifizierung.

Verschlüsselung von API-Keys in der Datenbank (Service-Layer Decorator).

Wichtige Hinweise für den Agenten:

Nutze Pydantic v2 für alle Schemas.

Nutze Tailwind-Klassen direkt (kein Custom CSS wenn möglich).

Achte auf mobile Ansicht (Responsive Design) für die Matrix-Ansicht (horizontales Scrolling erlauben).

Schreibe Unit-Tests für die Sync-Logik (Mocking der externen APIs).