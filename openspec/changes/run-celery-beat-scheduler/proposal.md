## Why

`app/celery_app.py` definiert acht Beat-Jobs (Kalender-Sync, Feiertage, Cleanup, Draft-Generierung, Planungsserien, Versionspruefung, Erinnerungen, Lueckenscan), Docker Compose startet aber nur `celery worker`. Ohne Beat-Prozess laeuft keiner dieser Jobs (Issue #455, Release-Blocker). Zusaetzlich veroeffentlicht `build.yml` jeden `main`-Push als `latest`, obwohl `release.yml` `latest` fuer stabile Releases reserviert.

Beim Verifizieren zeigte sich: Worker und Beat laufen mit der Runtime-Rolle ohne DDL-Rechte, Celery legt seine Broker-/Result-Tabellen aber erst bei Bedarf an. Auf einer frischen Datenbank brachen beide mit `permission denied for schema public` ab.

## What Changes

- Neuer Compose-Service `beat` (genau eine Instanz, Runtime-Credentials, wartet auf `migrate`, Schema-Guard beim Start, Schedule-Datei auf dem Named Volume `beat_schedule`).
- Alembic-Revision legt die Celery-Broker- und Result-Tabellen als Owner an und vergibt DML-Rechte an die Runtime-Rolle.
- `build.yml` veroeffentlicht nur Branch- und SHA-Tags; `latest` bleibt `release.yml` (nur stabile Releases) vorbehalten.
- Langlaufende Services erhalten `restart: unless-stopped`; `db-test` liegt im Profil `test`.
- Backend-Image installiert das Projekt selbst (echte `app_version`) und setzt `UV_NO_SYNC=1`, damit `uv run` beim Containerstart keine Dev-Abhaengigkeiten nachinstalliert.

## Capabilities

### New Capabilities
- `production-deployment`: Scheduler-Service, Neustartrichtlinien und Image-Tag-Politik.

## Impact

- `docker-compose.yml`, `docker-compose.override.yml`, `services/backend/Dockerfile`, `.github/workflows/build.yml`
- `services/backend/app/celery_app.py`, neue Alembic-Revision `20261007_celery_tables`
- `docs/production-runbook.md`
