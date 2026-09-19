# Use-Case Dokumentation

Diese Seite dokumentiert die detaillierten Anwendungsfälle (Use-Cases) des NAK District Planners.

## UC-01: Kalender-Anbindung (Ingest)

**Ziel:** Einbindung externer Kalenderquellen.

**Unterstützte Provider:**
- **Google Calendar** (manuell verwaltete OAuth-Token)
- **Microsoft 365 / Outlook** (Konfiguration vorhanden, Synchronisierung derzeit nicht verfügbar)
- **iCalendar (ICS)** (URL-basiert, direkt oder über CalDAV)
- **CalDAV** (WebDAV-basiert)

**Ablauf:**
1. User wählt Provider-Typ.
2. Für Google hinterlegt ein Administrator die verwalteten Token als JSON; für ICS/CalDAV werden URL und Credentials hinterlegt.
3. Google synchronisiert derzeit nur den primären Kalender; eine interaktive OAuth-Anmeldung und Kalender-Auswahl sind Phase 2.
4. Microsoft-Graph-Integrationen können bis zur vollständigen Zeitbereichsabfrage nicht synchronisiert werden.
5. Speicherung der verschlüsselten Credentials.

**Vertrauens-Entscheidung (Trust Policy):**
- In v1 werden Events aus konfigurierten, vertrauenswürdigen ICS-/CalDAV-Quellen direkt durch UC-02 übernommen.
- Die reviewbasierte Ingestion mit `ExternalEventCandidate` ist als Phase 2 geplant.
- Google- und Microsoft-Integrationen erweitern diese akzeptierte V1-Ausnahme nicht.

::: info Technik
Nutzung des Strategy-Patterns für verschiedene Provider mit einheitlichem Sync-Mechanismus.
:::

## UC-02: Zyklischer Sync (Hintergrund)

**Ziel:** Automatisches Update der Termine von allen verbundenen Kalenderquellen.

**Ablauf:**
1. Celery-Job prüft `last_sync_at` für alle aktiven `CalendarIntegration`-Einträge.
2. Ruft die APIs verfügbarer Provider auf (Google, ICS, CalDAV); Microsoft Graph ist bis zur vollständigen Zeitbereichsabfrage ausgesetzt.
3. Ordnet externe Events vorhandenen Slots über Gemeinde, Datum, Uhrzeit und Kategorie zu; für bereits verknüpfte Events erkennt ein Content-Hash Änderungen.

**Sync-Logik (für die in v1 freigegebenen ICS-/CalDAV-Quellen):**
- **Neu (v1):** Erstelle oder aktualisiere den direkt übernommenen Slot/Event aus einer vertrauenswürdigen Quelle.
- **Geändert:** Aktualisiere ein bereits verknüpftes Event, wenn sein Content-Hash abweicht.
- **Gelöscht:** Markiere den zugehörigen `PlanningSlot` mit `status=CANCELLED`.
- **Idempotenz:** Duplikate werden durch UID + Source-Vergleich verhindert.

**Phase 2: Review-basierte Ingestion:**
- Ein externer Event ohne exakte Slot-Zuordnung wird als `ExternalEventCandidate` angelegt und erfordert manuelles Matching oder Genehmigung.
- Eine exakte Zuordnung erstellt direkt ein `ExternalEventLink` ohne Candidate.
- Für einen noch ausstehenden Candidate aktualisiert ein erneuter Sync die Candidate-Daten und den Content-Hash, statt einen zweiten Candidate anzulegen.

### V1-Entscheidung: Direkte Übernahme externer Events

Für Version 1 werden Events aus konfigurierten, vertrauenswürdigen
Quellen nach erfolgreicher Hash-Prüfung direkt übernommen. Ein
manueller Review-Schritt für unbekannte externe Events (`ExternalEventCandidate`)
ist nicht Bestandteil von v1. `SyncState` und `ExternalEventLink` dienen weiterhin
der Änderungs- und Zuordnungsverfolgung.

Diese Entscheidung setzt voraus, dass nur fachlich freigegebene Kalenderquellen
konfiguriert werden. Ein Review-Workflow für neue oder nicht vertrauenswürdige
Quellen bleibt als Phase 2 geplant.

## UC-03: Dienstplanung & Lücken-Visualisierung

**Ziel:** Bezirksebene sieht alle Gottesdienste und deren Besetzung.

**Visualisierung:** Matrix-Ansicht (Vue-Komponente).
- **X-Achse:** Datum.
- **Y-Achse:** Gemeinde.
- **Inhalt:** Wenn `Kategorie="Gottesdienst"` AND `ServiceAssignment=NULL` -> Status: **LÜCKE (Rot)**.

