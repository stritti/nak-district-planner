## Why

RC-1 besitzt bereits einen dedizierten Migration-Service mit Owner-Credentials, fuehrt `alembic upgrade head` aber zusaetzlich beim Start jedes API-Prozesses aus. Dadurch benoetigt der Runtime-Start implizit DDL-Faehigkeiten und mehrere Replikate koennen gleichzeitig Migrationen anstossen.

## What Changes

- Schema-Migrationen werden ausschliesslich durch einen One-Shot-Deployment-Service ausgefuehrt.
- Backend und Worker warten auf den erfolgreichen Abschluss dieses Services.
- Runtime-Services erhalten weiterhin nur die eingeschraenkten Application-DB-Credentials.
- Der FastAPI-Lifespan fuehrt keine Alembic-Migration aus.
- Tests sichern die Deployment-Grenze gegen Regressionen ab.

## Capabilities

### Modified Capabilities
- `production-deployment`: Migrationen sind ein expliziter Deployment-Schritt vor Runtime-Prozessen.
- `database-security`: Owner-Credentials bleiben auf den Migration-Service beschraenkt.

## Impact

- `docker compose up` startet Migrationen einmalig vor Backend und Worker.
- Ein Migrationsfehler verhindert den Runtime-Start statt erst in einem API-Prozess aufzutreten.
- Horizontale API-Skalierung loest keine parallelen Schema-Aenderungen mehr aus.
