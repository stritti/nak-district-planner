## Context

Das System kennt PlanningSeries (wiederkehrende, automatisch generierte Planungsslots), PlanningSlot (Planung) und EventInstance (konkreter Termin). PlanningSeriesSlotGenerationService erzeugt bereits ohne Monatsentscheidung Slots für einen mehrmonatigen Zeitraum; ohne Kategorie wird Gottesdienst angenommen. Auch die Gottesdienst-Vorgenerierung läuft automatisch. Beide Pfade sind für unregelmäßig ausfallende Proben, Seniorentermine und sonstige Gemeindeveranstaltungen ungeeignet.

Die Events-API, die bestehenden PLANNED/CONFIRMED-Freigaben, District-applicability und die Mandanten-/Rollenprüfungen sind für übernommene Termine weiter gültig. Die Checkliste ist eine vorgeschaltete Planungsfunktion und kein dritter Kalender.

## Ziele und Architekturentscheidungen

### 1. Eigenständige Vorlage statt weiterer PlanningSeries-Modus

Ein neues Domänenmodell RecurringEventTemplate enthält:
- id, district_id, congregation_id optional (null = Bezirkstermin)
- title, description optional, category (kein Gottesdienst im ersten Ausbauschritt), start_time als lokale Uhrzeit, duration_minutes > 0
- recurrence als validierte, versionierte Regel mit verpflichtendem anchor_date; active_from, active_until optional; is_active; revision / updated_at
- applicability nur bei Bezirksterminen: [] = nur auf Bezirksebene, ["all"] oder eine eindeutige Menge bezirkszugehöriger Gemeinden; niemals bei Gemeindeterminen
- timezone = Europe/Berlin in der ersten Ausbaustufe

Die Vorlage ist keine PlanningSeries und wird nicht von deren Celery-Generatoren bearbeitet. Die Kalenderberechnung kann pure gemeinsame Domänen-Helfer verwenden; bestehende Generator-Interfaces und Gottesdienstkonventionen bleiben unverändert. Gottesdienste werden als Vorlagenkategorie vorerst abgelehnt, damit keine zweite Gottesdienst-Generierung entsteht.

### 2. Typisierte Wiederholungsregeln

Die persistierte Rule definiert genau eine Variante:
- WEEKLY: weekdays (ISO 1=Montag bis 7=Sonntag, eindeutige Liste), interval >=1, Anker anchor_date für Wochenparität
- MONTHLY_DAY: day_of_month von 1 bis 31, interval >=1
- MONTHLY_WEEKDAY: weekday ISO 1..7, ordinal 1..5 oder -1 für letzter, interval >=1

Alle Regeln werden am unveränderlichen anchor_date ausgerichtet; das Auswerten eines isolierten Monats muss dasselbe Ergebnis liefern wie die Betrachtung mehrerer Monate. Fehlt z. B. der 31. oder der fünfte Dienstag, gibt es in diesem Monat kein Vorkommen (kein Verschieben auf Monatsende). Die Grenze active_from/active_until ist inklusiv; inaktive Vorlagen erzeugen keine neuen offenen Vorschläge.

Serverseitig werden alle Vorkommen aus lokalem Datum und Uhrzeit in Europe/Berlin berechnet. Sommer-/Winterzeit wird erst beim Erzeugen des konkreten EventInstance-Zeitpunkts auf UTC aufgelöst. Für nicht existierende oder doppeldeutige lokale Uhrzeiten wird eine explizite Prüfung/Entscheidung verlangt, statt stillschweigend um eine Stunde zu verschieben oder eine UTC-Variante zu wählen. Eine lokale Vorlage um 19:30 bleibt ganzjährig um 19:30 lokal.

### 3. Checkliste als Projektion mit gespeicherten Entscheidungen

GET für ein (Jahr, Monat) berechnet Vorkommen aus aktiven Vorlagen und verknüpft sie mit vorhandenen Entscheidungen. Unbearbeitete Vorschläge liegen nicht als PlanningSlot oder EventInstance in der Datenbank.

