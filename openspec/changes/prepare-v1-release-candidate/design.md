## Kontext

`main` steht nach #414 und #415 auf einem konsolidierten Stand. Der letzte stabile GitHub Release ist `v0.34.0`; Release Please hält aktuell PR #409 für `0.35.0` offen. Der produktive Release-Workflow baut nach einem Release Backend- und Frontend-Images und setzt für stabile Versionen die Tags `{{version}}`, `{{major}}.{{minor}}`, `{{major}}` und `latest`.

Für die v1-Stabilisierung wird ein echter SemVer-Prerelease benötigt. GitHub soll den Release als Prerelease darstellen und GHCR darf durch einen RC keine stabilen Alias-Tags verlieren. Parallel ist Issue #403 weiterhin offen: Das aktive `main`-Ruleset erzwingt noch keine Pull Requests und keine Required Status Checks. Der RC kann technisch vorbereitet werden, darf aber erst nach diesem Admin-Gate veröffentlicht werden.

Die aktuelle Release-Automation hat zusätzlich einen Governance-Fehler: Release-PR #409 wird durch `github-actions[bot]` aktualisiert und seine Pull-Request-Workflows werden mit `action_required` beendet, ohne Jobs auszuführen. `docs/release-process.md` verlangt bereits `RELEASE_PLEASE_TOKEN`, der Workflow fällt aber bisher auf `GITHUB_TOKEN` zurück. Dieser Fallback ist mit verpflichtenden PR-Gates nicht sicher. Der mit #414 eingeführte Dokumentations-Workflow baut VitePress außerdem nur nach Push auf `main`; ein fehlerhafter Dokumentations-PR kann deshalb derzeit ohne VitePress-Build gemergt werden.

## Ziele

- `v1.0.0-rc.1` reproduzierbar mit der vorhandenen Release-Please-Pipeline erzeugen.
- Weitere Bugfixes während des Freeze automatisch als `rc.2`, `rc.3`, ... versionieren können.
- GitHub Releases der RC-Phase ausdrücklich als Prerelease markieren.
- Stabile GHCR-Aliase vor Prerelease-Versionen schützen.
- Release-PR-Updates müssen normale Pull-Request-Checks auslösen können.
- Dokumentationsänderungen müssen vor dem Merge einen VitePress-Build bestehen.
- Den finalen v1.0-Gate-Lauf und den Übergang von RC auf `v1.0.0` eindeutig dokumentieren.
- Bestehende Qualitätsgates unverändert beibehalten.

## Nicht-Ziele

- Keine neue Release-Engine neben Release Please.
- Keine Änderung an Produktlogik, Datenmodell oder API.
- Keine automatische Mutation des GitHub-Rulesets; #403 bleibt ein Repository-Admin-Schritt.
- Keine Feature-Erweiterungen während der RC-Phase.
- Kein automatisches Deployment in eine Produktionsumgebung.
- Kein Pages-Deployment aus Pull Requests.

## Entscheidungen

### 1. Release Please verwendet während des Freeze die Prerelease-Strategie

Für das Root-Paket werden `versioning: prerelease`, `prerelease: true` und `prerelease-type: rc` gesetzt. Damit kann Release Please eine bereits veröffentlichte RC-Version bei weiteren releaserelevanten Commits auf den nächsten Candidate erhöhen und der erzeugte GitHub Release wird als Prerelease gekennzeichnet.

Der erste Candidate muss von `0.34.0` gezielt auf `1.0.0-rc.1` springen. Dafür wird **kein** dauerhaftes `release-as` in `release-please-config.json` gespeichert. Stattdessen erhält ausschließlich der Merge-Commit dieses Changes den Footer:

```text
Release-As: 1.0.0-rc.1
```

Release Please unterstützt diesen Commit-Footer als einmalige Versionsvorgabe. Die Konfiguration bleibt dadurch nach dem Merge wiederverwendbar und erzwingt nicht bei jedem Lauf dieselbe Version.

### 2. RC-Images erhalten keine stabilen Alias-Tags

Der exakte SemVer-Tag `{{version}}` wird für jeden Release veröffentlicht. Die Tags `{{major}}.{{minor}}`, `{{major}}` und `latest` werden nur aktiviert, wenn `tag_name` keinen SemVer-Prerelease-Suffix enthält. Für `v1.0.0-rc.1` entsteht damit ausschließlich:

```text
ghcr.io/stritti/nak-district-planner/backend:1.0.0-rc.1
ghcr.io/stritti/nak-district-planner/frontend:1.0.0-rc.1
```

Die bereits veröffentlichten stabilen Aliase bleiben unverändert.

### 3. Release Please darf nicht auf `GITHUB_TOKEN` zurückfallen

`release.yml` prüft `RELEASE_PLEASE_TOKEN` vor Ausführung von Release Please und verwendet ausschließlich dieses Secret. Ist es nicht gesetzt, bricht der Workflow mit einer verständlichen Fehlermeldung ab.

