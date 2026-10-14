## Why

Celery-Tasks überbrücken mit `asyncio.run(...)` pro Ausführung in asynchronen Code, nutzen aber die modulweite, gepoolte Async-Engine aus `app/adapters/db/session.py`. asyncpg-Verbindungen sind an die Event-Loop gebunden, die sie geöffnet hat. Ab der zweiten Task-Ausführung im selben Worker-Prozess scheitert die Wiederverwendung gepoolter Verbindungen mit "Event loop is closed" bzw. "attached to a different loop" — etwa jeder zweite Task schlägt fehl, Beat-Jobs fallen still aus (#464).

## What Changes

- `_run_as_system_worker` (der gemeinsame Einstieg aller Celery-Task-Bodies) gibt den Verbindungspool der Engine per `await engine.dispose()` frei, bevor die Loop von `asyncio.run` endet. Der nächste Task öffnet frische Verbindungen auf seiner eigenen Loop.
- Engine-Objekt, `begin`-Listener für die RLS-GUCs (`app.is_system_worker` usw.) und OpenTelemetry-Instrumentierung bleiben unverändert; die API nutzt weiterhin den gepoolten Engine-Pool.
- Integrationstest (echtes PostgreSQL): drei aufeinanderfolgende `asyncio.run`-Task-Bodies im selben Prozess mit gepoolter Engine.

## Impact

- Code: `services/backend/app/application/tasks.py`
- Tests: `services/backend/tests/integration/test_worker_event_loop_engine.py`
- Keine Migration, keine Konfigurationsänderung.