RecurringEventDecision:
- id, district_id, template_id, occurrence_local_date (ursprünglicher Soll-Termin als lokales Datum), status (ACCEPTED oder SKIPPED), planning_slot_id optional, created_by, created_at, updated_at
- eindeutiger Schlüssel (template_id, occurrence_local_date), zusätzlich district_id für Tenant/RLS
- ACCEPTED referenziert den entstandenen oder bewusst zugeordneten PlanningSlot; SKIPPED besitzt keine slot_id
- Fremdschlüssel mit geprüfter Bezirkszugehörigkeit; ein nicht mehr existentes Ziel wird als Prüfbedarf angezeigt, nie ungeprüft neu angelegt

Die Darstellung unterscheidet OPEN, ACCEPTED, SKIPPED, CONFLICT und NEEDS_REVIEW. CONFLICT ist ein aus der aktuellen Planungsrealität abgeleiteter Zustand und keine automatische Ablehnung. Entscheidungen bleiben erhalten, wenn eine Vorlage später inaktiv wird oder ihre Regel bearbeitet wird; der Monatsstatus kann weiterhin als historischer Eintrag angezeigt werden. Ein verschobener akzeptierter Termin bleibt dem ursprünglichen Vorkommen zugeordnet, auch wenn er einen anderen Monat erreicht.

Ein übersprungener Vorschlag kann explizit wieder geöffnet werden (Entscheidung entfernen); ACCEPTED wird dagegen durch Bearbeitung oder Stornierung des verknüpften Events verwaltet. Wird ein Event endgültig gelöscht, meldet die Checkliste NEEDS_REVIEW und verlangt eine bewusste Neuzuordnung oder Freigabe der Entscheidung; sie generiert nicht automatisch nach.

### 4. Übernahme, Konflikte und Freigabe

Accept ist eine explizite Transaktion:
1. Zugriff auf Bezirk und ggf. Gemeinde prüfen, Vorlagenrevision und Vorkommen anhand der aktuellen Regel serverseitig validieren.
2. Ein vorhandenes ACCEPTED idempotent mit der verknüpften slot_id beantworten, ein SKIPPED nur nach bewusstem Wiederöffnen übernehmen.
3. Bestehende aktive Terminslots in derselben Gemeinde, am selben Datum und zur selben Uhrzeit auf Konflikte prüfen. District-Level-Termine werden anhand gleicher organisatorischer Zuordnung und identifizierter Vorlage geprüft, ohne parallele Bezirksveranstaltungen pauschal zu verbieten.
4. Bei Kollision CONFLICT ohne Veränderung fremder/manueller Termine zurückgeben. Ein bereits vorhandener passender Termin kann nur durch eine separate, ausdrückliche Zuordnung übernommen werden.
5. PlanningSlot (ACTIVE, approval_status=PLANNED, kein Dienstleiter) und EventInstance (INTERNAL origin, für die spätere Freigabe geeignete Sichtbarkeit und UTC-Zeiten) erzeugen, Decision ACCEPTED mit slot_id speichern; alles atomar.
6. Für gleichzeitige Requests DB-Unique-Constraint auf Entscheidung und die bestehenden aktiven Slot-Constraints nutzen. Eine verletzte Constraint ergibt eine idempotente Antwort oder HTTP 409, niemals einen zusätzlichen Slot.

Der geplante Termin nimmt anschließend unverändert am bestehenden Monatsfreigabe-Workflow teil. Das bloße Abhaken eines Vorschlags bestätigt/veröffentlicht noch keinen Monatsplan. Abweichende Uhrzeit oder Beschreibung können bei der Übernahme gezielt überschrieben werden; die Entscheidung bleibt an der ursprünglichen lokalen Vorkommens-ID hängen. Die Vorlage wird durch einmalige Änderungen nicht verändert.

Ein Bulk-Accept nimmt explizit selektierte Vorkommen und verarbeitet sie mit per-item-Ergebnis, sodass Konflikte für einzelne Termine die anderen nicht stillschweigend verhindern. Für jeden Versuch gilt dasselbe idempotente Verhalten.

### 5. Berechtigungen und Isolation

