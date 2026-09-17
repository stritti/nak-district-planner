# Playwright-E2E-Tests

Die E2E-Tests verwenden den Vite-Preview-Server und mocken die API-Aufrufe im
Browser. Dadurch bleiben die kritischen Planungsflows reproduzierbar, ohne eine
laufende Datenbank oder einen OIDC-Provider zu benötigen.

## Lokal ausführen

```bash
bun install
bun run build
bunx playwright install chromium
bunx playwright test tests/e2e/matrix-assignment.spec.ts --project=chromium
```

## Abgedeckte Flows

- Dienstplan-Lücke öffnen und Leader zuweisen
- BLOCK-Konflikt aus einem strukturierten HTTP-409 anzeigen und Zuweisung verhindern

Noch ausstehend sind der WARN-Flow mit expliziter Bestätigung und der Abwesenheits-
Flow. Beide benötigen zusätzliche API-Mocks für den jeweiligen Konflikttyp.
