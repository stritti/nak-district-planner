## Warum

Die GitHub-Actions-Pipeline wiederholt mehrere teure Setup-Schritte, obwohl deren Eingaben bereits durch Lockfiles bestimmt sind. Besonders die Alembic-Prüfung installiert Python-Abhängigkeiten ohne Cache, die E2E-Tests laden Chromium bei jedem Lauf erneut und der Frontend-Sicherheitsaudit installiert `node_modules`, obwohl `bun audit` direkt aus `bun.lock` arbeitet. MegaLinter validiert außerdem bei jedem Pull Request den gesamten bereits auf `main` bzw. `develop` geprüften Codebestand.

Ziel ist eine kürzere Feedback-Zeit und weniger Runner-, Netzwerk- und Registry-Arbeit, ohne Testumfang, Coverage-Grenzen oder Security-Gates abzuschwächen.

## Was sich ändert

- `uv`-Caching auch für den Alembic-Workflow aktivieren und CI-Installationen mit `--locked` an einen aktuellen Lockfile-Stand binden.
- Bun-Install-Cache mit versionsgebundenem Schlüssel und Restore-Key wiederverwenden; Installationen bevorzugen den lokalen Cache.
- Playwright-Chromium anhand des Frontend-Lockfiles cachen und nur bei Cache-Miss herunterladen.
- Den redundanten `bun install` vor `bun audit` entfernen und den Audit mit Bun 1.3+ ausführen.
- Den nicht benötigten CodeQL-Autobuild für Python und JavaScript/TypeScript entfernen.
- Veraltete Security-Runs per Concurrency abbrechen.
- MegaLinter auf Pull Requests nur für neue/geänderte Dateien gegen den jeweiligen PR-Base-Branch ausführen; Pushes auf `main` und `develop` validieren weiterhin den gesamten Codebestand.
- Bestehende Docker-BuildKit-GHA-Caches mit identischen `backend`-/`frontend`-Scopes in Build- und Release-Workflow unverändert weiterverwenden.

## Capabilities

### New Capabilities

- `ci-pipeline-performance`: deterministisches Dependency-Caching, Browser-Caching und ereignisabhängige Voll-/Diff-Prüfungen für GitHub Actions

### Modified Capabilities

- Keine fachlichen Produkt-Capabilities werden geändert.

## Impact

- **CI:** weniger Registry-Downloads und redundante Installationen, schnellere Wiederholungs- und Folge-Läufe.
- **Qualität:** Backend-Unit-, Integrations- und Performance-Tests bleiben bestehen; Coverage muss weiterhin mindestens 80 % erreichen.
- **Migrationen:** alle bestehenden Alembic-Prüfungen inklusive Downgrade/Upgrade-Roundtrip bleiben bestehen.
- **Security:** CodeQL, `pip-audit` und `bun audit` bleiben aktiv; nur unnötige Build-/Installationsarbeit entfällt.
- **Linting:** Pull Requests prüfen nur ihren Diff gegen den korrekten Base-Branch; Pushes auf `main` und `develop` bleiben Vollprüfungen.
- **Produktcode:** keine Änderungen.
