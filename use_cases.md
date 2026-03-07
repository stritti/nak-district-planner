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

## UC-04: Bezirks-Events verteilen

Ziel: Ein Termin im Bezirk (z.B. Ämterstunde) soll in den Gemeindekalendern erscheinen.

Logik: Event bekommt applicability-Liste. Im Frontend der Gemeinde werden diese "virtuell" eingeblendet.

Filter: Nur Events mit status=PUBLISHED werden an die Gemeinden delegiert.

## UC-05: Sicherer Export (iCal)

Ziel: Abonnierbare URLs für Mitglieder und Amtsträger.

Endpoint: /api/v1/export/{token}/calendar.ics

Filter-Logik:

Token-Typ "Öffentlich": Nur visibility=PUBLIC und status=PUBLISHED. Namen in ServiceAssignment anonymisieren (z.B. nur "Dienstleiter").

Token-Typ "Intern": Zeige visibility=INTERNAL und volle Namen.