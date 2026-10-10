## ADDED Requirements

### Requirement: Wiederkehrende Terminvorlagen auf Gemeinde- und Bezirksebene

Das System SHALL eine unabhängig von PlanningSeries verwaltete RecurringEventTemplate unterstützen. Jede Vorlage SHALL genau einem Bezirk und optional einer Gemeinde dieses Bezirks zugeordnet sein und Titel, Kategorie (außer Gottesdienst), lokale Startzeit, positive Dauer, optional Beschreibung, verpflichtendes anchor_date, Aktivitätszeitraum, is_active sowie eine validierte Wiederholungsregel besitzen. Bezirkstermine MAY per bestehender applicability-Semantik an Gemeinden verteilt werden; Gemeindetermine SHALL keine applicability besitzen.

#### Scenario: Wöchentliche Chorprobe einer Gemeinde
- **GIVEN** eine aktive Vorlage Chorprobe für Gemeinde A, jeden Dienstag 19:30 Uhr für 90 Minuten
- **WHEN** November 2026 als Planungsmonat geöffnet wird
- **THEN** erscheinen die Dienstage 03., 10., 17. und 24.11. um 19:30 Uhr als offene Vorschläge für A
- **AND** Gemeinde B erhält keine dieser Vorschläge

#### Scenario: Monatlicher letzter Dienstag auf Bezirksebene
- **GIVEN** eine aktive Bezirksvorlage Seniorennachmittag am letzten Dienstag jedes Monats, 14:30 Uhr
- **WHEN** die Checkliste für November 2026 geöffnet wird
- **THEN** erscheint der 24.11.2026 um 14:30 Uhr genau einmal
- **AND** der Vorschlag wird als Bezirkstermin mit der festgelegten applicability geführt

#### Scenario: Ungültige Scope-Kombination
- **WHEN** ein Gemeindetemplate zugleich eine Bezirksverteilung oder die Gemeinde eines fremden Bezirks enthält
- **THEN** wird die Änderung zurückgewiesen
- **AND** keine Vorlage wird verändert

#### Scenario: Gottesdienstvorlage
- **WHEN** eine wiederkehrende Vorlage mit Kategorie Gottesdienst angelegt wird
- **THEN** lehnt das System diesen separaten Generatorpfad ab
- **AND** die vorhandenen Gottesdienst- und PlanningSeries-Generatoren bleiben unverändert

### Requirement: Kalenderfeste, deterministische Wiederholungsregeln

Das System SHALL WEEKLY (ein oder mehrere ISO-Wochentage mit ganzzahligem Wochenintervall), MONTHLY_DAY (Tag 1..31 mit Monatsintervall) und MONTHLY_WEEKDAY (Wochentag mit 1. bis 5. oder letztem Vorkommen, Monatsintervall) anbieten. Ein verpflichtendes, stabiles anchor_date SHALL die Intervallphase bestimmen; die Berechnung SHALL unabhängig vom angefragten Fenster sein und SHALL die inklusiven Aktivitätsgrenzen einhalten.

#### Scenario: Letzter Dienstag statt vierter Dienstag
- **GIVEN** eine Vorlage für den letzten Dienstag eines Monats
- **WHEN** ein Monat mit fünf Dienstagen geplant wird
- **THEN** entsteht ein Vorschlag für den fünften und nicht den vierten Dienstag

#### Scenario: Fehlender fünfter Wochentag
- **GIVEN** eine Vorlage für den fünften Dienstag
- **WHEN** der ausgewählte Monat nur vier Dienstage besitzt
- **THEN** entsteht in diesem Monat kein Vorschlag

#### Scenario: Fehlender Kalendertag
- **GIVEN** eine Vorlage für den 31. Tag jedes Monats
- **WHEN** Februar 2027 geöffnet wird
- **THEN** entsteht kein Vorkommen und kein stillschweigend verschobener Februartermin

#### Scenario: Zweiwöchentlicher Termin mit Anker
- **GIVEN** eine Vorlage jeden zweiten Dienstag mit Ankerwoche ab 03.11.2026
- **WHEN** November einzeln oder November und Dezember zusammen berechnet werden
- **THEN** stimmen die Novembertermine 03.11. und 17.11. in beiden Berechnungen überein

