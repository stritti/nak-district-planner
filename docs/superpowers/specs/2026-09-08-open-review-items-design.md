# Design: Offene Findings aus PR #208

## Ziel

Die noch offenen Punkte aus dem Code-Review #208 werden als kleine, unabhängig
reviewbare Pull Requests umgesetzt. Jeder PR erhält eigene Tests und eine
präzise Statusaktualisierung in den Review-Dokumenten.

## PR-Schnitt und Reihenfolge

1. **B-4 — Auth-Coverage:** fehlende JWT-Claims-Fälle ergänzen und die
   `app/adapters/auth`-Coverage auf mindestens 90 % bringen.
2. **B-3 — Produktentscheidung:** die Entscheidung zum Review-Workflow für
   externe Sync-Events dokumentieren. Keine Implementierung von
   `ExternalEventCandidate` ohne Freigabe.
3. **PR-5 — Rate-Limiter-Observability:** Fail-open-Zähler und betriebliche
   Dokumentation/Alert-Hinweis ergänzen.
4. **PR-7 — Pre-Go-Live-Verifikation:** Health-Check und Audit-Log-Pfade mit
   Tests bzw. reproduzierbaren Verifikationsschritten absichern.
5. **PR-8 — Sync-Refactoring:** Connector-Registry und typisiertes
   `SyncResult` einführen, ohne fachliche Verhaltensänderung.
6. **PR-6 — Dokumentation:** veraltete Sicherheits- und Statusdokumente nach
   den technischen Änderungen bereinigen.
7. **PR-9 — Frontend-Aufteilung:** fünf kleine, verhaltensneutrale PRs für die
   größten Views; zunächst MatrixView, danach Leaders, Events, Integrations
   und Districts.
8. **PR-11 — optional:** `EncryptedJSON` als SQLAlchemy-TypeDecorator nur
   umsetzen, wenn die bestehenden Tests die Transparenz beim Lesen/Schreiben
   abdecken und kein Sicherheitsrisiko durch die Migration entsteht.

## Abhängigkeiten

- B-4, PR-5 und PR-7 sind unabhängig und können parallel entwickelt werden.
- B-3 ist eine Entscheidungs-/Dokumentations-PR und blockiert keine technische
  Umsetzung.
- PR-6 folgt PR-5/PR-7, damit die Dokumentation den tatsächlich gemergten
  Zustand beschreibt.
- PR-8 ist unabhängig, sollte aber vor PR-6 abgeschlossen sein.
- PR-9 und PR-11 sind nachrangig und ändern keine Sicherheitsentscheidung.

## Qualitäts- und Sicherheitsregeln

- Keine Secrets oder Test-Credentials committen.
- Keine fachliche Verhaltensänderung in PR-8, PR-9 oder PR-11.
- Sicherheitsrelevante Änderungen erhalten positive und negative Tests.
- Jeder PR wird einzeln geprüft, committed, gepusht und mit einer eigenen
  Beschreibung eröffnet.
- Die Arbeitskopie mit bestehenden, nicht zugehörigen Änderungen wird nicht
  überschrieben; PRs arbeiten in separaten Worktrees/Branches.

## Erfolgskriterien

- B-4 erreicht nachweisbar mindestens 90 % JWT-Claims-Coverage.
- Fail-open, Health-Check und Audit-Logging sind operational dokumentiert und
  testbar.
- Sync-Refactoring besteht die bisherigen Sync-Tests unverändert.
- Review-Dokumente behaupten nur noch Zustände, die im jeweiligen Branch oder
  in einem referenzierten, gemergten Folge-PR nachweisbar sind.
- Für jeden offenen Punkt existiert entweder ein eigener PR oder eine explizite
  Produktentscheidung.
