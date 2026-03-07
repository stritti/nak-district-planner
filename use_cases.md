# Use-Case Dokumentation (Detailliert)

## UC-01: Kalender-Anbindung (Ingest)

Ziel: Einbindung externer Kalenderquellen.

Ablauf: User wählt Typ (z.B. Google) -> OAuth-Handshake -> Auswahl des Kalenders -> Speicherung der verschlüsselten Credentials.

Technik: Nutzung des Strategy-Patterns für verschiedene Provider.

## UC-02: Zyklischer Sync (Hintergrund)

Ziel: Automatisches Update der Termine.

Ablauf: Celery-Job prüft last_sync_at. Ruft Provider-API auf.

Logik: - Neu: Erstelle Event.

Geändert (Hash-Check): Update Event.

Gelöscht: Markiere intern als "cancelled" oder lösche (konfigurierbar).

## UC-03: Dienstplanung & Lücken-Visualisierung

Ziel: Bezirksebene sieht alle Gottesdienste und deren Besetzung.

Visualisierung: Matrix-Ansicht (Vue-Komponente).

X-Achse: Datum.

Y-Achse: Gemeinde.

Inhalt: Wenn Kategorie="Gottesdienst" AND ServiceAssignment=NULL -> Status: LÜCKE (Rot).

Aktion: Klick auf Zelle -> Modal zur Auswahl eines Dienstleiters -> Erstellt ServiceAssignment.

Spalten-Logik: Die Spalten der Matrix setzen sich zusammen aus:
- Datumsangaben aus den Gottesdienst-Zeitplänen (service_times) der Gemeinden im gewählten Zeitraum.
- Datumsangaben aller importierten Feiertags-Events (category="Feiertag") des Bezirks — unabhängig vom Gemeinde-Zeitplan. Dadurch erscheinen kirchliche Festtage (Palmsonntag, Ostersonntag, Pfingstsonntag) und gesetzliche Feiertage immer als Spalten.

Feiertags-Anzeige: Im Spaltenkopf werden Feiertags-Namen grau und kursiv unter dem Datum angezeigt. Ein Feiertag wird als Spalte eingeblendet, auch wenn keine Gemeinde an diesem Tag regulären Gottesdienst hat.

## UC-04: Bezirks-Events verteilen

Ziel: Ein Termin im Bezirk (z.B. Ämterstunde) soll in den Gemeindekalendern erscheinen.

Logik: Event bekommt applicability-Liste. Im Frontend der Gemeinde werden diese "virtuell" eingeblendet.

Filter: Nur Events mit status=PUBLISHED werden an die Gemeinden delegiert.

## UC-06: Feiertags-Import

Ziel: Gesetzliche und kirchliche Feiertage im System verfügbar machen, damit sie in der Dienstmatrix sichtbar sind.

### Quellen

**Gesetzliche Feiertage (Nager.Date API):**
- Endpoint: `https://date.nager.at/api/v3/PublicHolidays/{year}/DE`
- Kostenlos, keine Authentifizierung.
- Gefiltert nach Bundesland (state_code am Bezirk) + bundesweite Feiertage.
- Hinweis: Ostersonntag wird von Nager.Date nur für Brandenburg (BB) zurückgegeben.

**NAK-kirchliche Festtage (berechnet):**
- Palmsonntag = Ostern − 7 Tage
- Ostersonntag = Ostern
- Pfingstsonntag = Ostern + 49 Tage
- Entschlafenen-Gottesdienst = erster Sonntag im März, Juli und November (3× pro Jahr)
- Berechnung via Anonymem Gregorianischem Algorithmus (kein externer Dienst, keine Abhängigkeit).
- Gilt für alle Bezirke, unabhängig vom state_code.

### Automatisierung (Celery Beat)

Task `auto_import_feiertage` läuft jeden **1. des Monats um 03:00 Uhr** (Europe/Berlin):
- Januar–August: Importiert das laufende Jahr.
- September–Dezember: Importiert laufendes Jahr **und** Folgejahr (4 Monate Vorlauf).
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

Ziel: Abonnierbare URLs für Mitglieder und Amtsträger.

Endpoint: /api/v1/export/{token}/calendar.ics

Filter-Logik:

Token-Typ "Öffentlich": Nur visibility=PUBLIC und status=PUBLISHED. Namen in ServiceAssignment anonymisieren (z.B. nur "Dienstleiter").

Token-Typ "Intern": Zeige visibility=INTERNAL und volle Namen.