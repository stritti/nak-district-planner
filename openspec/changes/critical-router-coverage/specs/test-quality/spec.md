# test-quality Delta

## ADDED Requirements

### Requirement: Datei-bezogene Testabdeckung kritischer Backend-Router

Die Backend-Unit-Tests SHALL für `auth.py`, `leader_unavailabilities.py`, `planning_series.py` und `system.py` jeweils mindestens 80 Prozent Line Coverage erreichen. CI SHALL für jede dieser Dateien den exakten Eintrag im Coverage-XML verlangen, und SHALL bei Unterschreitung fehlschlagen. Die globale Mindest-Coverage bleibt unverändert. Tests für 403-/404-/422-Pfade SHALL Scope und Authentisierung durch reale Berechtigungsfunktionen prüfen.

#### Scenario: Alle kritischen Router abgedeckt
- **WHEN** alle vier Router jeweils mindestens 80 Prozent Unit-Line-Coverage erreichen
- **THEN** besteht das zusätzliche CI-Gate

#### Scenario: Ein Router oder Coverage-Eintrag fehlt
- **WHEN** eine gemessene Router-Coverage kleiner als 80 Prozent ist oder der Klasseintrag im XML fehlt
- **THEN** schlägt das Gate unabhängig vom globalen Durchschnitt fehl

#### Scenario: Fremde Bezirks-ID im Mutationsrequest
- **WHEN** ein authentifizierter Benutzer eine fremde Bezirksressource schreibt
- **THEN** verweigert die API vor der Speicherung die Änderung, und ein Test verifiziert die verweigerte Repository-Mutation
