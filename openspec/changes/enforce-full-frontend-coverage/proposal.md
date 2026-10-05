## Why

Die bisherige Frontend-Coverage misst nur eine explizite Allowlist einzelner Dateien. Neue oder bestehende Production-Dateien koennen dadurch 0 % Coverage besitzen, ohne die angezeigte Coverage zu beeinflussen.

## What Changes

- Coverage umfasst den gesamten relevanten Frontend-Production-Code unter `src`.
- Tests, Test-Support und Typdeklarationen werden explizit ausgeschlossen.
- Ausfuehrbare Startup-Logik wird aus `main.ts` in ein separat getestetes Modul verschoben, sodass `main.ts` nur Bootstrap-Wiring enthaelt.
- Die Mindestschwelle bleibt pro Production-Datei fuer Statements, Branches, Functions und Lines bei 80 Prozent.
- Neue Production-Dateien koennen Coverage weder durch fehlende Include-Eintraege noch durch Aggregation mit gut getesteten Dateien umgehen.

## Capabilities

### Modified Capabilities
- `quality-gates`: Frontend-Coverage bezieht sich auf den vollstaendigen Production-Code-Scope und erzwingt 80 Prozent pro gemessener Datei.

## Impact

- Frontend CI kann bisher ungetestete Bereiche sichtbar machen und blockieren.
- Testluecken muessen durch gezielte Tests statt durch Include-Listen oder abgesenkte Schwellen geschlossen werden.
