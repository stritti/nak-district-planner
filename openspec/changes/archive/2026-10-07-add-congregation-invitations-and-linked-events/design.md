## Context

Die Terminplanung kennt aktuell nur isolierte Events pro Gemeinde. Einladungen werden in der Praxis oft in mehreren Gemeinden kommuniziert, aber ohne technische Verknuepfung gepflegt. Dadurch entstehen doppelte Eingaben und abweichende Standaende, wenn die einladende Gemeinde Uhrzeit, Ort oder Beschreibung aendert.

Die neue Funktion betrifft Backend-Domain, API und Matrix-Frontend gleichzeitig und muss zur bestehenden hexagonalen Architektur passen: Fachlogik in `domain`/`application`, Persistenz in `adapters/db`, HTTP in `adapters/api`.

## Goals / Non-Goals

**Goals:**
- Einladungen zwischen Gemeinden als eigenes Fachkonzept modellieren, inkl. Einladungsquelle und eingeladenen Zielen.
- Verknuepfte Termineintraege fuer eingeladene Gemeinden mit Rueckverweis auf den Originaltermin bereitstellen.
- Aenderungen am Originaltermin kontrolliert auf verknuepfte Eintraege propagieren, mit expliziter Rueckfrage/Bestaetigung vor Ueberschreiben.
- Matrix um Einladungsziele erweitern (Bezirks-Gemeinde oder Freitext-Hinweis ausserhalb des Bezirks).

**Non-Goals:**
- Vollautomatische, ungefragte Ueberschreibung lokaler Anpassungen in eingeladenen Gemeinden.
- Neue Rollen-/Rechtestruktur ausserhalb bestehender AuthZ-Regeln.
- Erweiterung auf externe Kalender-Provider-Sync fuer Einladungsworkflow in dieser Aenderung.

## Decisions

### 1) Eigenes Einladungs-Aggregat statt lose Event-Flags
**Entscheidung:** Einladungen werden als eigene Entitaet mit Quellevent und Zielkontext modelliert (inkl. Target-Typ intern/freitext).

**Warum:** Saubere Trennung zwischen normalem Event und Einladungsbeziehung; erleichtert Auditierbarkeit und zukuenftige Erweiterungen (mehrere Zielgemeinden, Statushistorie).

**Alternative:** Nur zusaetzliche Felder direkt am Event (`invited_from_congregation_id`, `is_invitation_copy`). Wurde verworfen, weil Mehrfachziele und Ueberschreib-Workflows damit schwer konsistent abbildbar sind.

### 2) Verknuepfte Event-Kopien pro Zielgemeinde
**Entscheidung:** Fuer interne Einladungen wird pro eingeladener Gemeinde ein eigener verknuepfter Eventeintrag erzeugt, der auf das Quellevent referenziert.

**Warum:** Bestehende Filterlogik (z. B. `GET /events` nach `congregation_id`) funktioniert unveraendert; jede Gemeinde sieht "ihren" Termin direkt.

**Alternative:** Virtuelle Darstellung ohne persistente Ziel-Events. Wurde verworfen, weil lokale Notizen/Status je Zielgemeinde und manuelle Korrekturen schlechter abbildbar sind.

### 3) Update-Propagation als zweistufiger Workflow
**Entscheidung:** Aenderungen am Quellevent erzeugen fuer verknuepfte Ziele eine "pending overwrite"-Anfrage. Erst nach Bestaetigung wird der Zieltermin ueberschrieben.

**Warum:** Erfuellt die Anforderung "mit Rueckfrage ueberschreiben" und vermeidet unbeabsichtigtes Ueberschreiben lokaler Anpassungen.

**Alternative:** Sofortiges Ueberschreiben mit Undo. Wurde verworfen, da Undo-Fenster und Konfliktfaelle komplexer sind und schlechter zum gewuenschten Bestatigungsprozess passen.

### 4) Matrix-Zielmodell mit diskriminierter Eingabe
**Entscheidung:** Matrix speichert Einladungsziel als union-artigen Typ:
- `DISTRICT_CONGREGATION` mit `target_congregation_id`
- `EXTERNAL_NOTE` mit `external_target_note`

**Warum:** Deckt interne und externe Einladungen explizit und validierbar ab.

**Alternative:** Ein einzelnes Freitextfeld. Wurde verworfen, da interne Bezirksziele nicht referenziell abgesichert waeren.

## Risks / Trade-offs

- [Risiko] Viele verknuepfte Einladungen koennen bei Event-Aenderungen zu Lastspitzen fuehren → Mitigation: Batch-Updates/queued Jobs fuer Propagation in Application-Layer.
- [Risiko] Ueberschreib-Anfragen bleiben unbestaetigt und fuehren zu divergenten Daten → Mitigation: sichtbarer Pending-Status in API/Frontend und regelmaessige Nachverfolgung.
- [Trade-off] Persistente Event-Kopien erhoehen Datenvolumen → akzeptiert fuer klare Mandantensicht und einfache Query-Pfade.

## Migration Plan

1. DB-Schema erweitern (Einladungsentitaeten, Verknuepfungsfelder, Overwrite-Request-Status).
2. Repository-Ports und SQLAlchemy-Adapter fuer Einladungen und Overwrite-Requests implementieren.
3. API-Endpunkte fuer Einladungsanlage, Matrix-Zielpflege und Overwrite-Bestaetigung bereitstellen.
4. Frontend-Matrix und Eventansichten um Einladungsinformationen/Bestaetigungsdialoge erweitern.
5. Bestehende Event-Listen und Filter gegen neue Felder regressiontesten.

## Open Questions

- Sollen eingeladene Gemeinden nur komplett zustimmen/ablehnen oder feldweise Ueberschreibungen bestaetigen koennen?
- Welche Event-Felder gelten als "propagierbar" (z. B. Titel/Datum/Uhrzeit/Ort/Beschreibung) und welche bleiben lokal?
- Braucht es zusaetzliche Benachrichtigungen (z. B. E-Mail/In-App) bei offenen Overwrite-Anfragen?