#### Scenario: Sommerzeit
- **GIVEN** eine Vorlage um 19:30 Uhr Europe/Berlin
- **WHEN** ein Vorkommen im Winter und eines im Sommer übernommen wird
- **THEN** sind beide lokal um 19:30 Uhr geplant
- **AND** die UTC-Zeitpunkte berücksichtigen den jeweiligen Offset

#### Scenario: Nicht vorhandene oder doppeldeutige lokale Zeit
- **WHEN** ein Vorschlag auf eine lokale Uhrzeit in einer DST-Lücke oder Überlappung fällt
- **THEN** wird das Vorkommen als prüfbedürftig markiert
- **AND** kein UTC-Zeitpunkt ohne explizite Entscheidung stillschweigend angenommen

### Requirement: Monatliche To-do-Liste vor Anlage konkreter Termine

Das System SHALL für einen angefragten Kalendermonat eine nach Datum und Uhrzeit geordnete Checkliste berechnen, deren offene Einträge zunächst keine PlanningSlots oder EventInstances sind. Die Liste SHALL serverseitig vor Pagination nach Suchtext (Titel/Beschreibung), Kategorie, Entscheidungsstatus und Organisationseinheit filterbar und mit den Zuständen OPEN, ACCEPTED, SKIPPED, CONFLICT und NEEDS_REVIEW darstellbar sein. Die Auswahl und jede Änderung SHALL serverseitig gegen den aktuellen Bezirk und die Vorlage geprüft werden.

#### Scenario: Filter vor Pagination
- **GIVEN** mehr Vorschläge als auf eine Ergebnis-Seite passen
- **WHEN** die Checkliste mit q=Chor, category=Musik und status=OPEN angefragt wird
- **THEN** filtert der Server die gesamte Monatsmenge vor der Seitenauswahl
- **AND** total und Pagination zählen nur passende Vorschläge

#### Scenario: Neue Monatsplanung
- **GIVEN** eine wöchentliche und eine monatliche aktive Vorlage
- **WHEN** ein berechtigter Benutzer den kommenden Monat öffnet
- **THEN** sieht er alle passenden Vorschläge als OPEN
- **AND** es sind allein durch die Vorschau keine Termine erzeugt oder veröffentlicht

#### Scenario: Bewusst ausgelassene Chorprobe
- **WHEN** ein berechtigter Benutzer die Chorprobe am 24.11. als SKIPPED markiert und die Seite neu lädt
- **THEN** bleibt dieser Vorschlag als SKIPPED sichtbar
- **AND** für diese Entscheidung wird kein PlanningSlot angelegt

#### Scenario: Ausgelassenen Termin wieder öffnen
- **GIVEN** ein Vorkommen ist SKIPPED
- **WHEN** ein Berechtigter die Entscheidung ausdrücklich zurücknimmt
- **THEN** wird es erneut OPEN, ohne andere Termine zu verändern

#### Scenario: Vorlagenänderung nach Bearbeitung
- **GIVEN** ein Vorkommen wurde übernommen oder übersprungen
- **WHEN** eine Vorlage geändert oder deaktiviert wird
- **THEN** bleiben die bereits getroffenen Entscheidungen und zugeordneten Termine unverändert
- **AND** zukünftige unbearbeitete Vorschläge werden anhand der aktuellen gültigen Vorlage berechnet

### Requirement: Explizite, idempotente Übernahme in die Event-Planung

Das System SHALL einen ausgewählten Vorschlag nur nach expliziter, berechtigter Bestätigung als PlanningSlot und EventInstance anlegen. Der Slot SHALL ACTIVE mit approval_status PLANNED sein und zunächst keine ServiceAssignment besitzen. Bei Bezirksterminen SHALL der neue Slot die zum Übernahmezeitpunkt validierte template.applicability vollständig und kanonisch übernehmen; bei Gemeindeterminen SHALL slot.applicability leer sein. Die EventInstance SHALL source=INTERNAL und visibility=PUBLIC erhalten. Die PUBLIC-Einstellung SHALL den Entwurf nicht veröffentlichen: Öffentliche Feeds zeigen weiterhin nur CONFIRMED-Slots, und Bezirksverteilung bleibt an ACTIVE und CONFIRMED gebunden. Die Übernahme SHALL die vorliegende Template-Revision prüfen und je (template_id, occurrence_local_date) genau eine persistierte Entscheidung ACCEPTED mit Verweis auf den konkreten Slot atomar speichern. Wiederholte oder parallele Aufrufe SHALL keine doppelten Termine anlegen.