Der bisherige Fallback auf `GITHUB_TOKEN` wird entfernt. Das verhindert einen scheinbar erfolgreichen Release-Please-Lauf, dessen erzeugter oder aktualisierter PR keine normalen Pull-Request-Workflows auslöst. Ein fehlendes Secret wird damit früh und eindeutig sichtbar.

### 4. Dokumentations-Build wird ein PR-Gate

`docs.yml` reagiert zusätzlich auf dokumentationsrelevante Pull Requests gegen `main`. Der Build-Job erhält den stabilen Namen `Build documentation` und führt `npm ci` sowie `npm run docs:build` aus.

`configure-pages`, Artifact-Upload und Deployment laufen bei Pull Requests nicht. Der Deploy-Job wird nur für Push/Dispatch ausgeführt und erhält die notwendigen `pages: write`- und `id-token: write`-Berechtigungen job-lokal. Pull Requests benötigen nur `contents: read`.

### 5. #403 ist ein hartes Release-Gate

Die RC-Infrastruktur darf vorab gemergt werden, damit Release Please den Candidate-PR erzeugen kann. Der eigentliche Release-PR für `v1.0.0-rc.1` darf jedoch nicht gemergt werden, solange das aktive `main`-Ruleset nicht mindestens Pull Requests und die in `docs/production-runbook.md` dokumentierten Required Status Checks verbindlich erzwingt. `Build documentation` wird nach erfolgreicher Verifikation als zusätzliches Gate aufgenommen.

Der aktuelle Connector kann das Ruleset lesen, aber nicht administrativ verändern. Die Konfiguration und anschließende Verifikation bleiben deshalb explizit bei Issue #403.

### 6. RC-Freeze erlaubt nur Stabilisierung

Nach Erstellung des ersten RC werden keine Features mehr für v1.0 aufgenommen. Zulässig sind Bugfixes, Security-Fixes, Testhärtung, Dokumentationskorrekturen und zwingende Betriebsfixes. Jeder Codefix erhält gezielte Regressionstests einschließlich relevanter Ausnahmefälle. Die Backend-Coverage darf nicht unter 80 Prozent fallen.

### 7. Finalisierung auf v1.0.0 ist ein separater, überprüfbarer Schritt

Nach bestandenem RC-Gate wird die Release-Please-Konfiguration in einem separaten Change von der Prerelease-Strategie zurück auf die normale Versionierung gestellt und `prerelease` deaktiviert. Der Merge-Commit dieses Finalisierungs-Changes erhält einmalig `Release-As: 1.0.0`. Dadurch bleiben RC-Erzeugung und Stable-Promotion nachvollziehbar getrennt.

## Risiken und Gegenmaßnahmen

- **RC überschreibt `latest`:** stabile Docker-Aliase sind für Tags mit `-` explizit deaktiviert.
- **Dauerhaft erzwungene RC-Version:** es wird kein `release-as` in der Konfigurationsdatei gespeichert; die Vorgabe lebt nur im Merge-Commit.
- **Release ohne Branch-Gates:** #403 ist dokumentierte Merge-Vorbedingung des RC-Release-PRs.
- **Release-Please-PR ohne ausführbare CI:** `RELEASE_PLEASE_TOKEN` ist zwingend; der Workflow scheitert explizit, wenn das Secret fehlt. Ein PR mit `action_required` erfüllt das RC-Gate nicht.
- **Dokumentationsregression:** relevante PRs müssen `Build documentation` bestehen; PRs deployen nicht auf Pages.
- **Feature-Creep nach RC:** die RC-Phase ist als Freeze definiert; releaserelevante Änderungen müssen Stabilisierung sein.
- **Stable-Promotion bleibt Prerelease:** die Finalisierung erfordert explizit das Zurückstellen der Release-Please-Konfiguration vor `v1.0.0`.

## Verifikation

- `release-please-config.json` muss valides JSON bleiben und die unterstützten Prerelease-Optionen verwenden.
- `.github/workflows/release.yml` und `.github/workflows/docs.yml` müssen als gültige GitHub-Actions-Workflows geladen werden.
- Ein PR-Lauf muss Backend-Unit/Coverage, Frontend-Unit/E2E, Alembic, Restore Drill, MegaLinter, Dependency Review, Security/CodeQL und Docker-Build unverändert bestehen.
- `Build documentation` muss für diesen dokumentationsrelevanten PR erfolgreich laufen.
- Der erste durch Release Please aktualisierte Release-PR muss `1.0.0-rc.1` in Manifest, Root-Package, Backend, Frontend und Lockfile setzen.
- Der erzeugte GitHub Release muss als Prerelease markiert sein.
- Die veröffentlichten RC-Images dürfen nur den exakten RC-Versionstag erhalten; `latest`, `1` und `1.0` dürfen nicht auf einen RC zeigen.
- Vor Merge des RC-Release-PRs muss #403 erneut gegen den tatsächlichen Ruleset-Stand verifiziert werden.
