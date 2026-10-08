## 1. Ursachen beheben

- [x] 1.1 `asyncio.run`-Patches schließen übergebene (auch verschachtelte) Coroutinen
- [x] 1.2 `AsyncSession`-Mock im Audit-Writer-Test: `__aenter__` liefert die Session, `add` ist synchron
- [x] 1.3 Testlauf bindet `AsyncSessionLocal` an eine `NullPool`-Engine (kein Loop-übergreifender Pool)
- [x] 1.4 Produktion: `_run_as_system_worker` disposed den Engine-Pool pro Celery-Task-Loop

## 2. Gate

- [x] 2.1 `filterwarnings` in `pyproject.toml`: `coroutine .* was never awaited` als Fehler, inkl. Unraisable-Variante
- [x] 2.2 Gate durch temporäres Wiedereinführen eines Lecks nachgewiesen
- [x] 2.3 Unit-Suite dreimal stabil grün, Integrations- und Performance-Tests grün
