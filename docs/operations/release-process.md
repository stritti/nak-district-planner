# Release-Prozess

> **Stand:** [v1.0.0](https://github.com/stritti/nak-district-planner/releases/tag/v1.0.0) ist seit dem 10. Oktober 2026 stabil veröffentlicht. Die RC-1.0-Abschnitte weiter unten sind historisch; kommende Features siehe [Roadmap](/roadmap).

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

### 1. `release.yml`: Draft-Release und Readiness-Gate

1. `release-please` legt mit `draft: true` und `force-tag-creation: true` einen **Draft-Release** und einen Git-Tag an.
2. `publish-upgrade-notes` überprüft SemVer-Tag, Zugehörigkeit zu `main`, Draft-Status, den öffentlich veröffentlichten Vorgänger-Tag und Upgrade-Anweisungen. Ein Fehler blockiert alle folgenden Jobs.
3. `docker-build` erstellt beide Images aus demselben Tag und pusht ausschließlich eindeutige `candidate-<run_id>-<run_attempt>`-Tags.
4. `scripts/promote_release_images.py` überprüft die beiden Digests und veröffentlicht **danach** beide exakten Versionstags. Bereits vorhandene Versionstags dürfen nicht auf abweichende Digests zeigen.
5. Stabile Releases promoten erst danach die Aliase `major.minor`, `major` und `latest`. Release Candidates verändern diese Aliase nicht.
6. **Erst zuletzt** macht `gh release edit --draft=false` den GitHub Release öffentlich.

Die Concurrency-Gruppe `release-publication` serialisiert alle Runs. GHCR kann Tags in zwei Paketen nicht atomar ändern: Während der Alias-Promotion ist eine kurze Versionsabweichung möglich. Produktion verwendet deshalb **nur exakte Versionstags** mit `APP_VERSION`, niemals mutable Aliase.

Schlägt die Alias-Promotion oder die GitHub-Veröffentlichung fehl, versucht das Skript die vorherigen Alias-Digests wiederherzustellen. Bei fehlenden alten Aliases ist eine manuelle Bereinigung nötig. Der Release bleibt Draft. Der Workflow verwendet weiterhin `RELEASE_PLEASE_TOKEN` für Release Please und `GITHUB_TOKEN` für GHCR und Draft-Änderungen.
### 2. `build.yml` – Docker-Build-Prüfung ohne Veröffentlichung

Dieser Workflow prüft Docker Compose und die Dockerfiles bei Pushes auf `main` oder `develop` sowie bei Pull Requests. Die Builds verwenden ausdrücklich `push: false`; der Workflow meldet sich nicht bei GHCR an und benötigt keine Schreibrechte für Packages. Es werden keine Branch- oder SHA-Images veröffentlicht. Die Checks `Build Backend Image` und `Build Frontend Image` bleiben für das Release-Gate erhalten.

Nur `release.yml` veröffentlicht Images. Release Please erzeugt den Tag zusammen mit einem unveröffentlichten Draft-Release. Beide Service-Images werden aus diesem Git-Tag gebaut. Für normale Commits und Pull Requests werden keine zusätzlichen Git-Tags angelegt.

### 3. `docs.yml` – Dokumentations-Build und Pages-Deployment

Jeder Pull Request gegen `main` muss den stabilen Check `Build documentation` erfolgreich durchlaufen. Dadurch kann der Check im `main`-Ruleset verpflichtend sein, ohne bei Pull Requests mit anderen Dateipfaden zu fehlen. Ein Deployment nach GitHub Pages findet nur bei einem dokumentationsrelevanten Push auf `main` oder bei manuellem Workflow-Dispatch statt, niemals aus einem Pull Request.

---

## Verbindliche Release-Hinweise bei produktiven Änderungen

Releaserelevante Änderungen, die einen manuellen Eingriff an einer bestehenden
Produktivinstallation erfordern, erhalten **zusätzlich zum automatischen
CHANGELOG einen eigenständigen Upgrade-Hinweis**. Beispiele sind neue
Pflichtvariablen, geänderte Datenbank- oder Queue-Credentials, interne
Ports/Proxy-Routen, erforderliche Migrationen, Änderungen an IdP-Deployments
und geänderte Backup- oder Restore-Abläufe.

1. Mit dem entsprechenden Feature-/Fix-PR eine **neue Datei**
   `docs/operations/release-notes/<issue>-<thema>.md` hinzufügen. Kein Release-Tag
   und keine vorweggenommene Versionsnummer im Dateinamen. Bereits veröffentlichte
   Notizen nicht für spätere Releases erneut verwenden.
2. Der Hinweis beginnt mit einer präzisen `###`-Überschrift und enthält
   `**Betroffen:**`, `**Vor dem Update:**` und `**Nach dem Update:**` (fett, mit Doppelpunkt, in dieser Reihenfolge am Zeilenanfang)
   Abschnitte. Er nennt alle neuen Pflichtwerte, Vorbedingungen,
   manuelle Schritte und Verifikationen; optionale Änderungen sind als solche
   zu kennzeichnen. Secrets dürfen nur als Variablennamen vorkommen.
3. Im Release-PR prüfen, dass Hinweise für sämtliche Betreiberaktionen seit
   dem vorherigen Release vorhanden und fachlich korrekt sind. Änderungen
   ohne manuellen Handlungsbedarf benötigen keine solche Datei.
4. Vor der öffentlichen Veröffentlichung ergänzt `publish-upgrade-notes` ausschließlich den **Draft** um neue Hinweise. Ältere Hinweise werden nicht dupliziert; der generierte CHANGELOG bleibt unverändert.
5. Bei ungültigen Hinweisen oder GitHub-API-Fehlern werden die Image-Builds und die Release-Veröffentlichung blockiert.
6. Der Draft wird erst nach erfolgreicher Image-Digest-/Tag-Promotion veröffentlicht.

Der Publisher ist idempotent; erneute Workflows erzeugen keine Duplikate.
Die zugehörigen Regressionstests laufen im Dokumentations-CI-Job
(`python3 -m unittest discover -s scripts -p 'test_publish_release_upgrade_notes.py'`).
Erstmalig wird dieses Verfahren für die
[Produktionshärtung #472](./release-notes/472-production-hardening.md) genutzt.

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
   - Einen **Draft**-GitHub-Release mit dem CHANGELOG als Beschreibung
7. `publish-upgrade-notes` validiert die Betriebsanweisungen und ergänzt den Draft-Release.
8. `docker-build` baut beide Staging-Images, verifiziert die Digests, promotet Versionstags und danach stabile Aliase. Zuletzt wird der GitHub Release veröffentlicht.

---

## Release-Recovery bei partieller Veröffentlichung

1. Fehler im Actions-Job und Draft-Status unter GitHub Releases prüfen. Der Draft darf nicht manuell vorzeitig freigegeben werden.
2. In GHCR für **beide** Dienste den Digest des Kandidaten und eines möglicherweise schon gesetzten Versionstags vergleichen. Fertige Versionstags sind write-once.
3. Unter Actions -> Release -> Run workflow mit Branch `main` und dem vorhandenen Draft-Tag (z. B. `v1.2.3`) neu starten. Notes, beide Builds und die Promotion werden erneut geprüft.
4. Falls ein Retry einen anderen Digest für einen schon existierenden Versionstag erzeugt, wird die Veröffentlichung blockiert. Alte Images nicht überschreiben: Original-Digest aus dem früheren Run sichern, den Gegenpart der identischen Revision herstellen und die Freigabe kontrolliert abschließen.
5. Wenn nach einem fehlgeschlagenen Alias-Update das automatische Rollback scheitert, Aliase mit den vorherigen Digests wiederherstellen. Neu entstandene Aliase ohne früheren Digest gegebenenfalls manuell löschen.
6. Erst beide exakt versionierten Images, Upgrade-Hinweise, GHCR-Aliase und anschließend die Freigabe des Drafts prüfen. Bis dahin bei produktiven Installationen die letzte vollständig veröffentlichte `APP_VERSION` beibehalten.

Bei einem Recovery-Versuch prüft der Promotionsschritt außerdem sämtliche öffentlichen GitHub Releases. Existiert bereits eine **höhere SemVer-Version**, wird der ältere Draft vor Änderungen an GHCR-Versionstags oder Aliases abgewiesen. Unmittelbar vor der öffentlichen Freigabe erfolgt die Prüfung erneut. Das schützt vor einem Downgrade von `latest` und weiteren stabilen Aliases.

Vor einer neuen Veröffentlichung muss der direkte Vorgänger-Tag ein **öffentliches GitHub Release** besitzen. Ist der Vorgänger noch Draft oder wurde das Release bei vorhandenem Tag gelöscht, verweigert der Notes-Schritt die Freigabe des Nachfolgers. Zuerst den ursprünglichen Draft reparieren und veröffentlichen, statt seine Upgrade-Anweisungen zu überspringen.

Ein nicht vorhandener Draft wird als Recovery-Ziel abgelehnt. GitHub und GHCR unterstützen keine atomare Mehrfachveröffentlichung, daher werden Images in Produktion nur über exakte Versions-Tags referenziert.

---
## Historie: v1.0 Release-Candidate-Phase (abgeschlossen)

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

**Abgeschlossen am 10. Oktober 2026:** Die Promotion erfolgte über [PR #563](https://github.com/stritti/nak-district-planner/pull/563) mit `Release-As: 1.0.0` und den grünen [Release-PR #564](https://github.com/stritti/nak-district-planner/pull/564). Der [stabile Release](https://github.com/stritti/nak-district-planner/releases/tag/v1.0.0) und die [GHCR-Images](https://github.com/stritti/nak-district-planner/actions/runs/38087662984) wurden veröffentlicht.

Der dokumentierte Ablauf der finalen Promotion war:

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

## Post-1.0: Abhängigkeiten der Dokumentation

Die VitePress-Dokumentation wird aus dem Root-`package.json` und Root-`bun.lock` gebaut. Ein Wechsel von VitePress 1.x auf einen neuen Major ist **kein** Bestandteil der Release-Promotion. Er erfolgt in einem gesonderten Dependency-PR erst, nachdem sowohl `@stritti/vitepress-plugin-openspec` als auch `vitepress-plugin-mermaid-diagram` kompatibel sind, `bun audit --audit-level=moderate` sauber ist, die Mermaid-SVG-Prüfung besteht und der Pages-Build grünes Licht gibt. Zur Vermeidung eines ungeprüften Toolchain-Wechsels bleibt bis dahin die per Lockfile fixierte 1.x-Version gültig. Dependabot prüft die Root-Dependencies wöchentlich.

Für Bun 1.4.2 verwenden sowohl das Root-Lockfile als auch `services/frontend/bun.lock` `lockfileVersion: 1` und `configVersion: 1`; CI erzwingt an beiden Orten `bun install --frozen-lockfile`. Ein Lockfile-Formatwechsel darf keine impliziten Dependency-Upgrades auslösen.

Die OpenSpec-Dokumentationsprüfung validiert die **Baseline und alle aktiven Changes** mit `openspec validate --all --strict --no-interactive`. Ungültige aktive Spezifikationen müssen vor dem Merge korrigiert oder vollständig archiviert werden.

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

Neue Releases werden nach dem Merge eines Release-PRs auf `main` automatisch gestartet. Für **Recovery** unterstützt `release.yml` `workflow_dispatch` mit dem Input `release_tag` und Branch `main`. Dabei wird nur ein existierender Draft mit gültigem SemVer-Tag akzeptiert; Release Please läuft nicht erneut. Der Dokumentations-Workflow unterstützt ebenfalls `workflow_dispatch`.

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

---

## Bestehende CI-Images bereinigen

Der Workflow **Cleanup non-release container images** (`.github/workflows/cleanup-images.yml`) wird ausschließlich manuell gestartet und löscht nur im Branch `main`.

1. Bei beiden GHCR-Paketen unter **Package settings → Manage Actions access** dem Repository `nak-district-planner` die Rolle **Admin** geben. Der Workflow verwendet `GITHUB_TOKEN`; ein persönlicher Token ist nicht erforderlich.
2. In **Actions → Cleanup non-release container images → Run workflow** den Branch `main` und den Modus `preview` wählen.
3. Die Kandidaten mit Paket, Versions-ID, Digest und Tags in der Run-Zusammenfassung prüfen.
4. Zum Bereinigen denselben Workflow mit Modus `delete` starten. Dieser Lauf ermittelt die Kandidaten erneut und prüft vor jeder Löschung nochmals die aktuellen Tags.

Ein Kandidat muss mindestens einen Tag haben; sämtliche Tags müssen `main`, `develop` oder `sha-<7 bis 40 hexadezimale Zeichen>` sein. Ein zusätzlicher Release-Tag oder unbekannter Tag schützt die gesamte Version. Auch Digests, die in der Paketliste unter einer geschützten Version vorkommen, bleiben erhalten. Untagged-Versionen werden grundsätzlich nicht gelöscht: Sie können Plattform-Manifeste oder Attestierungen von Release-Images sein. Deshalb ist dieser Workflow keine vollständige Bereinigung aller ungetaggten Daten.

Beide Pakete werden vollständig und mit Pagination gelesen, bevor Löschungen beginnen. API-Fehler brechen den Lauf ab; bereits ausgeführte Löschungen werden nicht automatisch rückgängig gemacht. Der Workflow startet weder durch Push noch zeitgesteuert. Seine Schutzregeln werden mit simulierten API-Antworten in Pull Requests und vor jedem manuellen Lauf geprüft.
