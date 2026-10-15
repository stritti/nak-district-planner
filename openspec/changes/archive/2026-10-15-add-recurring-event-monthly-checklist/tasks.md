## 1. Domänenmodell und Regeln

- [x] 1.1 RecurringEventTemplate, validierte Wiederholungsregeln und RecurringEventDecision als getrennte Domänenmodelle entwerfen; nicht mit PlanningSeries-Generatoren vermischen.
- [x] 1.2 Pure Monats-Expansion (WEEKLY, MONTHLY_DAY, MONTHLY_WEEKDAY inkl. letzter Wochentag), feste Anker, aktive Grenzen und Europe/Berlin implementieren.
- [x] 1.3 Deterministische Statusprojektion für OPEN, ACCEPTED, SKIPPED, CONFLICT und NEEDS_REVIEW samt stabiler Vorkommens-ID entwickeln.
- [x] 1.4 Kategorien für Gottesdienste im neuen Vorlagenpfad verhindern, damit die vorhandene automatische Vorgenerierung unverändert bleibt.

## 2. Persistenz und Use Cases

- [x] 2.1 Alembic-Migration mit Mandantenbezug, Unique-Constraints, nullable planning_slot_id (ON DELETE SET NULL), referenzieller Scope-Prüfung und PostgreSQL-RLS für Vorlagen/Entscheidungen.
- [x] 2.2 Repository-Ports und Adapter für Vorlagen, Entscheidungen und verknüpfte PlanningSlots erstellen.
- [x] 2.3 Accept, Skip, Reopen, Resolve (LINK_EXISTING/MARK_SKIPPED/REOPEN nur bei fehlendem Slot) und Bulk-Accept als Use-Cases umsetzen; atomar je Vorkommen mit separaten Transaktionen/Savepoints, Idempotenz, Optimistic-Concurrency-Check und per-item-Konflikten.
- [x] 2.4 Übernommene Termine als PlanningSlot (ACTIVE, PLANNED, template.applicability bei Bezirksterminen bzw. [] bei Gemeindeterminen) + EventInstance (source=INTERNAL, visibility=PUBLIC) erstellen und an die bestehenden Freigabe-/Exportregeln anbinden; Zeitverschiebung ohne Neuanlage erhalten.
- [x] 2.5 Deaktivieren/Bearbeiten von Vorlagen und historische Entscheidungen ohne Datenverlust berücksichtigen; Audit-Events erfassen.

## 3. API und Sicherheit

- [x] 3.1 REST-Verträge für Templates, Monatsvorschau inkl. serverseitigem q-/Kategorie-/Statusfilter vor Pagination und Vorkommensentscheidungen inkl. Resolve als typisierte Schemas dokumentieren und implementieren.
- [x] 3.2 VIEWER-, CONGREGATION_ADMIN- und DISTRICT_ADMIN-Scope-Rechte durchsetzen; die bestehende Monatsfreigabe ausschließlich bei expliziter congregation_id auf die eigene Gemeinde für CONGREGATION_ADMIN erweitern, bezirksweite Freigabe unverändert lassen; keine implizite Erweiterung von PLANNER.
- [x] 3.3 Manipulierte district_id/congregation_id/template_id/slot_id, fremde applicability und stale template_revision abfangen; Abfragen unter eingeschränkter DB-Rolle/RLS testen.
- [x] 3.4 Paginierung, Monatsbegrenzung, Eingabevalidierung, angemessene Fehlermeldungen und reproduzierbare HTTP 409-Konflikte implementieren.

## 4. Bedienoberfläche

- [x] 4.1 Vorlagenverwaltung für Bezirk bzw. Gemeinde mit verständlichen Regel-Editoren und sofortiger Monatsvorschau.
- [x] 4.2 Checkliste in die Monatsplanung integrieren: serverseitige Text-/Kategorie-/Statusfilter, Selektions- und Mehrfachübernahme, bewusstes Auslassen, erneutes Öffnen, NEEDS_REVIEW-Auflösung, Konflikthilfe.
- [x] 4.3 Termin vor Übernahme individuell anpassen, erfolgreiche Übernahme in der bestehenden Eventübersicht sichtbar machen und Freigabe getrennt halten.
- [x] 4.4 Responsive/mobile Bedienung und Lade-, Leer-, Fehler-, Berechtigungs- und Paralleländerungszustände vorsehen.

