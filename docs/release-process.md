# Release-Prozess

Der NAK District Planner verwendet eine vollautomatisierte **Semantic Versioning (SemVer)** Release-Pipeline, die auf [Conventional Commits](https://www.conventionalcommits.org/de/) und [release-please](https://github.com/googleapis/release-please) basiert.

---

## Versionierungsschema (SemVer)

Stabile Versionen folgen dem Format **`MAJOR.MINOR.PATCH`** (z. B. `1.2.3`):

| Segment | Bedeutung | Auslöser |
|---------|-----------|---------|
| `MAJOR` | Inkompatible API-Änderungen | Commit mit `BREAKING CHANGE:` im Footer |
| `MINOR` | Neue, abwärtskompatible Features | Commit mit Präfix `feat:` |
| `PATCH` | Fehlerbehebungen | Commit mit Präfix `fix:` oder `perf:` |

> **Hinweis:** Solange das Projekt die Version `0.x.y` hat, löst ein `feat:`-Commit einen Minor-Bump (z. B. `0.1.0 → 0.2.0`) und ein `BREAKING CHANGE` ebenfalls nur einen Minor-Bump aus, um die Vorab-Phase zu respektieren.

Für die Stabilisierungsphase vor `v1.0.0` werden SemVer-Prereleases im Format **`1.0.0-rc.N`** verwendet, beginnend mit `v1.0.0-rc.1`. Diese Releases werden auf GitHub ausdrücklich als Prerelease markiert.

---

## Conventional Commits

Alle Commits auf dem `main`-Branch **müssen** dem [Conventional Commits Standard](https://www.conventionalcommits.org/de/) folgen, damit die automatische Versionierung korrekt funktioniert.

### Format

```text
<type>(<scope>): <kurze Beschreibung>

[optionaler Body]

[optionaler Footer: BREAKING CHANGE: ...]
```

### Zulässige Typen

| Typ | Wirkung auf Version | Sichtbar im CHANGELOG |
|-----|--------------------|-----------------------|
| `feat` | Minor-Bump | ja (Features) |
| `fix` | Patch-Bump | ja (Bug Fixes) |
| `perf` | Patch-Bump | ja (Performance) |
| `revert` | Patch-Bump | ja (Reverts) |
| `docs` | Patch-Bump | ja (Documentation) |
| `refactor` | Patch-Bump | ja (Code Refactoring) |
| `chore` | kein Bump | ausgeblendet |
| `style` | kein Bump | ausgeblendet |
| `test` | kein Bump | ausgeblendet |
| `build` | kein Bump | ausgeblendet |
| `ci` | kein Bump | ausgeblendet |

### Beispiele

```bash
# Neues Feature → Minor-Bump (0.1.0 → 0.2.0)
git commit -m "feat(matrix): Gottesdienst-Zuweisung per Drag & Drop"

# Fehlerbehebung → Patch-Bump (0.1.0 → 0.1.1)
git commit -m "fix(api): Datumsformat bei ICS-Export korrigiert"

# Breaking Change → Major-Bump (1.0.0 → 2.0.0)
git commit -m "feat(auth)!: JWT-basiertes Auth erfordert Header-Änderung" -m "BREAKING CHANGE: X-API-Key Header wurde durch Authorization: Bearer ersetzt"

# Nur Doku → Patch-Bump
# Release-Auswirkung richtet sich nach der Release-Please-Konfiguration.
git commit -m "docs: Release-Prozess dokumentiert"
```

---

## Wie die Pipeline funktioniert

Die Release-Pipeline besteht aus mehreren GitHub Actions Workflows. Für die eigentliche Veröffentlichung sind `release.yml` und die Docker-Builds maßgeblich.

### 1. `release.yml` – Release Please + Docker-Veröffentlichung

```text
Push auf main
     │
     ▼
RELEASE_PLEASE_TOKEN prüfen
     │
     ▼
googleapis/release-please-action
     │
     ├─── Kein neuer Commit mit relevantem Typ
     │         → Nichts passiert
     │
     └─── Neuer relevanter Commit erkannt
               │
               ├─── Release-PR existiert noch nicht
               │         → Release-PR wird erstellt / aktualisiert
               │           (CHANGELOG.md + Versions-Bump in Dateien)
               │
               └─── Release-PR wird gemergt
                         → GitHub Release + Git-Tag
                         → docker-build im selben Workflow-Run
                           (needs: release-please, releases_created == 'true')
                         → Docker-Images mit erlaubten Versions-Tags veröffentlicht
```

`release.yml` verwendet ausschließlich `RELEASE_PLEASE_TOKEN`. Ein Fallback auf `GITHUB_TOKEN` ist absichtlich nicht erlaubt, weil von `GITHUB_TOKEN` erzeugte Aktualisierungen des Release-PRs die für das Ruleset erforderlichen Pull-Request-Workflows unterdrücken können. Fehlt das Secret, bricht der Workflow mit einer expliziten Fehlermeldung ab.

### 2. `build.yml` – Docker-Build-Prüfung ohne Veröffentlichung

Dieser Workflow prüft Docker Compose und die Dockerfiles bei Pushes auf `main` oder `develop` sowie bei Pull Requests. Die Builds verwenden ausdrücklich `push: false`; der Workflow meldet sich nicht bei GHCR an und benötigt keine Schreibrechte für Packages. Es werden keine Branch- oder SHA-Images veröffentlicht. Die Checks `Build Backend Image` und `Build Frontend Image` bleiben für das Release-Gate erhalten.

Nur `release.yml` veröffentlicht Images, nachdem Release Please nach dem Merge eines Release-PRs einen GitHub Release und den zugehörigen Git-Tag erstellt hat. Beide Service-Images werden aus diesem Git-Tag gebaut. Für normale Commits und Pull Requests werden keine zusätzlichen Git-Tags angelegt.

### 3. `docs.yml` – Dokumentations-Build und Pages-Deployment

Jeder Pull Request gegen `main` muss den stabilen Check `Build documentation` erfolgreich durchlaufen. Dadurch kann der Check im `main`-Ruleset verpflichtend sein, ohne bei Pull Requests mit anderen Dateipfaden zu fehlen. Ein Deployment nach GitHub Pages findet nur bei einem dokumentationsrelevanten Push auf `main` oder bei manuellem Workflow-Dispatch statt, niemals aus einem Pull Request.

---

## Release-PR Workflow

1. Entwickler pushen Feature-Branches und erstellen Pull Requests auf `main`.
2. Nach dem Merge in `main` analysiert **release-please** alle neuen Commits seit dem letzten Release.
3. release-please erstellt oder aktualisiert automatisch einen **Release-PR**.
4. Dieser PR enthält:
   - Aktualisiertes root-`CHANGELOG.md`
   - Versions-Bump in `package.json` (root + frontend)
   - Versions-Bump in `services/backend/pyproject.toml`
   - Versions-Bump in `services/backend/uv.lock`
5. Ein Maintainer prüft den Release-PR einschließlich aller Required Status Checks und mergt ihn erst nach bestandenem Gate.
6. release-please erstellt automatisch:
   - Einen Git-Tag
   - Einen GitHub Release mit dem CHANGELOG als Beschreibung
7. Der `docker-build`-Job im selben Workflow-Run (`needs: release-please`, nur bei `releases_created == 'true'`) checkt den Release-Tag aus und baut und veröffentlicht Docker-Images mit den für den Release-Typ erlaubten Tags.

---

## v1.0 Release-Candidate-Phase

Vor `v1.0.0` wird mindestens ein echter Release Candidate veröffentlicht. Während dieser Phase ist Release Please auf die Prerelease-Versionierungsstrategie mit `prerelease-type: rc` eingestellt.

### Erster Candidate

Der erste Candidate wird einmalig über einen `Release-As`-Footer im Merge-Commit des RC-Vorbereitungs-Changes angefordert:

```text
Release-As: 1.0.0-rc.1
```

`release-as` wird nicht dauerhaft in `release-please-config.json` hinterlegt. Damit kann Release Please nachfolgende Stabilisierungsversionen regulär als weitere RCs fortschreiben.

### Feature Freeze

Ab `v1.0.0-rc.1` gilt Feature Freeze für die v1.0-Linie. Zulässig sind ausschließlich:

- Bugfixes mit gezielten Regressionstests
- Security-Fixes
- Testhärtung einschließlich relevanter Ausnahmefälle
- notwendige Dokumentationskorrekturen
- zwingende Betriebs- und Release-Fixes

Neue fachliche Features werden nicht mehr in die v1.0-Stabilisierungslinie aufgenommen. Die Backend-Coverage-Grenze bleibt mindestens 80 Prozent.

### Verbindliches RC-Gate

Ein RC-Release-PR darf erst gemergt werden, wenn das aktive `main`-Ruleset aus Issue #403 Pull Requests und die Required Status Checks tatsächlich erzwingt. Mindestens folgende Checks gehören zum v1-Gate:

- `Backend — Unit Tests & Coverage` mit Backend-Coverage >= 80 Prozent
- vollständige Backend-Integration-/Performance-Suite ohne Skips
- `Frontend — Unit Tests`
- `Frontend — E2E Tests`
- `Migration Graph & FK Names` inklusive blockierendem `alembic check`, Roundtrip und Drift-Prüfung
- `Encrypted Backup & Isolated Restore`
- `MegaLinter`
- `Dependency Review`
- `CodeQL Analysis (python)`
- `CodeQL Analysis (javascript-typescript)`
- `Python Dependency Audit (pip-audit)`
- `Frontend Dependency Audit (bun audit)`
- `Build Backend Image`
- `Build Frontend Image`
- `Build documentation`

Ein Workflow mit `action_required`, der seine eigentlichen Jobs nicht ausgeführt hat, gilt nicht als bestanden.

### Weitere Candidates

Werden nach `v1.0.0-rc.1` releaserelevante Stabilisierungskorrekturen gemergt, erhöht die Prerelease-Strategie den Candidate-Zähler für den nächsten Release. Jeder Candidate durchläuft erneut das vollständige Gate.

### Promotion auf `v1.0.0`

Die finale Promotion ist ein eigener überprüfbarer Change:

1. Prerelease-Versionierung in `release-please-config.json` deaktivieren und auf die normale Versionierung zurückstellen.
2. Den vollständigen v1-Gate-Lauf auf diesem finalen Stand durchführen.
3. Den Finalisierungs-Change mit dem einmaligen Footer `Release-As: 1.0.0` mergen.
4. Den von Release Please erzeugten `v1.0.0`-Release-PR erst nach erneut vollständig grünem Gate mergen.
5. Prüfen, dass `v1.0.0` als stabiler GitHub Release erscheint und die stabilen GHCR-Aliase aktualisiert werden.

### Toolchain-Versionen

Laufzeit- und CI-Toolchain müssen identisch sein. Ein Dependabot-Update eines Basis-Images wird nur zusammen mit allen Pins gemergt:

| Werkzeug | Quelle der Wahrheit | Muss übereinstimmen mit |
|---|---|---|
| Python | `services/backend/Dockerfile` (`python:3.14.7-slim`) | `PYTHON_VERSION` in `ci.yml` und `alembic-check.yml`, `python-version` in `security.yml`, `requires-python` und ruff `target-version` in `services/backend/pyproject.toml`, `uv.lock` |
| bun | `services/frontend/Dockerfile` (`oven/bun:1.4.2-alpine`) | `BUN_VERSION` in `ci.yml`, `docs.yml` und `security.yml`; Lockfiles bestehen `bun install --frozen-lockfile` |
| uv | `version` von `astral-sh/setup-uv` in `ci.yml` | `alembic-check.yml`, `security.yml` |

---

## Automatisch aktualisierte Dateien

release-please aktualisiert bei einem Release die Versions-Angaben in folgenden Dateien:

| Datei | Format |
|-------|--------|
| `package.json` | `"version": "1.2.0"` |
| `services/frontend/package.json` | `"version": "1.2.0"` |
| `services/backend/pyproject.toml` | `version = "1.2.0"` (unter `[project]`) |
| `services/backend/uv.lock` | Paketversion von `nak-district-planner-backend` |
| `.release-please-manifest.json` | Aktuelle Release-Please-Versionen pro Pfad |
| `CHANGELOG.md` | Neuer Abschnitt mit allen Änderungen |

Bei einem RC enthalten die Versionsdateien entsprechend eine Prerelease-Version wie `1.0.0-rc.1`.

---

## Docker-Image-Tags bei einem Release

Stabile Releases veröffentlichen Backend- und Frontend-Images mit folgenden Tags:

| Tag | Beispiel | Bedeutung |
|-----|---------|-----------|
| `{{version}}` | `1.2.0` | Exakte Version |
| `{{major}}.{{minor}}` | `1.2` | Minor-Stream |
| `{{major}}` | `1` | Major-Stream |
| `latest` | `latest` | Neueste stabile Version |

Release Candidates veröffentlichen ausschließlich den exakten Prerelease-Tag:

```text
ghcr.io/stritti/nak-district-planner/backend:1.0.0-rc.1
ghcr.io/stritti/nak-district-planner/frontend:1.0.0-rc.1
```

Die stabilen Aliase `1.0`, `1` und `latest` werden von einem RC nicht verändert. Erst `v1.0.0` aktualisiert sie wieder.

---

## Manuelles Auslösen

Ein direktes Auslösen der Release-Pipeline über die GitHub-UI ist derzeit nicht konfiguriert; Releases werden durch Pushes auf `main` gestartet. Der Dokumentations-Workflow unterstützt zusätzlich `workflow_dispatch`.

---

## Konfiguration

Die Release-Pipeline wird durch folgende Dateien konfiguriert:

| Datei | Zweck |
|-------|-------|
| `release-please-config.json` | Ein Paket (Root, `simple`), Versionsdateien aller Services via `extra-files`, gemeinsame Tag- und RC-Konfiguration |
| `.release-please-manifest.json` | Aktuelle Versions-Stände, nicht manuell bearbeiten |
| `.github/workflows/release.yml` | Release Please und Release-Docker-Images |
| `.github/workflows/build.yml` | Docker-Build-Prüfung ohne Veröffentlichung |
| `.github/workflows/docs.yml` | Dokumentations-Build und Pages-Deployment |

---

## Erforderliches GitHub Secret

Der Workflow benötigt zwingend das Repository-Secret `RELEASE_PLEASE_TOKEN`.

Verwendet werden muss ein Token, dessen mit Release Please erzeugte oder aktualisierte Pull Requests die normalen Pull-Request-Workflows auslösen können. Ein Fine-Grained Personal Access Token benötigt die für Contents, Pull Requests und Issues erforderlichen Schreibrechte. Der Release-Workflow fällt absichtlich nicht auf `GITHUB_TOKEN` zurück.

Das Secret darf nicht in Dateien, Logs oder Commits gespeichert werden.

---

## Weiterführende Links

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [release-please](https://github.com/googleapis/release-please)
