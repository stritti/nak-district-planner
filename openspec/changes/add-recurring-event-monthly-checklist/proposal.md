## Why

Viele Gemeinde- und Bezirkstermine finden regelmäßig statt, sind aber nicht in jedem Monat verbindlich: etwa jeden Dienstag um 19:30 Uhr die Chorprobe oder am letzten Dienstag des Monats der Seniorennachmittag. Heute fehlt eine Möglichkeit, solche Termine zentral vorzumerken und sie in der konkreten Monatsplanung einzeln zu übernehmen oder bewusst auszulassen.

Die bereits vorhandene PlanningSeries erzeugt PlanningSlots automatisch für einen mehrmonatigen Horizont und ist primär für Gottesdienste ausgelegt. Für optionale Gemeinde- und Bezirksveranstaltungen braucht es stattdessen eine explizite, nachvollziehbare Monatsentscheidung. Eine automatisch erzeugte Serie wäre hier fachlich falsch.

## What Changes

- Wiederverwendbare Terminvorlagen mit Geltungsbereich Gemeinde oder Bezirk, Titel, Kategorie, Beschreibung, Dauer, lokaler Uhrzeit, optionaler Laufzeit und Wiederholungsregel.
- Regeln für wöchentliche Wiederholung (auch alle N Wochen), monatliche Kalendertage und n-ten bzw. letzten Wochentag eines Monats.
- Monatsbezogene, nach Gemeinde oder Bezirk filterbare Planungscheckliste: Offen, Übernommen, Ausgelassen sowie Konflikt/Prüfbedarf.
- Einzelne oder mehrere Vorschläge werden bewusst zu regulären PlanningSlots mit EventInstance im Status PLANNED übernommen, nicht sofort veröffentlicht. Übernommene Termine können anschließend wie bisher bearbeitet und freigegeben werden.
- Auslassen ist eine persistierte Entscheidung je Vorlagen-Vorkommen und Kalendermonat. Wiederholte Vorschau bzw. Übernahme darf keine Duplikate erzeugen.
- Prüfung auf bestehende Termine, Rechte, Ausnahmefälle und stabile Verknüpfung bei späteren Terminänderungen.
- Terminvorlagen werden nicht vom täglichen PlanningSeries-Generator und nicht vom Gottesdienst-Entwurfsgenerator verarbeitet.

## Capabilities

### New Capabilities

- recurring-event-monthly-planning: Vorlagenverwaltung, deterministische lokale Wiederholungsberechnung, monatsbezogene Checkliste und explizite Übernahme/Verwerfung in den bestehenden Planungsprozess.

### Modified Capabilities

- Keine bestehenden Requirements werden aufgehoben oder stillschweigend geändert. Die neue Capability integriert sich in planning-model, planning-visibility, rbac-model und tenant-isolation, ohne deren bisherige Automatismen oder Rechte zu erweitern.

## Impact

- Backend: neues Vorlagen- und Entscheidungsmodell, Migration mit Mandantenschutz/RLS, dedizierter Application-Service und API-Endpunkte für Vorlagen und Monatscheckliste.
- Frontend: Vorlagenverwaltung sowie Checklistenbereich in der Monatsplanung, einschließlich Lade-, Konflikt- und Fehlerzuständen.
- Bestehende Events-API, EventInstance, PlanningSlot, Monatsfreigabe, Kalenderansichten und ICS-Export werden wiederverwendet.
- Qualitätsanforderung für die spätere Umsetzung: gezielte Unit-, Integrations- und UI-Tests einschließlich Ausnahmefällen, Code Coverage >80 % und bestehende CI-Gates unverändert.
- Tracking: #557.

## Non-goals

- Keine automatische Veröffentlichung, Einladungen oder Erinnerungen.
- Keine Änderungen an der automatischen Gottesdienst- oder PlanningSeries-Generierung.
- Kein eigener Veranstaltungsort im Event-Datenmodell oder externer RRULE-/Kalender-Synchronisationseditor und kein massenhaftes Vorab-Anlegen für zukünftige Monate.
- Keine Änderung des bestehenden Rollenmodells oder seiner Berechtigungsgrenzen.
