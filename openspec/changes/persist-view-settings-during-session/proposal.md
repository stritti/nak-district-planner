## Why

Filter und Sortierung gehören zum aktuellen Arbeitskontext. Beim Wechsel zwischen Matrix, Eventliste und anderen Ansichten sollen Benutzer ihre Auswahl während einer Sitzung nicht erneut einstellen müssen.

## What Changes

- Filterwerte sowie Sortierfeld, Sortierrichtung und vorhandene Sortieroptionen bleiben während derselben Browser-Sitzung pro Ansicht erhalten.
- Die Wiederherstellung gilt beim Verlassen und erneuten Öffnen einer Ansicht, bei Zurück-/Vorwärtsnavigation und beim Neuladen im selben Tab.
- Matrix und Eventliste sind verbindliche Anwendungsfälle; die Regel gilt ebenso für weitere Ansichten mit Filtern oder Sortieroptionen.
- Einstellungen sind nach Benutzer, fachlichem Kontext (Bezirk/Gemeinde) und Ansicht getrennt.
- Abmelden und Beginn einer neuen Browser-Sitzung setzen die Einstellungen auf die Standardwerte zurück.
- Ungültig gewordene Werte werden verworfen, ohne gültige Einstellungen zu verlieren.

## Capabilities

### Modified Capabilities

- `frontend-ux`: Session-weite Wiederherstellung von Filtern und Sortierungen.

## Impact

- OpenSpec-Delta: `specs/frontend-ux/spec.md`.
- Spätere Umsetzung betrifft die Zustandsverwaltung und Ansichten des Frontends, insbesondere Matrix und Eventliste.
- Keine Änderung von APIs, Berechtigungen oder fachlichen Sichtbarkeitsregeln.
- Dieser Change dokumentiert die Anforderung; die Implementierung ist noch offen.
