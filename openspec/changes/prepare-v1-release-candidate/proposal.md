## Warum

Der letzte veröffentlichte stabile Stand ist `v0.34.0`, während `main` inzwischen die für den nächsten Release vorgesehenen Änderungen aus #410, #412, #413, #414 und #415 enthält. Vor `v1.0.0` soll dieser Stand als echter Release Candidate veröffentlicht und mit denselben technischen Gates wie der finale Release stabilisiert werden.

Die aktuelle Release-Pipeline kennt nur stabile Releases. Würde ein SemVer-Prerelease mit der bestehenden Docker-Metadatenkonfiguration veröffentlicht, würden zusätzlich die stabilen Alias-Tags `1.0`, `1` und `latest` auf den RC zeigen. Außerdem muss GitHub den RC als Prerelease kennzeichnen und Release Please nach dem ersten Candidate weitere RC-Versionen hochzählen können.

Die erneute Gate-Prüfung zeigt zwei weitere Release-Risiken: Der bestehende Release-PR #409 wird vom `github-actions[bot]` aktualisiert und seine Pull-Request-Workflows enden mit `action_required`, ohne die eigentlichen Jobs auszuführen. Das ist mit künftigen Required Status Checks nicht vereinbar. Außerdem validiert der mit #414 eingeführte VitePress-Workflow Dokumentationsänderungen bislang erst nach dem Merge auf `main`, nicht bereits im Pull Request.

## Was sich ändert

- Release Please wird für die Stabilisierungsphase auf die Prerelease-Versionierungsstrategie mit dem Typ `rc` umgestellt.
- GitHub Releases aus dieser Phase werden als Prerelease markiert.
- Der erste Candidate wird beim Merge dieses Changes einmalig über `Release-As: 1.0.0-rc.1` erzwungen; die Konfiguration enthält keinen dauerhaft erzwungenen Versionswert.
- Release-Docker-Images eines RC erhalten nur den exakten Versions-Tag, z. B. `1.0.0-rc.1`. Die stabilen Alias-Tags `1.0`, `1` und `latest` werden ausschließlich für stabile Versionen veröffentlicht.
- `release.yml` verlangt `RELEASE_PLEASE_TOKEN` explizit und fällt nicht mehr auf `GITHUB_TOKEN` zurück. Fehlt das Secret, scheitert der Workflow klar, statt einen Release-PR zu erzeugen, dessen Required Checks nicht laufen.
- Der VitePress-Build läuft für dokumentationsrelevante Pull Requests als `Build documentation`; Pages-Deployment bleibt auf Push/Dispatch beschränkt.
- Der Release-Prozess dokumentiert RC-Freeze, Gate-Anforderungen, weitere RCs und den Übergang auf `v1.0.0`.
- Der eigentliche RC-Release-PR darf erst gemergt werden, nachdem Issue #403 vollständig umgesetzt und der tatsächliche `main`-Ruleset-Stand verifiziert wurde.

## Capabilities

### New Capabilities

- `release-candidate-process`: reproduzierbarer Release-Candidate-Zyklus vor `v1.0.0`, inklusive Prerelease-Kennzeichnung, versionssicherer Docker-Tags, ausführbarer Release-PR-CI, Dokumentations-Build und verbindlicher Release-Gates.

### Modified Capabilities

- Keine fachlichen Produkt-Capabilities werden geändert.

## Impact

- **Release-Automation:** Release Please erzeugt während der Stabilisierungsphase `rc`-Versionen und markiert die GitHub Releases als Prerelease; ein fehlendes `RELEASE_PLEASE_TOKEN` wird zum expliziten Konfigurationsfehler.
- **Container-Veröffentlichung:** RC-Images können nicht versehentlich `latest`, den Major- oder den Minor-Alias überschreiben.
- **Dokumentation:** VitePress wird bei relevanten Pull Requests gebaut, aber nur nach Merge/Dispatch veröffentlicht.
- **Qualität:** Die bestehenden Test-, Coverage-, Migration-, Restore-, Lint- und Security-Gates werden nicht reduziert; der Dokumentations-Build kommt als zusätzliches Gate hinzu.
- **Betrieb:** Das noch offene Ruleset-Hardening aus #403 bleibt eine zwingende Vorbedingung für das Mergen des RC-Release-PRs.
- **Produktcode:** keine Laufzeitänderung.
