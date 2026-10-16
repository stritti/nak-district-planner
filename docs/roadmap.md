# Roadmap und aktueller Stand

> **Stand: 16. Oktober 2026 (GitHub-PR-Status abgeglichen).** [v1.1.0](https://github.com/stritti/nak-district-planner/releases/tag/v1.1.0) ist seit dem 15. Oktober 2026 veröffentlicht (nach [v1.0.0](https://github.com/stritti/nak-district-planner/releases/tag/v1.0.0) vom 10. Oktober 2026). Für kommende Features sind weder Version noch Termin verbindlich festgelegt.

Diese Seite ist die **einzige aktive produktbezogene Roadmap**. Die verbindlichen Regeln für implementiertes Verhalten stehen in der [OpenSpec-Baseline](https://github.com/stritti/nak-district-planner/tree/main/openspec/specs). [Aktive OpenSpec-Changes](https://github.com/stritti/nak-district-planner/tree/main/openspec/changes) und GitHub-Issues beschreiben Änderungen, die noch nicht notwendigerweise umgesetzt sind.

## Release- und Integrationsstand

- **Veröffentlicht:** v1.0.0 (10. Oktober 2026) und v1.1.0 (15. Oktober 2026, [PR #572](https://github.com/stritti/nak-district-planner/pull/572)).
- **In `main` integriert und in 1.1.0 enthalten (Auswahl):** Kalendersynchronisation (PR #568, Valkey, persistierte Sync-Fehler), Rollenvertrag/verschobene Serien (PR #571), technische Konsolidierung (PR #573, Issue #474), wiederkehrende Gemeinde-/Bezirkstermine (PR #570, Issue #557), Produktionshärtung mit migrierter Restore-Verifikation (PR #574, Issue #472), Basis für Inline-Editing (PR #576, #577, #578) sowie konfigurierbare Aufgaben je Termin (PR #579).
- **Auf `main`, noch nicht veröffentlicht:** Der Release-PR [#592](https://github.com/stritti/nak-district-planner/pull/592) („release 1.2.0“) ist offen; ein Release-PR ist noch keine veröffentlichte Version. Enthalten sind: geteilte `SERVICE_LEADER_LABEL`-Konstante (PR #580, über PR #587), gehashte Export-Tokens (PR #590, Issue #582), angeglichene RLS-Rollen-Guards (PR #589, Issue #581), Audit-Snapshot der Duty-RLS-Funktionen (PR #591, Issue #583), Code-Review mit Auth-Härtung, gemeinsamen Guards und View-Zerlegung (PR #593), Inline-Editing auf mobilen Karten (PR #594) und in der Amtstragenden-Verwaltung (PR #595), OpenSpec-Abgleich und Adapter-Härtung zu [#471](https://github.com/stritti/nak-district-planner/issues/471) (PR #596) der stabile Fehlervertrag für wiederkehrende Termine zu [#557](https://github.com/stritti/nak-district-planner/issues/557) (PR #597) sowie der Abschluss des Inline-Editings (PR #599).
- **Offene Folgefragen:** GitGuardian-Incident 36714356 (PR #574) ist extern zu klassifizieren, ohne das Security-Gate abzuschwächen; Codecov-Upload benötigt weiterhin `CODECOV_TOKEN`.

## Fachlicher Backlog

| Vorhaben | Umfang | Nachweis | Status |
| --- | --- | --- | --- |
| Wiederkehrende Gemeinde-/Bezirkstermine | Wochen-/Monatsmuster, monatliche Checkliste, explizite Übernahme, DST-/Konflikt-/Rechteprüfungen, Dubletten verhindern | [Issue #557](https://github.com/stritti/nak-district-planner/issues/557), [PR #570](https://github.com/stritti/nak-district-planner/pull/570) | **In `main` integriert (PR #570, Issue #557); OpenSpec-Change archiviert, in Release 1.1.0 enthalten** |
| Konfigurierbare Aufgaben je Termin | Schließdienst, Organist, Dirigent, Namensvorschläge und Amtsträger-Lifecycle | [PR #525](https://github.com/stritti/nak-district-planner/pull/525), [PR #579](https://github.com/stritti/nak-district-planner/pull/579) | **In `main` integriert (PR #579); OpenSpec-Change archiviert, in Release 1.1.0 enthalten** |
| Inline-Editing in Übersichten | Berechtigte Tabellenzellen bearbeiten; gemeinsamer Vue-Editor mit Konflikt-/Fehlerbehandlung | [PR #530](https://github.com/stritti/nak-district-planner/pull/530), [PR #576](https://github.com/stritti/nak-district-planner/pull/576), [PR #577](https://github.com/stritti/nak-district-planner/pull/577), [PR #578](https://github.com/stritti/nak-district-planner/pull/578) | **In `main`, noch nicht veröffentlicht (Release-PR #592):** Ereignisliste (Titel, Start, Kategorie, Zuordnung, Verantwortliche:r; Tabelle und mobile Karten, PR #576–#578, #593, #594), Amtstragenden-Verwaltung (Name, Kontakt, Grad, Beauftragung, Heimat-Gemeinde, Aktiv-Status, PR #595) und Matrix-Zuweisung. Konfliktprüfung, Vorschau und Bestätigungen werden serverseitig erzwungen. Dialog-Zuweisungen und das Umbenennen von Bezirk und Gruppe sind bedingte Schreibzugriffe (`If-Match`, PR #599). Der Change `event-list-inline-cell-editing` ist abgeschlossen und archiviert (PR #599). **Bewusst Folgearbeit:** bedingte Schreibzugriffe für den Gemeinde-Dialog, die Aktiv-Schalter von Erinnerungen und Event-Hooks sowie das Dienst-Panel. Notizen, Benutzerverknüpfung, Listensichtbarkeit und Dienstende bleiben bewusst im Dialog |

**Reihenfolge:** wiederkehrende Termine, organisatorische Aufgaben und Inline-Editing sind umgesetzt (siehe Status). Das ist keine beschlossene Release-Zusage.

## Technische Nacharbeiten

| Thema | Offenes Issue | Geplanter Schwerpunkt |
| --- | --- | --- |
| OIDC und Datenschutz | [#471](https://github.com/stritti/nak-district-planner/issues/471) | **Geschlossen, in `main`:** Opaque-Token-Bindung, JWKS-Drosselung (auch ohne Cache), keine Provider-Details oder E-Mail-Adressen in Antworten und Logs, gehashte Export-Tokens (Einzelissues #581, #582, #583), OpenSpec `oidc-authentication` abgeglichen (PR #596); Release-PR #592 offen |
| Kalendersynchronisation | [#470](https://github.com/stritti/nak-district-planner/issues/470) | **In `main` integriert:** PR #568 gemergt; OpenSpec-Change `sync-reliability` archiviert; in Release 1.1.0 enthalten |
| Produktivbetrieb | [#472](https://github.com/stritti/nak-district-planner/issues/472) | **In `main` integriert:** PR #574 gemergt; OpenSpec-Change archiviert, in Release 1.1.0 enthalten; GitGuardian-Incident 36714356 extern zu klären |
| Architektur | [#474](https://github.com/stritti/nak-district-planner/issues/474) | **In `main` integriert:** PR #573 am 13. Oktober gemergt; OpenSpec-Change `refactor-issue-474` archiviert; Codecov-Upload benötigt weiterhin `CODECOV_TOKEN` |
| Berechtigungen und Serien | [#503](https://github.com/stritti/nak-district-planner/issues/503) | **In `main` integriert:** PR #571 gemergt; Regressionen für verschobene Serien ergänzt; in Release 1.1.0 enthalten |
| Matrix- und Kalender-Folgearbeiten | [#584](https://github.com/stritti/nak-district-planner/issues/584), [#585](https://github.com/stritti/nak-district-planner/issues/585) | **Geschlossen:** Lifecycle-Review-Flags in Matrix-Zellen; verteilte Bezirksslots in persönlichen Kalendern |

Alle oben genannten Issues sind geschlossen; Integration in `main` bedeutet nicht automatisch Veröffentlichung, veröffentlicht ist bisher nur v1.1.0. Diese Themen sind **Folgearbeiten nach v1.0** und nicht rückwirkend Blocker des veröffentlichten Releases. Aktuelle Änderungen siehe [offene Issues](https://github.com/stritti/nak-district-planner/issues?q=is%3Aissue%20is%3Aopen), [PRs](https://github.com/stritti/nak-district-planner/pulls) und [Releases](https://github.com/stritti/nak-district-planner/releases).

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
