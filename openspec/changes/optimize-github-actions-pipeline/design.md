## Kontext

Die Pipeline besteht aus getrennten Workflows für Tests/Coverage, Alembic, Docker-Builds, Security, MegaLinter und Releases. Docker-Build und Release verwenden bereits gemeinsame GitHub-Actions-BuildKit-Caches mit den Scopes `backend` und `frontend`. Die größten verbleibenden Wiederholungen liegen bei Dependency-Setups, Playwright und Prüfungen, die keine installierten Abhängigkeiten benötigen.

## Ziele

- Wiederholte Downloads und Dependency-Auflösung vermeiden.
- Pull-Request-Feedback beschleunigen, ohne die Prüfbreite des Hauptbranches zu reduzieren.
- Cache-Misses jederzeit korrekt und deterministisch behandeln.
- Bestehende Test-, Coverage-, Migration- und Security-Gates unverändert beibehalten.

## Nicht-Ziele

- Keine Zusammenlegung unabhängiger Jobs, wenn dadurch Parallelität und damit die Wall-Clock-Zeit schlechter würde.
- Keine Wiederverwendung von `node_modules` als Artefakt zwischen Jobs; Transfer und Plattformkopplung sind voraussichtlich teurer bzw. fragiler als Bun mit warmem Paketcache.
- Keine Wiederverwendung von Build-Artefakten zwischen Pull-Request- und Release-Workflows, da Commit-Provenienz und Build-Kontext eindeutig bleiben sollen.
- Keine Reduktion der Backend-Coverage-Grenze von 80 %.

## Entscheidungen

### 1. Lockfile-strikte Installationen

`uv sync` wird in CI mit `--frozen` ausgeführt. Bun verwendet weiterhin `--frozen-lockfile` und zusätzlich `--prefer-offline`. Damit bleiben Installationen deterministisch; vorhandene Cache-Inhalte werden bevorzugt, fehlende Pakete werden normal aus der Registry geladen.

### 2. Cache-Schlüssel enthalten relevante Tool-/Dependency-Versionen

Der Bun-Cache enthält `BUN_VERSION` und Hashes der relevanten Lock-/Package-Dateien. Ein Restore-Key erlaubt die Wiederverwendung bereits vorhandener Pakete nach kleineren Dependency-Änderungen, ohne einen exakten Cache-Hit vorzutäuschen.

Der Playwright-Browsercache wird mit Betriebssystem und Hash des Frontend-Lockfiles adressiert. Ändert sich die Playwright-Version, ändert sich der Lockfile-Hash und Chromium wird neu installiert.

### 3. Cache-Miss bleibt ein vollwertiger Pfad

Caches sind reine Beschleuniger. Bei einem Bun-Cache-Miss läuft `bun install` vollständig. Bei einem Playwright-Cache-Miss wird Chromium installiert. Die Pipeline hängt nicht von bereits vorhandenen Cache-Daten ab.

### 4. Security ohne redundante Builds

Python und JavaScript/TypeScript werden von CodeQL ohne überwachten Build extrahiert; der separate Autobuild-Schritt entfällt. `bun audit` liest die Dependency-Liste aus `bun.lock`, daher entfällt die vorherige `node_modules`-Installation ausschließlich in diesem Audit-Job.

### 5. MegaLinter ereignisabhängig

Pull Requests validieren nur neue/geänderte Dateien. Pushes auf `main` und `develop` validieren weiterhin den gesamten Codebestand. Dadurch bleibt der Branch-Baseline-Gate vollständig, während Pull Requests nicht immer wieder unveränderte Dateien linten.

### 6. Parallelität vor Artefakt-Sharing

Frontend-Unit- und E2E-Tests bleiben parallel. Ein vorgeschalteter Build-Job mit anschließendem Artefakt-Download würde den E2E-Start serialisieren und kann die Gesamtzeit erhöhen. Build-Artefakte werden deshalb nicht künstlich zwischen diesen Jobs geteilt. Vorhandene Diagnose-Artefakte und die bereits workflowübergreifend nutzbaren BuildKit-Caches bleiben bestehen.

## Risiken und Gegenmaßnahmen

- **Veralteter Browsercache:** Lockfile-Hash invalidiert den Cache bei Playwright-Updates.
- **Teilweise Bun-Caches:** `--prefer-offline` fällt für fehlende Pakete automatisch auf die Registry zurück.
- **Lint-Fehler in unveränderten Dateien:** Vollprüfung auf jedem Push nach `main`/`develop` verhindert eine dauerhaft ungeprüfte Baseline.
- **Security-Regressions durch entfernten Autobuild:** Die Änderung betrifft nur interpretierte CodeQL-Sprachen; die Analyse selbst bleibt unverändert aktiv.
- **Cache-Ausfall:** Alle Workflows funktionieren weiterhin ohne Cache-Hit.

## Verifikation

- GitHub Actions müssen die geänderten Workflow-Dateien erfolgreich laden.
- Backend-Unit-Tests müssen weiterhin mindestens 80 % Coverage erreichen.
- Backend-Integration- und Performance-Suites dürfen keine Skips enthalten.
- Alembic muss Single-Head, FK-Namen, Offline-SQL, Upgrade, Roundtrip, Seed-Dry-Run und Drift-Check bestehen.
- Frontend-Unit- und E2E-Tests müssen unverändert bestehen.
- Security- und MegaLinter-Workflows müssen erfolgreich bzw. gemäß bestehender `continue-on-error`-Semantik laufen.
- Ein Folgelauf mit unverändertem Lockfile soll Cache-Hits für `uv`, Bun und Playwright zeigen.
