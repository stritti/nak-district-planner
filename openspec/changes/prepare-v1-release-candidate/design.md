## Kontext

`main` steht nach #414 und #415 auf einem konsolidierten Stand. Der letzte stabile GitHub Release ist `v0.34.0`; Release Please hält aktuell PR #409 für `0.35.0` offen. Der produktive Release-Workflow baut nach einem Release Backend- und Frontend-Images und setzt für stabile Versionen die Tags `{{version}}`, `{{major}}.{{minor}}`, `{{major}}` und `latest`.

Für die v1-Stabilisierung wird ein echter SemVer-Prerelease benötigt. GitHub soll den Release als Prerelease darstellen und GHCR darf durch einen RC keine stabilen Alias-Tags verlieren. Parallel ist Issue #403 weiterhin offen: Das aktive `main`-Ruleset erzwingt noch keine Pull Requests und keine Required Status Checks. Der RC kann technisch vorbereitet werden, darf aber erst nach diesem Admin-Gate veröffentlicht werden.

Die aktuelle Release-Automation hat zusätzlich Governance-Lücken. Release-PR #409 wird durch `github-actions[bot]` aktualisiert und seine Pull-Request-Workflows werden mit `action_required` beendet, ohne Jobs auszuführen. `docs/release-process.md` verlangt bereits `RELEASE_PLEASE_TOKEN`, der Workflow fällt aber bisher auf `GITHUB_TOKEN` zurück. Der mit #414 eingeführte Dokumentations-Workflow baut VitePress nur nach Push auf `main`; seine ursprüngliche `npm ci`-Konfiguration ist nicht lauffähig, weil das Repository keinen Root-`package-lock.json`, sondern einen autoritativen Root-`bun.lock` besitzt. Zusätzlich sind CodeQL, Frontend-Bun-Audit und Dependency Review mit `continue-on-error` weich geschaltet und würden damit trotz Fehlern als vermeintliche v1-Gates nicht zuverlässig blockieren.

## Ziele

- `v1.0.0-rc.1` reproduzierbar mit der vorhandenen Release-Please-Pipeline erzeugen.
- Weitere Bugfixes während des Freeze automatisch als `rc.2`, `rc.3`, ... versionieren können.
- GitHub Releases der RC-Phase ausdrücklich als Prerelease markieren.
- Stabile GHCR-Aliase vor Prerelease-Versionen schützen.
- Release-PR-Updates müssen normale Pull-Request-Checks auslösen können.
- `Build documentation` muss auf jedem Pull Request gegen `main` existieren, damit der Check im Ruleset verpflichtend sein kann.
- Der Dokumentations-Build muss deterministisch aus dem vorhandenen `bun.lock` installieren.
- Pages-Deployments dürfen nicht parallel gegeneinander laufen.
- Alle als Required Checks vorgesehenen Security- und Dependency-Gates müssen fail-closed sein.
- Den finalen v1.0-Gate-Lauf und den Übergang von RC auf `v1.0.0` eindeutig dokumentieren.
- Bestehende Qualitätsgates unverändert beibehalten oder härten, niemals abschwächen.

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

### 4. Dokumentations-Build wird ein stabiler PR-Check

`docs.yml` reagiert auf jeden Pull Request gegen `main`. Der Build-Job erhält den stabilen Namen `Build documentation` und installiert die Root-Abhängigkeiten mit Bun aus dem vorhandenen Lockfile:

```text
bun install --frozen-lockfile --prefer-offline
bun run docs:build
```

Der Bun-Paketcache wird anhand von Runner-OS, Bun-Version und `bun.lock` adressiert. Ein Cache-Miss ändert die Semantik nicht; der Lockfile bleibt autoritativ. Der Check existiert unabhängig von geänderten Pfaden und kann ohne Pending-Falle als Required Status Check im Ruleset verwendet werden.

`configure-pages`, Artifact-Upload und Deployment laufen bei Pull Requests nicht. Der Deploy-Job wird nur für Push/Dispatch ausgeführt und erhält die notwendigen `pages: write`- und `id-token: write`-Berechtigungen job-lokal. Pull Requests benötigen nur `contents: read`. Für Pushes auf `main` bleiben Dokumentations-, OpenSpec-, Root-Package- und Root-Lockfile-Pfade als Trigger erhalten.

### 5. Pages-Deployments werden serialisiert

Deployment-fähige Runs aus Push auf `main` und `workflow_dispatch` verwenden gemeinsam die Concurrency-Gruppe `pages`. Damit kann ein älterer manueller Lauf nicht parallel zu einem neueren Push deployen. Pull-Request-Builds verwenden dagegen eine PR-spezifische Gruppe `docs-pr-<number>` und beeinflussen die Deployment-Queue nicht.

### 6. Security- und Dependency-Gates sind fail-closed

`continue-on-error` wird aus dem CodeQL-Job, dem Frontend-Bun-Audit und dem Dependency-Review-Job entfernt. Wenn eines dieser Gates einen Fehler meldet, muss der zugehörige Check rot werden und der PR darf das v1-Gate nicht erfüllen.

