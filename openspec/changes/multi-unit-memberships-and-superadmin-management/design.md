## Context

`rbac-model` beschreibt Mitgliedschaften als Zuordnung von Benutzer-Subject, Rolle und Bezirk/Gemeinde. Superadmins umgehen bereits Scope-Prüfungen. Die gewünschte Verwaltung mehrerer Zuordnungen und die Ernennung weiterer Superadmins müssen explizit spezifiziert werden. Die Freigaberegel aus `approved-user-onboarding` muss die vorhandene Superadmin-Ausnahme berücksichtigen.

## Goals / Non-Goals

Ziele: Ein Konto für mehrere Einheiten, unabhängige Rollen je Einheit, sichtbare Verwaltung aller Zuordnungen und globaler Superadmin-Zugriff mit expliziter Vergabe durch bestehende Superadmins.

Nicht Bestandteil: Zusätzliche Rollenarten, neue Registrierungen pro Einheit oder automatische Superadmin-Vergabe bei Registrierung.

## Decisions

### Einheit entspricht dem bestehenden Scope

Eine Einheit ist ein Bezirk (`DISTRICT`) oder eine Gemeinde (`CONGREGATION`). Derselbe Benutzer-Subject kann mehrere Mitgliedschaften besitzen, einschließlich Gemeinden in verschiedenen Bezirken und einer Kombination von Bezirks- und Gemeindemitgliedschaften. Eine Rolle gilt nur in ihrem Scope und entsprechend der bestehenden Rollen-/Scope-Hierarchie.

### Zuordnungen unabhängig verwalten

Eine neue Zuordnung ergänzt die bisherigen Mitgliedschaften. Änderung oder Entfernung einer Zuordnung betrifft nur diese. Eine erneute Zuweisung desselben Scopes aktualisiert die bestehende Zuordnung statt Duplikate anzulegen. Superadmins verwalten Zuordnungen global; andere berechtigte Administratoren bleiben auf ihre bestehenden Verwaltungsrechte beschränkt.

### Superadmin ist ein globaler Benutzerstatus

`is_superadmin` ist unabhängig von Mitgliedschaften. Nur ein authentifizierter bestehender Superadmin darf den Status für einen registrierten, sicher mit einem Subject verknüpften Benutzer vergeben. Die bestehende Bootstrap-Funktion bleibt für die initiale Einrichtung gültig. Der Status ist in Benutzerverwaltung und Zugriffskontext sichtbar und Änderungen werden gemäß bestehender Audit-Regeln erfasst.

### Globalen Zugriff durchgängig anwenden

Superadmins können alle Einheiten, fachlichen Daten und Verwaltungsfunktionen lesen bzw. bedienen, auch ohne Mitgliedschaften. Das gilt für Backend-Berechtigungsprüfungen, Datenzugriff einschließlich RLS und die Anzeige im Frontend. Ein ausgewählter Bezirk kann die Ansicht filtern, beschränkt aber keine Superadmin-Berechtigung. Authentifizierung und fachliche Validierungen gelten weiterhin.

## Risks / Trade-offs

- Zusätzliche Zuordnung ersetzt versehentlich eine bestehende: gezielte Regressionstests.
- Hohe Rolle in Einheit A wirkt in Einheit B: positive und negative Tests je Scope.
- Frontend zeigt globalen Zugriff, Backend/RLS blockiert ihn: beide Ebenen prüfen.
- Registrierungspayload setzt Superadmin-Status: nicht autorisierte Vergabe mit 403 ablehnen.
- Unverknüpfte Registrierung wird über uneindeutige E-Mail erhöht: sichere Kontoverknüpfung beibehalten.

## Validation

Ein Benutzer mit Rollen in mehreren Gemeinden/Bezirken, nachträgliches Hinzufügen und gezieltes Entfernen, unveränderte Scope-Grenzen für normale Benutzer, Superadmin-Vergabe durch berechtigte und unberechtigte Akteure sowie globaler Zugriff ohne Mitgliedschaften werden in API-, RLS- und UI-Tests geprüft.