#### Scenario: Übernahme ohne Veröffentlichung
- **WHEN** eine offene Chorprobe übernommen wird
- **THEN** erscheint sie als regulärer Termin mit approval_status PLANNED
- **AND** `EventInstance.visibility=PUBLIC` ist bereits gesetzt, aber PUBLIC-ICS-Feeds und bezirksweite Gemeindeverteilung bleiben bis CONFIRMED gesperrt

#### Scenario: Bezirkstermin übernimmt die Gemeindeverteilung
- **GIVEN** eine Bezirksterminvorlage mit applicability=["all"]
- **WHEN** ein Vorkommen angenommen und danach freigegeben wird
- **THEN** speichert der erzeugte PlanningSlot applicability=["all"] unverändert
- **AND** der Termin ist nach CONFIRMED für alle Gemeinden des Bezirks sichtbar, vorher nicht

#### Scenario: Öffentlicher Export nach Freigabe
- **GIVEN** eine übernommene Chorprobe mit EventInstance.visibility=PUBLIC
- **WHEN** deren Slot zunächst PLANNED und später CONFIRMED ist
- **THEN** fehlt sie im PUBLIC-ICS-Feed vor der Freigabe
- **AND** sie erscheint danach gemäß den geltenden Sichtbarkeitsregeln

#### Scenario: Doppelte Bestätigung
- **WHEN** dasselbe Vorkommen zweimal oder gleichzeitig angenommen wird
- **THEN** entsteht höchstens ein PlanningSlot und eine ACCEPTED-Entscheidung
- **AND** weitere Aufrufe liefern den vorhandenen Termin oder einen deterministischen Konflikt

#### Scenario: Bestehender manueller Termin
- **GIVEN** eine Gemeinde hat bereits einen aktiven Slot zur vorgeschlagenen Startzeit
- **WHEN** derselbe Vorschlag übernommen werden soll
- **THEN** erhält der Benutzer einen Konflikt statt einer automatischen Überschreibung
- **AND** eine eventuell beabsichtigte Zuordnung zum vorhandenen Slot erfordert eine ausdrückliche Aktion

#### Scenario: Auswahl mehrerer Vorschläge
- **WHEN** drei Vorschläge gemeinsam angenommen werden und einer mit einem vorhandenen Termin kollidiert
- **THEN** erhält jeder Vorschlag ein eigenes nachvollziehbares Ergebnis
- **AND** jedes Vorkommen wird in einer eigenen Transaktion oder durch isolierte Savepoints verarbeitet
- **AND** erfolgreiche Übernahmen bleiben auch nach konkurrierenden Constraint-Konflikten anderer Einträge gespeichert, während der Konflikt keine zusätzlichen Slots erzeugt

#### Scenario: Veraltete Vorschau
- **WHEN** ein Benutzer ein Vorkommen mit überholter template_revision bestätigen will
- **THEN** wird die Bestätigung mit HTTP 409 abgelehnt
- **AND** keine veraltete Uhrzeit wird angelegt

### Requirement: Dauerhafte Zuordnung und bewusste Abweichungen

Das System SHALL die Identität eines vorgeschlagenen Vorkommens durch Vorlagen-ID und ursprünglich lokal berechnetes Datum erhalten, unabhängig von späteren Verschiebungen eines übernommenen Termins. Ein gelöschter referenzierter Termin SHALL nicht automatisch neu erzeugt werden. Ist eine ACCEPTED-Entscheidung durch Löschung (einschließlich Retention Cleanup) ohne gültigen Slot-Verweis, SHALL die Checkliste NEEDS_REVIEW anzeigen und eine explizite, berechtigte Auflösung durch Zuordnung zu einem passenden existierenden Slot, Markierung als SKIPPED oder erneutes Öffnen anbieten. Erneutes Öffnen SHALL nur zulässig sein, wenn das Vorkommen weiterhin zur aktiven Vorlage passt. Übernommene Slots SHALL ansonsten den bestehenden Bearbeitungs-, Freigabe-, Sichtbarkeits- und Exportregeln folgen.

#### Scenario: Chorprobe verschoben
- **GIVEN** die Chorprobe am 10.11. wurde übernommen
- **WHEN** der konkrete Termin auf den 11.11. verschoben wird
- **THEN** bleibt die Checklistenentscheidung für das ursprüngliche Vorkommen vom 10.11. ACCEPTED
- **AND** beim nächsten Öffnen entsteht keine zweite Chorprobe am 10.11.

