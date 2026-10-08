## 1. Scheduler

- [x] 1.1 Compose-Service `beat` mit `.env` + `.env.docker`, `deploy.replicas: 1`, `depends_on: migrate (service_completed_successfully)`.
- [x] 1.2 Schedule-Datei auf Named Volume `beat_schedule` (`/app/beat`), Verzeichnis im Image fuer `appuser` angelegt.
- [x] 1.3 Schema-Guard auch bei `beat_init`.
- [x] 1.4 Alembic-Revision fuer `kombu_*`/`celery_*`-Tabellen inkl. Grants an die Runtime-Rolle.

## 2. Compose und Image

- [x] 2.1 `restart: unless-stopped` fuer backend, worker, beat, frontend, db, valkey.
- [x] 2.2 `db-test` unter `profiles: [test]`.
- [x] 2.3 Dockerfile: Projekt installieren, `UV_NO_SYNC=1`.

## 3. Release-Tags

- [x] 3.1 `build.yml` ohne `latest`; nur Branch- und `sha-`-Tags.

## 4. Tests und Doku

- [x] 4.1 Statische Tests fuer Beat-Service, Restart-Policies, `db-test`-Profil, Dockerfile und Tag-Politik.
- [x] 4.2 Unit-Test fuer Schema-Guard bei `beat_init`; Integrationstest fuer Broker-Tabellen als Runtime-Rolle.
- [x] 4.3 `docs/production-runbook.md` aktualisiert.
