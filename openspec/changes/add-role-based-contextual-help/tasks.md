## 1. Hilfe-Basis und Inhaltsmodell

- [ ] 1.1 Eine wiederverwendbare Help-Panel-Basiskomponente mit einklappbarer Darstellung und Ausblenden-Aktion implementieren
- [ ] 1.2 Ein strukturiertes Inhaltsschema fuer Hilfeeintraege definieren (help_id, Rollen, Kontexte, Titel, Schritte, optionale Links)
- [ ] 1.3 Initiale Hilfeinhalte fuer Gast, Viewer und Planner gemaess Spezifikation in einer zentralen Konfigurationsstruktur hinterlegen

## 2. Rollen- und Kontextauflosung

- [ ] 2.1 Eine zentrale Resolver-Logik fuer sichtbare Hilfe anhand Auth-Status, Rolle und View-Kontext implementieren
- [ ] 2.2 Sicherstellen, dass rollenfremde Hilfen gefiltert werden und nur passende Inhalte ausgeliefert werden
- [ ] 2.3 Tests fuer Guest/Viewer/Planner-Routing der Hilfeinhalte auf Resolver-Ebene erstellen

## 3. Persistenz fuer Ausblenden/Wiedereinblenden

- [ ] 3.1 Hidden-State-Datenmodell pro help_id und Nutzerkontext definieren
- [ ] 3.2 Persistenz fuer angemeldete Nutzer ueber Nutzer-Preferences-Store anbinden
- [ ] 3.3 Persistenz fuer nicht angemeldete Nutzer ueber lokalen Browser-Storage implementieren
- [ ] 3.4 Eine sichtbare Wiederherstellen-Aktion implementieren, die ausgeblendete Hilfe erneut anzeigt

## 4. Integration in priorisierte Views

- [ ] 4.1 Gast-Hilfe mit Registrierungsleitfaden in Registrierung/Login-nahe UI-Bereiche integrieren
- [ ] 4.2 Rollenbezogene Hilfe in Event-Uebersicht fuer Viewer und Planner integrieren
- [ ] 4.3 Planner-spezifische Hilfe in der Matrix-Planungsansicht kontextnah integrieren

## 5. Qualitaetssicherung und Rollout

- [ ] 5.1 End-to-End-Szenarien fuer Sichtbarkeit, Ausblenden und Wiederherstellen pro Rolle validieren
- [ ] 5.2 UI-Feinschliff fuer unaufdringliche, aber sichtbare Darstellung auf Desktop und Mobile durchfuehren
- [ ] 5.3 Optionales Feature-Flag fuer Help-Rendering konfigurieren und Fallback ohne Hilfe dokumentieren