#### Scenario: Checklistenentscheidung nach Löschung auflösen
- **GIVEN** eine ACCEPTED-Entscheidung zeigt NEEDS_REVIEW wegen eines gelöschten Slots
- **WHEN** eine berechtigte Person sie explizit einem anderen passenden, noch nicht verknüpften Slot desselben Scopes zuordnet
- **THEN** wird die bestehende Entscheidung atomar auf diesen Slot umgebucht und als ACCEPTED angezeigt
- **AND** der bereits existierende Slot wird nicht überschrieben

#### Scenario: Gelöschten Slot nicht automatisch regenerieren
- **GIVEN** eine ACCEPTED-Entscheidung zeigt NEEDS_REVIEW wegen eines gelöschten Slots
- **WHEN** die Checkliste erneut geöffnet wird
- **THEN** wird kein neuer Termin erzeugt
- **AND** ein ausdrückliches SKIPPED oder REOPEN kann den Zustand auflösen; REOPEN nur für aktuell gültige Vorkommen

#### Scenario: Konkreter Termin endgültig gelöscht
- **GIVEN** ein übernommener Slot ist nicht mehr vorhanden
- **WHEN** die Monatscheckliste geladen wird
- **THEN** erscheint das Vorkommen als NEEDS_REVIEW
- **AND** es wird weder automatisch neu erstellt noch ungefragt als OPEN behandelt

### Requirement: Organisationsrechte und Mandantenschutz

Das System SHALL die bestehenden Rollen und Scope-Grenzen nutzen: VIEWER dürfen nur berechtigte Vorlagen und Checklisten lesen; DISTRICT_ADMIN dürfen Vorlagen und Entscheidungen des Bezirks ändern; CONGREGATION_ADMIN dürfen dies nur für ihre Gemeinde. Die bestehende Monatsfreigabe SHALL für CONGREGATION_ADMIN mit expliziter congregation_id die Slots genau ihrer Gemeinde bestätigen können; ohne congregation_id bleibt für die bezirksweite Freigabe mindestens die bisherige Bezirks-PLANNER-Berechtigung erforderlich. Eine eigenständige PLANNER-Rolle SHALL dadurch keine bislang fehlenden Event-Erstellrechte erhalten. RLS und API-Guards SHALL fremde Bezirke, Gemeinden und Slot-Verknüpfungen schützen.

#### Scenario: Gemeinde A darf Gemeinde B nicht verändern
- **GIVEN** ein Benutzer ist nur CONGREGATION_ADMIN für Gemeinde A
- **WHEN** er ein Template oder Vorkommen von Gemeinde B ändern möchte
- **THEN** wird die Änderung mit HTTP 403 abgelehnt und es erfolgt keine Datenänderung

#### Scenario: Fremder Bezirk in URL oder Payload
- **WHEN** Template, Scope, Verteilung oder Slot-Referenz einem anderen Bezirk zugehört
- **THEN** verweigert API und Datenbank-RLS den unzulässigen Zugriff
- **AND** keine fremden Vorlagen-, Entscheidungs- oder Slot-Daten werden offengelegt

#### Scenario: Gemeindeadministrator bestätigt nur die eigene Gemeinde
- **GIVEN** ein Benutzer besitzt ausschließlich CONGREGATION_ADMIN für Gemeinde A
- **WHEN** er die Monatsfreigabe mit congregation_id=A anfordert
- **THEN** werden nur die Slots von Gemeinde A bestätigt
- **AND** kein Bezirks- oder Gemeinde-B-Slot wird freigegeben

#### Scenario: Gemeindeadministrator darf keine Bezirksfreigabe auslösen
- **GIVEN** ein Benutzer besitzt ausschließlich CONGREGATION_ADMIN für Gemeinde A
- **WHEN** er die Monatsfreigabe ohne congregation_id oder für Gemeinde B anfordert
- **THEN** antwortet der Server mit HTTP 403, ohne Slots zu verändern

#### Scenario: Unberechtigte Checklisten-Übernahme
- **WHEN** ein VIEWER oder ein PLANNER ohne Event-Erstellberechtigung einen Vorschlag annimmt oder auslässt
- **THEN** antwortet die API mit HTTP 403
- **AND** der Monatszustand bleibt unverändert
