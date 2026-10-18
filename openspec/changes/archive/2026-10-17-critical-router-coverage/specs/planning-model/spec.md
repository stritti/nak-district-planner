# planning-model Delta

## ADDED Requirements

### Requirement: Zeitkonsistente Aktualisierung von Planungsserien
Beim Ändern einer Planungsserie SHALL der Router `updated_at` als zeitzonenbewussten UTC-Zeitstempel speichern, konsistent mit der initialen Erzeugung. Der Zeitstempel SHALL nicht in eine naive lokale Zeit umgewandelt werden.

#### Scenario: Planungsserie wird geändert
- **WHEN** ein berechtigter Bezirksadministrator eine Planungsserie aktualisiert
- **THEN** ist `updated_at` UTC-bewusst und nicht älter als der zuvor gespeicherte UTC-Zeitstempel
