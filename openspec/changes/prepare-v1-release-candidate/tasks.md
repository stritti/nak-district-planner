## 1. Release-Please-Prerelease-Modus

- [x] 1.1 Root-Paket in `release-please-config.json` auf `versioning: prerelease` setzen.
- [x] 1.2 `prerelease: true` und `prerelease-type: rc` konfigurieren.
- [x] 1.3 Keine dauerhafte `release-as`-Konfiguration hinterlegen; erster RC wird einmalig per Merge-Commit-Footer `Release-As: 1.0.0-rc.1` angefordert.

## 2. Docker-Tags für RC absichern

- [x] 2.1 Exakten `{{version}}`-Tag für stabile und Prerelease-Versionen beibehalten.
- [x] 2.2 `{{major}}.{{minor}}`, `{{major}}` und `latest` bei Prerelease-Tags deaktivieren.
- [x] 2.3 Stable-Verhalten unverändert lassen: normale Releases veröffentlichen weiterhin exakten, Minor-, Major- und `latest`-Tag.

## 3. Release-PR-CI und Dokumentation härten

- [x] 3.1 `RELEASE_PLEASE_TOKEN` vor Release Please explizit verlangen und den `GITHUB_TOKEN`-Fallback entfernen.
- [x] 3.2 `Build documentation` auf jedem Pull Request gegen `main` ausführen, damit der Check im Ruleset immer vorhanden ist; Installation deterministisch über Root-`bun.lock`.
- [x] 3.3 Pages-Deployments aus Push und `workflow_dispatch` in derselben `pages`-Concurrency-Gruppe serialisieren; PR-Builds separat halten.
- [x] 3.4 CodeQL, Frontend-Bun-Audit und Dependency Review fail-closed konfigurieren; `continue-on-error` aus den v1-Gates entfernen.
- [x] 3.5 SemVer-Prerelease-Schema `MAJOR.MINOR.PATCH-rc.N` dokumentieren.
- [x] 3.6 RC-Freeze und zulässige Stabilisierungskategorien dokumentieren.
- [x] 3.7 #403 als zwingendes Merge-Gate des RC-Release-PRs dokumentieren.
- [x] 3.8 Finalisierung von RC auf `v1.0.0` als separaten Release-Please-Konfigurationsschritt dokumentieren.
- [x] 3.9 Verhalten der GHCR-Tags für Prereleases dokumentieren.

## 4. Verifikation

- [ ] 4.1 JSON-Syntax der Release-Please-Konfiguration validieren.
- [ ] 4.2 GitHub Actions lädt die angepassten Release-, Docs-, Security- und Dependency-Review-Workflows ohne Workflow-Syntaxfehler.
- [ ] 4.3 `Build documentation` besteht für diesen Pull Request mit `bun install --frozen-lockfile --prefer-offline`.
- [ ] 4.4 Backend Unit Tests inklusive Coverage-Gate >= 80 % bestehen.
- [ ] 4.5 Backend Integration-/Performance-Tests bestehen und enthalten keine Skips.
- [ ] 4.6 Frontend Unit- und E2E-Tests bestehen.
- [ ] 4.7 Alembic Migration Check inklusive `alembic check` und Roundtrip besteht.
- [ ] 4.8 Restore Drill, MegaLinter, Dependency Review, Security Scans/CodeQL und Docker-Build bestehen.
- [ ] 4.9 Verifizieren, dass CodeQL, Bun-Audit und Dependency Review ohne `continue-on-error` laufen.
- [ ] 4.10 Nach Merge dieses Changes prüfen, dass Release Please den bestehenden Release-PR auf `v1.0.0-rc.1` aktualisiert.
- [ ] 4.11 Vor Merge des RC-Release-PRs Ruleset `main` gegen #403 und `docs/production-runbook.md` erneut verifizieren.
- [ ] 4.12 Sicherstellen, dass der Release-PR selbst normale CI-Läufe erhält; `action_required` ohne Jobs ist kein bestandenes Gate.
