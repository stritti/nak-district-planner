# Release Please Einführung — Design

## Ziel

Die bestehende manuelle Release-Pipeline wird durch Release Please ersetzt. Releases sollen weiterhin eine gemeinsame Projektversion für Root/Docs, Backend und Frontend verwenden. Die Pipeline soll Versionsdateien und ein zentrales root-`CHANGELOG.md` über einen prüfbaren Release-PR aktualisieren, danach GitHub Releases und Docker-Images mit stabilen Tags veröffentlichen.

## Ausgangslage

- Aktuelle Version ist `0.29.1` in:
  - `package.json`
  - `services/backend/pyproject.toml`
  - `services/frontend/package.json`
- `docs/release-process.md` beschreibt bereits Release Please, aber die benötigten Konfigurationsdateien fehlen.
- `.github/workflows/release.yml` enthält derzeit handgeschriebene Shell-Logik für Commit-Analyse, Versionierung, Changelog, Tagging und Docker-Builds.
- Der bestehende Workflow ist riskant, weil er direkt nach `main` pusht, Release Please nachbaut und eine fehleranfällige Tag-/Output-Kopplung enthält.

## Gewählter Ansatz

Release Please wird im Manifest-Mode mit gemeinsamer Version eingeführt.

Neue/angepasste Dateien:

- `release-please-config.json`
- `.release-please-manifest.json`
- `.github/workflows/release.yml`
- `docs/release-process.md`

Die gemeinsame Version wird über den Release-Please-Plugin-Typ `linked-versions` modelliert. Zusätzlich setzt die Config `include-component-in-tag: false`, damit Release Please einen gemeinsamen `vX.Y.Z`-Tag statt komponentenpräfixierter Tags erzeugt. Die Komponenten bleiben getrennt deklariert, werden aber als eine Version veröffentlicht.

## Release-Please-Konfiguration

Pakete:

| Pfad | Release-Typ | Komponente | Version |
| --- | --- | --- | --- |
| `.` | `node` | `root` | `0.29.1` |
| `services/backend` | `python` | `backend` | `0.29.1` |
| `services/frontend` | `node` | `frontend` | `0.29.1` |

Manifest:

- `.release-please-manifest.json` wird mit `0.29.1` für alle drei Pfade initialisiert.
- Release Please aktualisiert künftig Manifest, Changelog und Versionsdateien im Release-PR.

Backend-Besonderheit:

- `services/backend/pyproject.toml` ist die primäre Python-Version.
- `services/backend/uv.lock` wird als Extra-Datei eingebunden; der Pfad ist relativ zu `services/backend` und aktualisiert die Version von `nak-district-planner-backend` im Lockfile.

## GitHub Actions Design

`.github/workflows/release.yml` wird vereinfacht:

1. Trigger auf `push` nach `main` und auf SemVer-Tags `v*.*.*`.
2. Job `release-please` nutzt `googleapis/release-please-action@v4` im Manifest-Mode.
3. Workflow-Berechtigungen:
   - `contents: write`
   - `pull-requests: write`
   - `issues: write`
   - `packages: write`
4. Release Please verwendet `secrets.RELEASE_PLEASE_TOKEN`.

Der bestehende Shell-basierte Release-Job wird entfernt. Dadurch gibt es keine doppelte Versionsberechnung und keinen direkten Action-Commit nach `main` außerhalb des Release-PRs.

## Docker-Veröffentlichung

Docker-Images werden nach einem veröffentlichten Release-Tag gebaut.

Design:

- Docker-Build bleibt im Release-Workflow als separater Job `docker-build`.
- Er läuft nur bei SemVer-Tag-Pushes, nicht bei normalen Pushes auf `main`.
- Images:
  - `ghcr.io/<owner>/<repo>/backend`
  - `ghcr.io/<owner>/<repo>/frontend`
- Tags:
  - `{{version}}`, z. B. `0.30.0`
  - `{{major}}.{{minor}}`, z. B. `0.30`
  - `{{major}}`, z. B. `0`
  - `latest`

Wichtig: Das Repository-Secret `RELEASE_PLEASE_TOKEN` soll ein PAT sein, nicht der normale `GITHUB_TOKEN`. Tags und Releases, die nur mit `GITHUB_TOKEN` erzeugt werden, triggern nachgelagerte Workflows nicht zuverlässig.

## Dokumentation

`docs/release-process.md` wird an die tatsächliche Konfiguration angepasst:

- Release-PR als Review-Gate erklären.
- `RELEASE_PLEASE_TOKEN` als notwendiges Secret dokumentieren.
- Gemeinsame Versionierung von Root, Backend und Frontend festhalten.
- Docker-Tagging beschreiben.
- Hinweis ergänzen, dass `.release-please-manifest.json` nicht manuell gepflegt wird.
- Einziges Changelog ist root-`CHANGELOG.md`; package-lokale Changelogs werden nicht erzeugt.

## Fehler- und Risikobehandlung

- Wenn `RELEASE_PLEASE_TOKEN` fehlt, schlägt der Release-Job sichtbar fehl; es werden keine Secrets im Repository gespeichert.
- Wenn keine release-relevanten Conventional Commits vorhanden sind, aktualisiert Release Please keinen Release-PR.
- Wenn Docker-Builds fehlschlagen, bleibt der GitHub Release bestehen, aber die Workflow-Ausführung zeigt den Fehler. Die Images können durch erneutes Ausführen des Workflows neu gebaut werden.
- Die alte manuelle Release-Logik wird nicht parallel beibehalten, um doppelte Tags/Releases zu vermeiden.

## Verifikation

Vor Abschluss der Implementierung wird geprüft:

- JSON-Syntax von `release-please-config.json` und `.release-please-manifest.json`.
- YAML-Syntax und Struktur von `.github/workflows/release.yml`.
- Version `0.29.1` ist konsistent initialisiert.
- Es wurden keine Secrets committed.
- Dokumentation beschreibt den realen Workflow.

## Nicht-Ziele

- Keine unabhängigen Backend-/Frontend-Versionen.
- Kein vollständiger Umbau der bestehenden CI-, Security- oder Build-Workflows außerhalb des Release-Pfads.
- Kein lokales Erzeugen eines echten GitHub Releases.
