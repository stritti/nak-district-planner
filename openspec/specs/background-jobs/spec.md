# background-jobs Specification

## Purpose
Regeln fuer Celery-Hintergrundjobs, damit Worker-Tasks Datenbankverbindungen nur in dem Event-Loop nutzen, der sie geoeffnet hat.

## Requirements

### Requirement: Worker-Tasks dürfen keine DB-Verbindungen über Event-Loops hinweg wiederverwenden

Jeder Celery-Task, der asynchronen Datenbankcode per `asyncio.run` ausführt, SHALL alle gepoolten Datenbankverbindungen freigeben, bevor seine Event-Loop endet, sodass nachfolgende Tasks im selben Worker-Prozess ausschließlich Verbindungen ihrer eigenen Loop verwenden. Der RLS-`begin`-Listener (SYSTEM_WORKER-GUCs) MUST dabei für jede Transaktion des Workers aktiv bleiben, und die API MUST weiterhin eine gepoolte Engine verwenden.

#### Scenario: Aufeinanderfolgende Tasks im selben Worker-Prozess

- **WHEN** ein Worker-Prozess drei Task-Bodies nacheinander jeweils mit eigenem `asyncio.run` ausführt und dabei die gemeinsame Session-Factory nutzt
- **THEN** gelingt jeder Lauf ohne "Event loop is closed" oder "attached to a different loop"

#### Scenario: RLS-Kontext bleibt erhalten

- **WHEN** ein Task-Body innerhalb von `_run_as_system_worker` eine Abfrage ausführt
- **THEN** liefert `current_setting('app.is_system_worker', true)` den Wert `true`
