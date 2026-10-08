## Warum

Der Backend-Testlauf meldete 12–16 `RuntimeWarning: coroutine ... was never awaited`
(Issue #435). Ursachen waren nicht awaitbar modellierte Mocks (`asyncio.run`-Patches in
Celery-Task-Tests, `AsyncMock`-Session mit asynchronem `add`) sowie ein Connection-Pool, der
asyncpg-Verbindungen über Event-Loop-Grenzen hinweg wiederverwendet. Letzteres ist auch ein
echter Produktionsfehler: Im Celery-Worker läuft jede Task in einem eigenen `asyncio.run()`-Loop,
die zweite DB-Task im selben Worker-Prozess scheiterte mit „attached to a different loop".

## Was sich ändert

- `_run_as_system_worker` gibt den Engine-Pool vor dem Schließen des Task-Loops frei
  (`await engine.dispose()`).
- Tests: `CoroutineClosingMock`/`close_coroutine` für `asyncio.run`-Patches, korrekt modellierte
  `AsyncSession`-Mocks, ungepoolte Engine (`NullPool`) für die App-Session-Factory im Testlauf.
- `pytest`-`filterwarnings` macht nicht awaitete Coroutinen zum Fehler – auch wenn sie erst bei
  der Garbage Collection als `PytestUnraisableExceptionWarning` gemeldet werden.

## Capabilities

### New Capabilities

- `test-quality`: Async-Test-Hygiene als CI-Gate für das Backend

## Impact

- `services/backend/pyproject.toml`, `services/backend/tests/`, `app/application/tasks.py`