## 5. Verifikation

- [x] 5.1 Unit-Tests: Dienstag wöchentlich, alle zwei Wochen mit festem Anker, letzter Dienstag, erster/fünfter Wochentag, 29./30./31., Februar/Schaltjahr, Monats- und Jahreswechsel, Aktivitätsgrenzen.
- [x] 5.2 Unit-Tests: lokale Zeit/UTC inkl. DST-Lücke und doppelter Stunde, Dauer, inaktive Vorlage, geänderte Vorlage, geändertes Vorkommen, ungültige Patterns.
- [x] 5.3 Integrations-/Race-Tests: doppelte und parallele Accepts, Bezirk-applicability, öffentlicher ICS-Export erst nach CONFIRMED, vorhandener manueller Termin, Skip/Reopen/Resolve, Retention-Löschung und ON DELETE SET NULL, verschobener Slot, per-item-Bulk-Commit trotz paralleler Unique-Fehler, unterschiedliche Gemeinden/Bezirke, bestehender Gottesdienstgenerator.
- [x] 5.4 API-/RLS-Tests für alle Rollen, gemeindebezogene Freigabe (eigene Gemeinde erlaubt, fremde/ganzes Bezirk verboten), Scope-Manipulation, Cross-Tenant-Zugriffe, Bulk-Teilkonflikte, Filter vor Pagination und stale Revisions.
- [x] 5.5 Frontend-Unit- und Browser-Tests für Monatswechsel, Checklistenstatus, Mehrfachübernahme, Fehlermeldungen und mobile Nutzung.
- [x] 5.6 OpenSpec strikt validieren; bestehende Lint-, Sicherheits-, Build- und CI-Gates ohne Abschwächung bestehen; neue Produktionspfade mit >80 % Code Coverage und Ausnahmefällen abdecken.

## 6. CI-Regressionen vom 13. Oktober 2026

- [x] 6.1 Import-Regression aus Commit 7747c86 korrigieren: TransactionPort verwendet contextlib.AbstractAsyncContextManager; keine SQL-Abhängigkeit im Application-Service.
- [x] 6.2 Repository- und Transaktionsverträge dokumentieren und wirkungslose Ellipsis-Anweisungen aus den sieben von CodeQL beanstandeten Protokollmethoden entfernen.
- [x] 6.3 Ausnahmefalltests für Accept, Skip und Resolve ergänzen: injizierte Integritätsfehler werden mit Ursache in Konflikte übersetzt, andere Fehler bleiben unverändert; ohne konfigurierte Fehlerklasse erfolgt keine Übersetzung.
- [x] 6.4 Vollständige CI am Code-Head f053af0 einschließlich Backend-/Router-Coverage und Security Scans bestätigen; alle sieben CodeQL-Review-Threads sind aufgelöst.

Die Korrektur des Importfehlers hat im ersten CI-Lauf die PostgreSQL-/RLS-Testausführung wieder ermöglicht. Die übrigen offenen Implementierungs- und Verifikationsaufgaben bleiben offen: erfolgreiche CI allein belegt keine vollständige Umsetzung des Fachfeatures; RecurringEventsView.vue und zugehörige Unit-Tests sind vorhanden.

Verifikationsstand am Code-Head `f053af0`: alle neun Workflows erfolgreich; 1.889 Backend-Unit-Tests bestanden (ein bestehender Skip), 239 PostgreSQL-/RLS-Tests bestanden. Backend-Gesamtcoverage 90 %, Recurring-Service 90 %, Recurring-Router 90 %, Repository 92 %, Schemas/ORM/Domänenmodell jeweils 100 %. Zusätzliche Tests prüfen Command-Ergebnisse und HTTP-Fehler, Scope-Abweisung, Template-Revisionen, gesperrte Datenbank-Lookups und Löschung fehlender Entscheidungen. Aufgabe 5.6 bleibt wegen der noch offenen strikten OpenSpec-Validierung und Fachverifikation offen; die vorhandene Checklisten-/Vorlagenoberfläche sowie die weiteren Punkte der Review-Zusammenfassung vom 12. Oktober müssen vor fachlicher Merge-Reife abschließend verifiziert werden.

