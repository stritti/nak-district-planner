## Why

Ein registrierter Benutzer kann für mehrere Gemeinden oder Bezirke zuständig sein. Dafür soll ein einziges Benutzerkonto mehrere unabhängige Zuordnungen erhalten. Außerdem müssen bestehende Superadmins weitere Benutzer über die Benutzerverwaltung zu Superadmins machen können.

## What Changes

- Mehrere Mitgliedschaften desselben Benutzers in Bezirken und Gemeinden ausdrücklich festlegen, jeweils mit eigener Rolle.
- Zusätzliche Zuordnungen nach der Registrierung ermöglichen, ohne vorhandene Zuordnungen zu ersetzen oder ein zweites Konto anzulegen.
- Superadmins können registrierte, eindeutig verknüpfte Benutzer zu weiteren Superadmins ernennen.
- Superadmins haben globalen Zugriff auf alle Einheiten, fachlichen Daten und Verwaltungsfunktionen, auch ohne Mitgliedschaften.
- Benutzerverwaltung und Zugriffskontext zeigen sämtliche Zuordnungen sowie den Superadmin-Status.
- Freigaberegeln ausdrücklich mit der bestehenden Ausnahme für Superadmins vereinbaren.

## Capabilities

### Modified Capabilities

- `rbac-model`: Mehrfachmitgliedschaften, Vergabe des Superadmin-Status und globaler Zugriff.
- `approved-user-onboarding`: Verwaltung zusätzlicher Zuordnungen und explizite Superadmin-Ausnahme.

## Impact

Benutzerverwaltung, Mitgliedschaftsverwaltung, Zugriffskontext und Frontend-Auswahl der Einheiten sind bei der Umsetzung abzugleichen. Bestehende Bootstrap-Vergabe, verifizierte Kontoverknüpfung, Rollen und fachliche Validierungen bleiben gültig. Dieser Change dokumentiert Anforderungen; Implementierung und Prüfung sind offene Aufgaben.
