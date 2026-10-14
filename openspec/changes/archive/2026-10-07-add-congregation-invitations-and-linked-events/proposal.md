## Why

Aktuell koennen Einladungen zwischen Gemeinden nur uneinheitlich und manuell abgebildet werden. Das fuehrt zu doppelter Pflege, Inkonsistenzen in Termindaten und fehlender Transparenz in der Bezirks-Matrix.

## What Changes

- Einfuehrung eines Einladungsmodells zwischen Gemeinden, bei dem ein Termin in der einladenden und in eingeladenen Gemeinden sichtbar ist.
- Erweiterung von Terminen um die Information zur Einladungs-Gemeinde in eingeladenen Gemeinden.
- Verknuepfung zwischen Originaltermin (Einladung) und abgeleiteten Termineintraegen in eingeladenen Gemeinden.
- Unterstuetzung von zentralen Termin-Updates durch die einladende Gemeinde mit Rueckfrage/Bestaetigung vor dem Ueberschreiben bei eingeladenen Gemeinden.
- Erweiterung der Matrix-Planung, damit pro Gemeinde ein Einladungsziel gesetzt werden kann (interne Gemeinde im Bezirk oder Freitext fuer externe Ziele).

## Capabilities

### New Capabilities
- `congregation-invitations`: Verwaltung von Einladungen zwischen Gemeinden inkl. Sichtbarkeit des Termins in beteiligten Gemeinden.
- `linked-invitation-events`: Verknuepfte Termininstanzen mit Update-Propagation und Bestaetigungs-Workflow fuer Ueberschreibungen.
- `matrix-invitation-targets`: Matrix-Funktion zum Setzen von Einladungszielen (Bezirks-Gemeinde oder Freitext-Hinweis).

### Modified Capabilities
- (none)

## Impact

- Backend: neue/erweiterte Domain-Modelle fuer Einladungsbeziehungen und verknuepfte Termine; neue Endpunkte fuer Einladungsverwaltung und Update-Bestaetigung.
- Frontend: Matrix-UI und Termin-UI mit Einladungsindikatoren, Zielauswahl und Bestaetigungsdialogen.
- Datenmodell: neue Relationen zwischen Termin und Einladungsmetadaten sowie Freitext-Zielinfo.
- Prozesse: klarer Abgleich zwischen einladender und eingeladener Gemeinde bei Terminaktualisierungen.
