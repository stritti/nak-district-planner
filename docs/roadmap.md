# Roadmap und aktueller Stand

> **Stand: 15. Oktober 2026 (GitHub-PR-Status abgeglichen).** [v1.0.0](https://github.com/stritti/nak-district-planner/releases/tag/v1.0.0) ist seit dem 10. Oktober 2026 stabil veröffentlicht. Release 1.1.0 ist vorbereitet: Der Release-PR [PR #572](https://github.com/stritti/nak-district-planner/pull/572) ist grün und mergefähig; das Veröffentlichen von Version und Tag erfolgt automatisch beim Merge. Für kommende Features sind weder Version noch Termin verbindlich festgelegt.

Diese Seite ist die **einzige aktive produktbezogene Roadmap**. Die verbindlichen Regeln für implementiertes Verhalten stehen in der [OpenSpec-Baseline](https://github.com/stritti/nak-district-planner/tree/main/openspec/specs). [Aktive OpenSpec-Changes](https://github.com/stritti/nak-district-planner/tree/main/openspec/changes) und GitHub-Issues beschreiben Änderungen, die noch nicht notwendigerweise umgesetzt sind.

## Release- und Integrationsstand

- **Veröffentlicht:** v1.0.0 (10. Oktober 2026).
- **Release 1.1.0 vorbereitet:** [PR #572](https://github.com/stritti/nak-district-planner/pull/572) (chore(main): release 1.1.0) ist geöffnet, grün und mergefähig. Ein Release-PR ist noch keine veröffentlichte Version; Tag und GitHub-Release entstehen automatisch beim Merge.
- **In `main` integriert und in 1.1.0 enthalten (Auswahl):** Kalendersynchronisation (PR #568, Valkey, persistierte Sync-Fehler), Rollenvertrag/verschobene Serien (PR #571), technische Konsolidierung (PR #573, Issue #474), wiederkehrende Gemeinde-/Bezirkstermine (PR #570, Issue #557), Produktionshärtung mit migrierter Restore-Verifikation (PR #574, Issue #472), Basis für Inline-Editing (PR #576, #577, #578) sowie konfigurierbare Aufgaben je Termin (PR #579).
- **Nach dem Release geplant:** [PR #580](https://github.com/stritti/nak-district-planner/pull/580) (geteilte `SERVICE_LEADER_LABEL`-Konstante, Refactoring aus Review zu #579) wird bewusst erst nach dem Releasen gemergt.
- **Offene Folgefragen:** GitGuardian-Incident 36714356 (PR #574) ist extern zu klassifizieren, ohne das Security-Gate abzuschwächen; Codecov-Upload benötigt weiterhin `CODECOV_TOKEN`.

## Fachlicher Backlog

| Vorhaben | Umfang | Nachweis | Status |
| --- | --- | --- | --- |
| Wiederkehrende Gemeinde-/Bezirkstermine | Wochen-/Monatsmuster, monatliche Checkliste, explizite Übernahme, DST-/Konflikt-/Rechteprüfungen, Dubletten verhindern | [Issue #557](https://github.com/stritti/nak-district-planner/issues/557), [PR #570](https://github.com/stritti/nak-district-planner/pull/570) | **In `main` integriert (PR #570, Issue #557); OpenSpec-Change archiviert, in Release 1.1.0 enthalten** |
| Konfigurierbare Aufgaben je Termin | Schließdienst, Organist, Dirigent, Namensvorschläge und Amtsträger-Lifecycle | [PR #525](https://github.com/stritti/nak-district-planner/pull/525), [PR #579](https://github.com/stritti/nak-district-planner/pull/579) | **In `main` integriert (PR #579); OpenSpec-Change archiviert, in Release 1.1.0 enthalten** |
| Inline-Editing in Übersichten | Berechtigte Tabellenzellen bearbeiten; gemeinsamer Vue-Editor mit Konflikt-/Fehlerbehandlung | [PR #530](https://github.com/stritti/nak-district-planner/pull/530), [PR #576](https://github.com/stritti/nak-district-planner/pull/576), [PR #577](https://github.com/stritti/nak-district-planner/pull/577), [PR #578](https://github.com/stritti/nak-district-planner/pull/578) | **Grundlagen und matrix-spezifische Inline-Zuweisungen in `main` (PR #576–#578); tabellenweite Migration (Change `event-list-inline-cell-editing`) weiterhin in Arbeit** |

**Vorgeschlagene Reihenfolge:** zuerst wiederkehrende Termine, dann organisatorische Aufgaben, danach tabellenweites Inline-Editing. Das ist keine beschlossene Release-Zusage; Security- und Architekturabhängigkeiten können eine andere Reihenfolge erfordern.

## Technische Nacharbeiten

| Thema | Offenes Issue | Geplanter Schwerpunkt |
| --- | --- | --- |
| OIDC und Datenschutz | [#471](https://github.com/stritti/nak-district-planner/issues/471) | Opaque Token-Bindung, JWKS-Refetch, Log-/Fehlerdaten, gehashte Export-Tokens (Einzelissues #581, #582, #583) |
| Kalendersynchronisation | [#470](https://github.com/stritti/nak-district-planner/issues/470) | **In `main` integriert:** PR #568 gemergt; OpenSpec-Change `sync-reliability` archiviert; in Release 1.1.0 enthalten |
| Produktivbetrieb | [#472](https://github.com/stritti/nak-district-planner/issues/472) | **In `main` integriert:** PR #574 gemergt; OpenSpec-Change archiviert, in Release 1.1.0 enthalten; GitGuardian-Incident 36714356 extern zu klären |
| Architektur | [#474](https://github.com/stritti/nak-district-planner/issues/474) | **In `main` integriert:** PR #573 am 13. Oktober gemergt; OpenSpec-Change `refactor-issue-474` archiviert; Codecov-Upload benötigt weiterhin `CODECOV_TOKEN` |
| Berechtigungen und Serien | [#503](https://github.com/stritti/nak-district-planner/issues/503) | **In `main` integriert:** PR #571 gemergt; Regressionen für verschobene Serien ergänzt; in Release 1.1.0 enthalten |
| Matrix- und Kalender-Folgearbeiten | [#584](https://github.com/stritti/nak-district-planner/issues/584), [#585](https://github.com/stritti/nak-district-planner/issues/585) | Lifecycle-Review-Flags in Matrix-Zellen; verteilte Bezirksslots in persönlichen Kalendern |

Die oben genannten Issues enthalten sowohl bereits in `main` integrierte Arbeiten als auch noch offene Folgearbeiten. Integration in `main` bedeutet nicht automatisch Veröffentlichung. Diese Themen sind **Folgearbeiten nach v1.0** und nicht rückwirkend Blocker des veröffentlichten Releases. Aktuelle Änderungen siehe [offene Issues](https://github.com/stritti/nak-district-planner/issues?q=is%3Aissue%20is%3Aopen), [PRs](https://github.com/stritti/nak-district-planner/pulls) und [Releases](https://github.com/stritti/nak-district-planner/releases).

## Release-Regeln

1. OpenSpec-Change vor einer fachlichen Verhaltensänderung erstellen und mit der bestehenden Baseline abgleichen.
2. Implementierung mit Domain-/Application-/Adapter-Grenzen, RBAC, Tenant-Isolation und migrationssicherem Datenmodell.
3. Unit-, Integrations- und gezielte **Negativ-/Ausnahme-Tests**. Verbindliche Messung siehe [Coverage-Strategie](/development/coverage-strategy), Gate nicht abschwächen.
4. CI, Security-Scans, Docs-Build und [Release-Prozess](/operations/release-process) prüfen.
5. Erst nach Implementierung und Tests die Baseline aktualisieren und den OpenSpec-Change archivieren. Ein Spec-PR allein liefert keine Funktion aus.

## Maßgebliche Dokumente

- **Fachliches Verhalten:** [OpenSpec-Baseline](https://github.com/stritti/nak-district-planner/tree/main/openspec/specs), [Use Cases](/features/use-cases)
- **Architektur:** [Architekturstatus](/architecture/status), [Engineering Standards](/development/engineering-standards)
- **Betrieb:** [Runbook](/operations/production-runbook), [Produktiv-Stack](/operations/production-compose)
- **Security:** [Security Baseline](/security/baseline)
- **Historie:** [Archivübersicht](/archive/), [Dokumentationslandkarte](/documentation-map)