**Aktion:** Klick auf Zelle -> Modal zur Auswahl eines Dienstleiters -> Erstellt `ServiceAssignment`.

### Spalten-Logik
Die Spalten der Matrix setzen sich zusammen aus:
- Datumsangaben aus den Gottesdienst-Zeitplänen (`service_times`) der Gemeinden im gewählten Zeitraum.
- Datumsangaben aller importierten Feiertags-Events (`category="Feiertag"`) des Bezirks — unabhängig vom Gemeinde-Zeitplan. Dadurch erscheinen kirchliche Festtage (Palmsonntag, Ostersonntag, Pfingstsonntag) und gesetzliche Feiertage immer als Spalten.

### Feiertags-Anzeige
Im Spaltenkopf werden Feiertags-Namen grau und kursiv unter dem Datum angezeigt. Ein Feiertag wird als Spalte eingeblendet, auch wenn keine Gemeinde an diesem Tag regulären Gottesdienst hat.

## UC-04: Bezirks-Events verteilen

**Ziel:** Ein Termin im Bezirk (z.B. Ämterstunde) soll in den Gemeindekalendern erscheinen.

**Logik:** Event bekommt `applicability`-Liste. Im Frontend der Gemeinde werden diese "virtuell" eingeblendet.

::: warning Filter
Nur Events mit `status=PUBLISHED` werden an die Gemeinden delegiert.
:::

## UC-06: Feiertags-Import

**Ziel:** Gesetzliche und kirchliche Feiertage im System verfügbar machen, damit sie in der Dienstmatrix sichtbar sind.

### Quellen

#### Gesetzliche Feiertage (Nager.Date API)
- **Endpoint:** `https://date.nager.at/api/v3/PublicHolidays/{year}/DE`
- Kostenlos, keine Authentifizierung.
- Gefiltert nach Bundesland (`state_code` am Bezirk) + bundesweite Feiertage.
- *Hinweis:* Ostersonntag wird von Nager.Date nur für Brandenburg (BB) zurückgegeben.

#### NAK-kirchliche Festtage (berechnet)
- Palmsonntag = Ostern − 7 Tage
- Ostersonntag = Ostern
- Pfingstsonntag = Ostern + 49 Tage
- Entschlafenen-Gottesdienst = erster Sonntag im März, Juli und November (3× pro Jahr)

::: tip Berechnung
Berechnung via Anonymem Gregorianischem Algorithmus (kein externer Dienst, keine Abhängigkeit). Gilt für alle Bezirke, unabhängig vom `state_code`.
:::

### Automatisierung (Celery Beat)
Task `auto_import_feiertage` läuft jeden **1. des Monats um 03:00 Uhr** (Europe/Berlin):
- **Januar–August:** Importiert das laufende Jahr.
- **September–Dezember:** Importiert laufendes Jahr **und** Folgejahr (4 Monate Vorlauf).
- Gesetzliche Feiertage nur für Bezirke mit gesetztem `state_code`.
- Kirchliche Festtage für **alle** Bezirke.

### Manueller Import (UI)
Unter "Kalender-Integrationen" → "Deutsche Feiertage importieren":
- Bezirk, Jahr und Bundesland wählen.
- Ohne Bundesland: nur kirchliche Festtage werden importiert.
- Ergebnis: Anzahl neu ersteller / aktualisierter / unveränderter Events.

### Idempotenz
UIDs sind stabil: `feiertag-DE-{district_id}-{datum}-{name-slug}`. Wiederholter Import überschreibt nur bei Namens- oder Datumsänderung (Hash-Vergleich). Alle importierten Events erhalten `category="Feiertag"`, `source=EXTERNAL`, `status=PUBLISHED`, `visibility=PUBLIC`.

### Konfiguration am Bezirk
Das Feld `state_code` (2-stellig, z.B. `BY`, `NW`) steuert den bundeslandspezifischen Import. Wird in "Bezirke & Gemeinden" beim Anlegen oder nachträglich gesetzt.

## UC-05: Sicherer Export (iCal)

**Ziel:** Abonnierbare URLs für Mitglieder und Amtsträger.

**Endpoint:** `/api/v1/export/{token}/calendar.ics`

**Filter-Logik:**

- **Token-Typ "Öffentlich":** Nur `visibility=PUBLIC` und `status=PUBLISHED`. Namen in `ServiceAssignment` anonymisieren (z.B. nur "Dienstleiter").
- **Token-Typ "Intern":** Zeige `visibility=INTERNAL` und volle Namen.
