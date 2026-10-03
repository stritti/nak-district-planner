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
- [x] 3.2 `Build documentation` für relevante Pull Requests ergänzen; Pages-Deployment auf Push/Dispatch begrenzen.
- [x] 3.3 SemVer-Prerelease-Schema `MAJOR.MINOR.PATCH-rc.N` dokumentieren.
- [x] 3.4 RC-Freeze und zulässige Stabilisierungskategorien dokumentieren.
- [x] 3.5 #403 als zwingendes Merge-Gate des RC-Release-PRs dokumentieren.
- [x] 3.6 Finalisierung von RC auf `v1.0.0` als separaten Release-Please-Konfigurationsschritt dokumentieren.
- [x] 3.7 Verhalten der GHCR-Tags für Prereleases dokumentieren.

## 4. Verifikation

- [ ] 4.1 JSON-Syntax der Release-Please-Konfiguration validieren.
- [ ] 4.2 GitHub Actions lädt die angepassten Release- und Dokumentations-Workflows ohne Workflow-Syntaxfehler.
- [ ] 4.3 `Build documentation` besteht für diesen Pull Request.
- [ ] 4.4 Backend Unit Tests inklusive Coverage-Gate >= 80 % bestehen.
- [ ] 4.5 Backend Integration-/Performance-Tests bestehen und enthalten keine Skips.
- [ ] 4.6 Frontend Unit- und E2E-Tests bestehen.
- [ ] 4.7 Alembic Migration Check inklusive `alembic check` und Roundtrip besteht.
- [ ] 4.8 Restore Drill, MegaLinter, Dependency Review, Security Scans/CodeQL und Docker-Build bestehen.
- [ ] 4.9 Nach Merge dieses Changes prüfen, dass Release Please den bestehenden Release-PR auf `v1.0.0-rc.1` aktualisiert.
- [ ] 4.10 Vor Merge des RC-Release-PRs Ruleset `main` gegen #403 und `docs/production-runbook.md` erneut verifizieren.
- [ ] 4.11 Sicherstellen, dass der Release-PR selbst normale CI-Läufe erhält; `action_required` ohne Jobs ist kein bestandenes Gate.