Die APIs sind unter /api/v1/districts/{district_id}/recurring-event-templates und /api/v1/districts/{district_id}/recurring-event-checklist vorgesehen:
- GET Templates / Checkliste: VIEWER im berechtigten Bereich, ohne Daten aus anderen Gemeinden/Bezirken.
- Bezirkstemplate anlegen/bearbeiten/deaktivieren sowie dessen Vorkommen annehmen/auslassen: DISTRICT_ADMIN des Bezirks.
- Gemeindetemplate und seine Vorkommen ändern: CONGREGATION_ADMIN genau dieser Gemeinde oder DISTRICT_ADMIN des Bezirks.
- PLANNER/VIEWER erhalten dadurch keine zusätzlichen Event-Erstellrechte; nur für ihren Scope autorisierte Benutzer dürfen Entscheidungen ändern.
- Ein Monatsfilter auf eine fremde Gemeinde, ein fremdes template_id, fremde applicability-Einträge oder eine unzulässige slot_id ist serverseitig abzulehnen.
- Neue Tabellen unterliegen PostgreSQL-RLS, Audit-Logging sowie derselben Datenzugriffsstruktur wie die bestehenden Planungstabellen.

Alle Endpunkte sind in Backend-Ports, Domänenservices und API-Adapter getrennt. Zugriffsprüfungen erfolgen vor dem Lesen/Schreiben fremder Daten.

### 6. UI und Fehlerführung

Die Monatsplanung zeigt einen Abschnitt "Wiederkehrende Termine" mit Monatsnavigation, Scope-/Gemeindefilter, Fortschritt offen/übernommen/ausgelassen und Checkboxen bzw. Aktionen zur bewussten Übernahme. Ein Vorschau-Dialog ermöglicht das Ändern einzelner konkreter Termindaten vor dem Bestätigen. Konflikte und ungültige lokale Zeiten haben eine eigene erkennbare Darstellung und blockieren ausschließlich die betroffenen Übernahmen. Eine Statusänderung wird erst nach erfolgreicher API-Antwort angezeigt; API-Fehler lassen die Auswahl bearbeitbar.

Die Vorlagenverwaltung nutzt denselben globalen Bezirkskontext wie die übrigen geschützten Ansichten. Liste und Checkliste sind auf schmalen Bildschirmen nutzbar. Bestehende Eventliste, Monatsansicht und Export erhalten nach Übernahme ihre Daten über die vorhandene API, ohne neue Anzeige-Logik für virtuelle Vorschläge.

### 7. API-Kontrakt (Planungsentwurf)

- GET/POST /api/v1/districts/{district_id}/recurring-event-templates
- PATCH /api/v1/districts/{district_id}/recurring-event-templates/{template_id}
- GET /api/v1/districts/{district_id}/recurring-event-checklist?year=2026&month=11&congregation_id=...
- POST /api/v1/districts/{district_id}/recurring-event-checklist/accept
- POST /api/v1/districts/{district_id}/recurring-event-checklist/skip
- POST /api/v1/districts/{district_id}/recurring-event-checklist/reopen
- POST /api/v1/districts/{district_id}/recurring-event-checklist/bulk-accept

Mutationen identifizieren ein Vorkommen mit template_id, occurrence_local_date und erwarteter template_revision. Bearbeitungsdaten sind streng validiert und auf die eigene Scope beschränkt. Veraltete Vorschauen führen zu HTTP 409 mit aktualisierbarem Konflikthinweis. Die exakten Payload-Typen werden vor der Implementierung im OpenAPI-Kontrakt festgeschrieben.

## Trade-offs und Risiken

- Eigene Terminvorlage statt Erweiterung von PlanningSeries: etwas zusätzlicher Code, aber keine Seiteneffekte auf Gottesdienst-/Langfristgenerator.
- Berechnete statt persistierte OPEN-Einträge: wenig Daten und keine Hintergrundjobs, aber dynamische Vorschau muss performant und deterministisch sein.
- SKIPPED-Entscheidungen sind erforderlich, sonst tauchen bewusst ausgelassene Termine bei jedem Aufruf erneut auf.
- Ein Scope mit vielen Vorlagen erhält serverseitig begrenzte, paginierte Ergebnisse; Auswertung bleibt auf genau einen Monat begrenzt.
- Die Trennung von Übernahme und Veröffentlichung ist fachlich zwingend: ein CHECKBOX-Klick ersetzt keine Monatsfreigabe.
