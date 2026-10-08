# test-quality Specification

## Purpose
Sichert die Aussagekraft der Backend-Tests: keine nicht awaiteten Coroutinen, CI bricht bei Regression ab, und Engine-Pools werden je Event-Loop getrennt.

## Requirements

### Requirement: Backend-Testlauf ohne nicht awaitete Coroutinen

Der Backend-Testlauf SHALL keine `RuntimeWarning: coroutine ... was never awaited` erzeugen. Mocks
für asynchrone Schnittstellen (OIDC, Celery-Bridge `asyncio.run`, Datenbank-Sessions) MUST so
modelliert sein, dass jede erzeugte Coroutine awaitet oder explizit geschlossen wird.

#### Scenario: Celery-Task-Test mit gemocktem asyncio.run
- **WHEN** ein Test `asyncio.run` in einem Task-Modul patcht und die Task aufruft
- **THEN** werden die übergebene Coroutine und die von ihr umschlossene Coroutine geschlossen
- **AND** es entsteht keine RuntimeWarning

#### Scenario: Gemockte AsyncSession
- **WHEN** Produktionscode `session.add()` auf einer gemockten `AsyncSession` aufruft
- **THEN** ist `add` als synchrone Methode modelliert und erzeugt keine Coroutine

### Requirement: CI schlägt bei Regression fehl

Die pytest-Konfiguration SHALL nicht awaitete Coroutinen als Fehler behandeln, auch wenn die
Warnung erst bei der Garbage Collection als unraisable exception gemeldet wird.

#### Scenario: Neu eingeführtes Coroutine-Leck
- **WHEN** ein Test eine Coroutine erzeugt und nie awaitet
- **THEN** schlägt der pytest-Lauf fehl

### Requirement: Engine-Pool pro Event-Loop

Asyncpg-Verbindungen SHALL NOT über Event-Loop-Grenzen wiederverwendet werden. Celery-Tasks, die
je einen eigenen `asyncio.run()`-Loop nutzen, MUST den Engine-Pool vor dem Schließen des Loops
freigeben.

#### Scenario: Zwei DB-Tasks im selben Worker-Prozess
- **WHEN** ein Worker-Prozess nacheinander zwei Tasks mit Datenbankzugriff ausführt
- **THEN** laufen beide erfolgreich, ohne „attached to a different loop"-Fehler