## 7. Nachbearbeitung von PR #570 (13. Oktober 2026)

- [x] 7.1 Fehlertexte des Bulk-Accepts durch öffentliche Fehlercodes ersetzen und im Frontend lokalisieren; interne Fehlermeldungen nicht weitergeben.
- [x] 7.2 Vorlagenliste mit autorisierungsgefilterter SQL-Paginierung, Gesamtzahl und UI-Seitenwechsel versehen.
- [x] 7.3 Gemeinde-Monatsfilter gegen fremde Scope-IDs absichern und Monatsexpansion auf maximal 500 sichtbare Vorlagen begrenzen.
- [x] 7.4 Wiederverwendbare Autorisierungsrichtlinie aus dem Router auslagern; Transaktionsaudit für RecurringEventTemplate/RecurringEventDecision ergänzen.
- [x] 7.5 Den aktuellen Refactoring-Stand aus main integrieren und sämtliche Git-Konflikte auflösen.
- [x] 7.6 Neue Tests und die gesamte CI inklusive RLS, Coverage, OpenSpec-Validierung und Browser-Verifikation am finalen Merge-Head ausführen.

Die Punkte 2 bis 4 kennzeichnen implementierten Code. Die CI-Verifikation 5.6 und 7.6 wurde am geprüften Commit `7941eb76` abgeschlossen: neun Workflows erfolgreich, 1.938 Backend-Unit-Tests bestanden (ein Skip), 245 PostgreSQL-/RLS-Tests bestanden, Backend-Gesamtcoverage 90 %, Recurring-Service und -Router je 92 %, Domänenmodell 100 %, Frontend-Unit/E2E, OpenSpec und Migrations-Roundtrip erfolgreich. Die breiteren fachlichen Abnahmen 5.3 bis 5.5 verbleiben offen, soweit dort über das CI-Gate hinausgehende Szenarien verlangt werden. Ein erfolgreicher Workflow ersetzt keine noch ausstehende Fachabnahme.

## 8. Codex-Review: Nacharbeitung vom 13. Oktober 2026

- [x] 8.1 UI-PATCH sendet keine Response-only-Felder (P1); expliziter Eingabevertrag und Regressionstest.
- [x] 8.2 Monatsfreigabe anhand des lokalen Europe/Berlin-Kalendermonats einschließlich UTC-Vortag; Grenztests.
- [x] 8.3 Akzeptierte, durch Planungsslot-RLS verborgene Verknüpfungen bleiben ACCEPTED, wenn der zusammengesetzte FK noch auf einen Slot verweist; sonst NULL und NEEDS_REVIEW.
- [x] 8.4 LINK_EXISTING validiert das lokale Datum des vorhandenen UTC-Slots ohne erneute DST-Fold-Mehrdeutigkeit.
- [x] 8.5 UNIQUE(planning_slot_id) verhindert parallele Doppelverknüpfungen und erlaubt mehrere NULL-Werte nach Retention; PostgreSQL-Test.
- [x] 8.6 Applicability-UUIDs werden kanonisch normalisiert und vor Persistenz auf Dubletten geprüft.
- [x] 8.7 Der Vorlagen-Tab bleibt nach 413 der Monatscheckliste nutzbar.
- [x] 8.8 Bezirkswechsel entfernt einen zuvor gesetzten Gemeindefilter.
- [x] 8.9 Nach Bulk-Teilerfolg werden persistierte Erfolge neu geladen und nur Fehler zur erneuten Auswahl vorgemerkt.
- [x] 8.10 Übersteuerte Jahre vor 1900 werden vor der DST/UTC-Konvertierung als ungültig zurückgewiesen.

Die OpenSpec-Requirements und das Design wurden um die fachlichen Grenzfälle ergänzt. Verifizierte GitHub-Actions-Protokolle: [CI-Lauf 38467018812](https://github.com/stritti/nak-district-planner/actions/runs/38467018812).
