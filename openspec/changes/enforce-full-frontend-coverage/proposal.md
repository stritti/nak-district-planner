## Why

Die bisherige Frontend-Coverage misst nur eine explizite Allowlist einzelner Dateien. Neue oder bestehende Production-Dateien koennen dadurch 0 % Coverage besitzen, ohne die angezeigte Gesamtcoverage zu beeinflussen.

## What Changes

- Coverage umfasst den gesamten relevanten Frontend-Production-Code unter `src`.
- Tests, Typdeklarationen und der reine Bootstrap-Entry-Point werden explizit ausgeschlossen.
- Die globale Mindestschwelle bleibt fuer Statements, Branches, Functions und Lines bei 80 Prozent.
- Neue Production-Dateien koennen Coverage nicht mehr durch fehlende Konfiguration umgehen.

## Capabilities

### Modified Capabilities
- `quality-gates`: Frontend-Coverage bezieht sich auf den vollstaendigen Production-Code-Scope.

## Impact

- Frontend CI kann bisher ungetestete Bereiche sichtbar machen und blockieren.
- Testluecken muessen durch gezielte Tests statt durch Include-Listen geschlossen werden.