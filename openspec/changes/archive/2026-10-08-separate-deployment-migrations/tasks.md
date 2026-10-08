## 1. Deployment

- [x] 1.1 One-Shot-Migration-Service ohne Tool-Profil betreiben.
- [x] 1.2 Backend und Worker auf erfolgreichen Migration-Service warten lassen.
- [x] 1.3 Owner-Credentials nur im Migration-Service laden. Korrektur nach Review: `MIGRATION_DATABASE_URL` war isoliert, `POSTGRES_PASSWORD` erreichte Backend/Worker aber weiter ueber `.env`. Das Passwort liegt jetzt in `.env.db` (Vorlage `.env.db.example`), das nur `db`, `db-test` und `migrate` laden.
- [x] 1.4 Alembic-Upgrade aus FastAPI-Lifespan entfernen.
- [x] 1.5 API-Startup prueft Alembic-Head read-only gegen `alembic_version` und scheitert bei Abweichung frueh.
- [x] 1.6 Produktions- und Entwicklungsablauf fuer Migrationen im Runbook dokumentieren.
- [x] 1.7 Celery-Worker prueft den Alembic-Head beim Start (`worker_init`) und beendet sich bei Abweichung.
- [x] 1.8 `alembic/env.py` serialisiert parallele Migrationslaeufe ueber `pg_advisory_lock`.
- [x] 1.9 `docs/production-runbook.md` an `docs/deployment-migrations.md` angleichen; Rollback auf aelteres Image (fail closed) dokumentieren.

## 2. Tests

- [x] 2.1 Test absichern, dass Runtime-Code kein `command.upgrade` ausfuehrt.
- [x] 2.2 Test absichern, dass Backend/Worker auf `service_completed_successfully` warten.
- [x] 2.3 Test absichern, dass `.env.docker.migrate` nicht in Runtime-Services geladen wird.
- [x] 2.4 Schema-Guard fuer aktuellen Stand, stale Revision, fehlenden Head und nicht lesbare Versionstabelle testen.
- [x] 2.5 Statischer Compose-Test: jeder Service ausser `db`, `db-test`, `migrate`, `valkey` wartet auf `migrate` und erhaelt kein `POSTGRES_PASSWORD`.
- [x] 2.6 Worker-Schema-Guard (Unit) sowie Schema-Guard als `nak_app` und Advisory-Lock gegen echte PostgreSQL-DB (Integration) testen.

## 3. Verifikation

- [x] 3.1 Backend Unit Tests und Coverage erfolgreich.
- [x] 3.2 Compose-Konfiguration erfolgreich.
- [x] 3.3 Migration Graph & FK Names erfolgreich.
- [x] 3.4 Encrypted Backup & Isolated Restore erfolgreich.

## Follow-ups (post-merge review)

- [x] Treat driver-level connection errors (OSError) as schema-version errors so workers exit
- [x] `make migrate` uses the Compose `migrate` service; host commands document `MIGRATION_DATABASE_URL`
