## 1. Zustandsverwaltung

- [x] 1.1 Vorhandene Filter und Sortieroptionen der Matrix, Eventliste und weiterer betroffener Ansichten erfassen.
- [x] 1.2 Gemeinsame Session-Speicherung nach Benutzer, Bezirk/Gemeinde und Ansicht umsetzen.
- [x] 1.3 Gültige Werte wiederherstellen; ungültige Werte und beschädigte Speicherung mit Standardwerten behandeln.
- [x] 1.4 Gespeicherten und aktiven Zustand bei Abmeldung bzw. Identitätswechsel bereinigen.

## 2. Ansichten

- [x] 2.1 Matrixfilter und Gruppensortierung beim erneuten Öffnen und Reload wiederherstellen.
- [x] 2.2 Vorhandene Filter und Listen-/Kalenderansicht der Eventliste anbinden; keine neue Sortierfunktion hinzufügen.
- [x] 2.3 Dieselbe Regel auf weitere bestehende Ansichten mit Filtern oder Sortierung anwenden.
- [x] 2.4 Bedienelemente und Datenabfragen synchron halten; explizite Rücksetzungen als neuen Zustand speichern.

## 3. Verifikation

- [x] 3.1 Unit-Tests für unabhängige Ansichten/Kontexte, Abmeldung und ungültige Speicherwerte ergänzen.
- [x] 3.2 Browser-Tests für Matrix und Eventliste: Seitenwechsel, Zurück-/Vorwärtsnavigation und Reload ergänzen.
- [x] 3.3 Standardwerte in neuer Sitzung und Isolation bei Benutzer-/Kontextwechsel prüfen.
- [x] 3.4 OpenSpec-Baseline strikt validieren und Frontend-Checks inklusive Coverage bestätigen (GitHub-CI: 690 Unit-Tests, 47 Browser-Tests, ESLint, Build und Mindestabdeckung erfolgreich).
- [ ] 3.5 Vollständige OpenSpec-Validierung mit `validate --all` ausführen; lokal durch defekten Prozesszugriff blockiert. Der bestehende Docs-Workflow validiert die Baseline strikt, da aktive Änderungen noch separate Validierungsschulden enthalten (siehe Workflow-Kommentar #475/#476).
