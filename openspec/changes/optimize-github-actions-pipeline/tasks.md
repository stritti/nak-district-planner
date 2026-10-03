## 1. Dependency- und Tool-Caches

- [x] 1.1 Alembic-Workflow auf `setup-uv`-Cache umstellen
- [x] 1.2 Backend-CI und Alembic mit `uv sync --locked` gegen veraltete Lockfiles absichern
- [x] 1.3 Bun-Cache-Schlüssel um Bun-Version und Restore-Key ergänzen
- [x] 1.4 Frontend-Installationen auf `--prefer-offline` umstellen
- [x] 1.5 Playwright-Chromium cachen und nur bei Cache-Miss installieren

## 2. Security-Workflow

- [x] 2.1 Redundanten `bun install` vor `bun audit` entfernen
- [x] 2.2 CodeQL-Autobuild für Python und JavaScript/TypeScript entfernen
- [x] 2.3 Concurrency mit `cancel-in-progress` ergänzen
- [x] 2.4 `bun audit` mit Bun 1.3+ und `--audit-level=moderate` ausführen

## 3. MegaLinter

- [x] 3.1 Pull Requests auf Diff-Validierung umstellen
- [x] 3.2 Pushes auf `main`/`develop` weiterhin vollständig validieren
- [x] 3.3 Diff-Ermittlung gegen den tatsächlichen PR-Base-Branch ausführen

## 4. Qualitätssicherung

- [x] 4.1 Workflow-Syntax über GitHub Actions auf dem finalen Review-Fix-Head verifizieren
- [x] 4.2 Backend-Unit-Tests inklusive Coverage >= 80 % verifizieren
- [x] 4.3 Backend-Integration-/Performance-Tests ohne Skips verifizieren
- [x] 4.4 Frontend-Unit- und E2E-Tests verifizieren
- [x] 4.5 Alembic-Checks inklusive Roundtrip und Drift-Check verifizieren
- [x] 4.6 Security- und MegaLinter-Läufe verifizieren
- [x] 4.7 Cache-Hits in einem Folgelauf dokumentieren
- [x] 4.8 Alle offenen Review-Threads beantworten und auflösen

## 5. MegaLinter-Laufzeit

- [x] 5.1 Laufzeitprofil des bisherigen MegaLinter-Jobs aus Actions-Logs ermitteln
- [x] 5.2 All-in-one-Image durch offizielle `python`-Flavor ersetzen
- [x] 5.3 Frontend-ESLint in den bereits installierten Bun-CI-Job verschieben
- [ ] 5.4 Frontend-ESLint auf dem PR-Head erfolgreich verifizieren
- [ ] 5.5 MegaLinter-Flavor mit allen konfigurierten Lintern erfolgreich verifizieren
- [ ] 5.6 Image-Pull- und Gesamtlaufzeit gegen den bisherigen Lauf vergleichen
