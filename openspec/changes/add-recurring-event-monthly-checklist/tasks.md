## 1. Domänenmodell und Regeln

- [ ] 1.1 RecurringEventTemplate, validierte Wiederholungsregeln und RecurringEventDecision als getrennte Domänenmodelle entwerfen; nicht mit PlanningSeries-Generatoren vermischen.
- [ ] 1.2 Pure Monats-Expansion (WEEKLY, MONTHLY_DAY, MONTHLY_WEEKDAY inkl. letzter Wochentag), feste Anker, aktive Grenzen und Europe/Berlin implementieren.
- [ ] 1.3 Deterministische Statusprojektion für OPEN, ACCEPTED, SKIPPED, CONFLICT und NEEDS_REVIEW samt stabiler Vorkommens-ID entwickeln.
- [ ] 1.4 Kategorien für Gottesdienste im neuen Vorlagenpfad verhindern, damit die vorhandene automatische Vorgenerierung unverändert bleibt.

## 2. Persistenz und Use Cases

- [ ] 2.1 Alembic-Migration mit Mandantenbezug, Unique-Constraints, nullable planning_slot_id (ON DELETE SET NULL), referenzieller Scope-Prüfung und PostgreSQL-RLS für Vorlagen/Entscheidungen.
- [ ] 2.2 Repository-Ports und Adapter für Vorlagen, Entscheidungen und verknüpfte PlanningSlots erstellen.
- [ ] 2.3 Accept, Skip, Reopen, Resolve (LINK_EXISTING/MARK_SKIPPED/REOPEN nur bei fehlendem Slot) und Bulk-Accept als Use-Cases umsetzen; atomar je Vorkommen mit separaten Transaktionen/Savepoints, Idempotenz, Optimistic-Concurrency-Check und per-item-Konflikten.
- [ ] 2.4 Übernommene Termine als PlanningSlot (ACTIVE, PLANNED, template.applicability bei Bezirksterminen bzw. [] bei Gemeindeterminen) + EventInstance (source=INTERNAL, visibility=PUBLIC) erstellen und an die bestehenden Freigabe-/Exportregeln anbinden; Zeitverschiebung ohne Neuanlage erhalten.
- [ ] 2.5 Deaktivieren/Bearbeiten von Vorlagen und historische Entscheidungen ohne Datenverlust berücksichtigen; Audit-Events erfassen.

## 3. API und Sicherheit

- [ ] 3.1 REST-Verträge für Templates, Monatsvorschau inkl. serverseitigem q-/Kategorie-/Statusfilter vor Pagination und Vorkommensentscheidungen inkl. Resolve als typisierte Schemas dokumentieren und implementieren.
- [ ] 3.2 VIEWER-, CONGREGATION_ADMIN- und DISTRICT_ADMIN-Scope-Rechte durchsetzen; die bestehende Monatsfreigabe ausschließlich bei expliziter congregation_id auf die eigene Gemeinde für CONGREGATION_ADMIN erweitern, bezirksweite Freigabe unverändert lassen; keine implizite Erweiterung von PLANNER.
- [ ] 3.3 Manipulierte district_id/congregation_id/template_id/slot_id, fremde applicability und stale template_revision abfangen; Abfragen unter eingeschränkter DB-Rolle/RLS testen.
- [ ] 3.4 Paginierung, Monatsbegrenzung, Eingabevalidierung, angemessene Fehlermeldungen und reproduzierbare HTTP 409-Konflikte implementieren.

## 4. Bedienoberfläche

- [ ] 4.1 Vorlagenverwaltung für Bezirk bzw. Gemeinde mit verständlichen Regel-Editoren und sofortiger Monatsvorschau.
- [ ] 4.2 Checkliste in die Monatsplanung integrieren: serverseitige Text-/Kategorie-/Statusfilter, Selektions- und Mehrfachübernahme, bewusstes Auslassen, erneutes Öffnen, NEEDS_REVIEW-Auflösung, Konflikthilfe.
- [ ] 4.3 Termin vor Übernahme individuell anpassen, erfolgreiche Übernahme in der bestehenden Eventübersicht sichtbar machen und Freigabe getrennt halten.
- [ ] 4.4 Responsive/mobile Bedienung und Lade-, Leer-, Fehler-, Berechtigungs- und Paralleländerungszustände vorsehen.

## 5. Verifikation

- [ ] 5.1 Unit-Tests: Dienstag wöchentlich, alle zwei Wochen mit festem Anker, letzter Dienstag, erster/fünfter Wochentag, 29./30./31., Februar/Schaltjahr, Monats- und Jahreswechsel, Aktivitätsgrenzen.
- [ ] 5.2 Unit-Tests: lokale Zeit/UTC inkl. DST-Lücke und doppelter Stunde, Dauer, inaktive Vorlage, geänderte Vorlage, geändertes Vorkommen, ungültige Patterns.
- [ ] 5.3 Integrations-/Race-Tests: doppelte und parallele Accepts, Bezirk-applicability, öffentlicher ICS-Export erst nach CONFIRMED, vorhandener manueller Termin, Skip/Reopen/Resolve, Retention-Löschung und ON DELETE SET NULL, verschobener Slot, per-item-Bulk-Commit trotz paralleler Unique-Fehler, unterschiedliche Gemeinden/Bezirke, bestehender Gottesdienstgenerator.
- [ ] 5.4 API-/RLS-Tests für alle Rollen, gemeindebezogene Freigabe (eigene Gemeinde erlaubt, fremde/ganzes Bezirk verboten), Scope-Manipulation, Cross-Tenant-Zugriffe, Bulk-Teilkonflikte, Filter vor Pagination und stale Revisions.
- [ ] 5.5 Frontend-Unit- und Browser-Tests für Monatswechsel, Checklistenstatus, Mehrfachübernahme, Fehlermeldungen und mobile Nutzung.
- [ ] 5.6 OpenSpec strikt validieren; bestehende Lint-, Sicherheits-, Build- und CI-Gates ohne Abschwächung bestehen; neue Produktionspfade mit >80 % Code Coverage und Ausnahmefällen abdecken.