Die vorhandenen fachlichen Schwellen bleiben unverändert: Dependency Review blockiert ab `high`, Bun-Audit ab `moderate`, CodeQL verwendet weiter `security-and-quality`. Die Änderung betrifft ausschließlich die Fehlersemantik, nicht die Scanner-Konfiguration.

### 7. #403 ist ein hartes Release-Gate

Die RC-Infrastruktur darf vorab gemergt werden, damit Release Please den Candidate-PR erzeugen kann. Der eigentliche Release-PR für `v1.0.0-rc.1` darf jedoch nicht gemergt werden, solange das aktive `main`-Ruleset nicht Pull Requests und die in `docs/production-runbook.md` dokumentierten Required Status Checks verbindlich erzwingt. `Build documentation` wird nach erfolgreicher Verifikation als zusätzliches Gate aufgenommen.

Der aktuelle Connector kann das Ruleset lesen, aber nicht administrativ verändern. Die Konfiguration und anschließende Verifikation bleiben deshalb explizit bei Issue #403.

### 8. RC-Freeze erlaubt nur Stabilisierung

Nach Erstellung des ersten RC werden keine Features mehr für v1.0 aufgenommen. Zulässig sind Bugfixes, Security-Fixes, Testhärtung, Dokumentationskorrekturen und zwingende Betriebsfixes. Jeder Codefix erhält gezielte Regressionstests einschließlich relevanter Ausnahmefälle. Die Backend-Coverage darf nicht unter 80 Prozent fallen.

### 9. Finalisierung auf v1.0.0 ist ein separater, überprüfbarer Schritt

Nach bestandenem RC-Gate wird die Release-Please-Konfiguration in einem separaten Change von der Prerelease-Strategie zurück auf die normale Versionierung gestellt und `prerelease` deaktiviert. Der Merge-Commit dieses Finalisierungs-Changes erhält einmalig `Release-As: 1.0.0`. Dadurch bleiben RC-Erzeugung und Stable-Promotion nachvollziehbar getrennt.

## Risiken und Gegenmaßnahmen

- **RC überschreibt `latest`:** stabile Docker-Aliase sind für Tags mit `-` explizit deaktiviert.
- **Dauerhaft erzwungene RC-Version:** es wird kein `release-as` in der Konfigurationsdatei gespeichert; die Vorgabe lebt nur im Merge-Commit.
- **Release ohne Branch-Gates:** #403 ist dokumentierte Merge-Vorbedingung des RC-Release-PRs.
- **Release-Please-PR ohne ausführbare CI:** `RELEASE_PLEASE_TOKEN` ist zwingend; der Workflow scheitert explizit, wenn das Secret fehlt. Ein PR mit `action_required` erfüllt das RC-Gate nicht.
- **Required-Check bleibt bei nicht relevanten Pfaden pending:** `Build documentation` läuft auf jedem PR gegen `main`, nicht nur bei Dokumentationsänderungen.
- **Nicht deterministische Docs-Installation:** der vorhandene `bun.lock` wird mit `--frozen-lockfile` erzwungen; ein veralteter Lockfile-Stand lässt den Build fehlschlagen.
- **Konkurrierende Pages-Deployments:** alle Deployment-fähigen Runs teilen die `pages`-Concurrency-Gruppe.
- **Scanner meldet Fehler, Check bleibt grün:** für die Required Security- und Dependency-Gates ist `continue-on-error` entfernt.
- **Dokumentationsregression:** jeder PR muss den VitePress-Build bestehen; PRs deployen nicht auf Pages.
- **Feature-Creep nach RC:** die RC-Phase ist als Freeze definiert; releaserelevante Änderungen müssen Stabilisierung sein.
- **Stable-Promotion bleibt Prerelease:** die Finalisierung erfordert explizit das Zurückstellen der Release-Please-Konfiguration vor `v1.0.0`.

## Verifikation

- `release-please-config.json` muss valides JSON bleiben und die unterstützten Prerelease-Optionen verwenden.
- `.github/workflows/release.yml`, `.github/workflows/docs.yml`, `.github/workflows/security.yml` und `.github/workflows/dependency-review.yml` müssen als gültige GitHub-Actions-Workflows geladen werden.
- `bun install --frozen-lockfile --prefer-offline` und `bun run docs:build` müssen im Dokumentationsjob erfolgreich sein.
- Ein PR-Lauf muss Backend-Unit/Coverage, Frontend-Unit/E2E, Alembic, Restore Drill, MegaLinter, Dependency Review, Security/CodeQL und Docker-Build unverändert bestehen.
- `Build documentation` muss auf diesem und auf nachfolgenden Pull Requests gegen `main` erfolgreich laufen.
- CodeQL, Frontend-Bun-Audit und Dependency Review müssen ohne `continue-on-error` erfolgreich sein.
- Der erste durch Release Please aktualisierte Release-PR muss `1.0.0-rc.1` in Manifest, Root-Package, Backend, Frontend und Lockfile setzen.
- Der erzeugte GitHub Release muss als Prerelease markiert sein.
- Die veröffentlichten RC-Images dürfen nur den exakten RC-Versionstag erhalten; `latest`, `1` und `1.0` dürfen nicht auf einen RC zeigen.
- Vor Merge des RC-Release-PRs muss #403 erneut gegen den tatsächlichen Ruleset-Stand verifiziert werden.
