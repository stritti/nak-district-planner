## 1. Regressionstest

- [x] 1.1 Integrationstest: drei aufeinanderfolgende `asyncio.run(_run_as_system_worker(...))` mit gepoolter Modul-Engine; schlägt vor dem Fix fehl ("different loop"/"Event loop is closed")

## 2. Fix

- [x] 2.1 `_run_as_system_worker` ruft im `finally` `await engine.dispose()` auf, solange die Task-Loop noch läuft
- [x] 2.2 RLS-GUC-Listener und gepoolte API-Engine unverändert; Test prüft `app.is_system_worker = true` in jedem Lauf

## 3. Verifikation

- [x] 3.1 `ruff check`, Unit- und Integrationstests grün
