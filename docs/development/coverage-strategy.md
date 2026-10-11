# Test- und Coverage-Strategie

Maßgeblich sind die tatsächlichen [CI-Jobs](https://github.com/stritti/nak-district-planner/blob/main/.github/workflows/ci.yml) und die [Vitest-Konfiguration](https://github.com/stritti/nak-district-planner/blob/main/services/frontend/vitest.config.ts), nicht historische Phasenpläne.

## Testebenen

- **Unit-Tests:** Domain, Application, Frontend-Stores, Composables und Komponenten.
- **Integration:** API, PostgreSQL-RLS, Authentifizierung, Kalender-Sync, Migrationen.
- **E2E:** Login, Rechteprüfung, zentrale Planungsabläufe.
- **Negativtests:** fremde Mandanten, unzulässige Rollen, falsche Tokens, Fehler-/Timeoutfälle, Idempotenz und Terminrandfälle.

## Aktuelle Mindestanforderungen

| Umfang | Verbindliche Regel |
| --- | --- |
| Backend | Mindestens **80 %** Gesamt-Line-Coverage in der Unit-Suite |
| Backend-kritische Router | Je mindestens **80 % Line Coverage** für `auth.py`, `leader_unavailabilities.py`, `planning_series.py`, `system.py` (fehlende Datei ist Fehler) |
| Frontend | **80 % pro Production-Datei** für Statements, Branches, Functions und Lines (`perFile: true`) |
| Ausnahmen | Nur begründete Testdoubles, reine Typdateien und Bootstrap-Wiring gemäß `vitest.config.ts`; kein großflächiges Ausschließen fachlichen Codes |

Tests müssen zusätzlich relevante Ausnahme- und Sicherheitsfälle prüfen; reine Prozentsätze reichen nicht.

## Lokal prüfen

```bash
cd services/backend
uv run pytest tests/unit/
uv run pytest tests/integration/ tests/performance/
cd ../frontend
bun run test
bun run lint
bun run build
cd ../..
bun run docs:build
```
