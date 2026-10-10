## Context

`rbac-model` beschreibt Mitgliedschaften als Zuordnung von Benutzer-Subject, Rolle und Bezirk/Gemeinde. Superadmins umgehen bereits Scope-Prüfungen. Die gewünschte Verwaltung mehrerer Zuordnungen und die Ernennung weiterer Superadmins müssen explizit spezifiziert werden. Die Freigaberegel aus `approved-user-onboarding` muss die vorhandene Superadmin-Ausnahme berücksichtigen.

## Goals / Non-Goals

Ziele: Ein Konto für mehrere Einheiten, unabhängige Rollen je Einheit, sichtbare Verwaltung aller Zuordnungen und globaler Superadmin-Zugriff mit expliziter Vergabe durch bestehende Superadmins.

Nicht Bestandteil: Zusätzliche Rollenarten, neue Registrierungen pro Einheit oder automatische Superadmin-Vergabe bei Registrierung.

## Decisions

### Einheit entspricht dem bestehenden Scope

Eine Einheit ist ein Bezirk (`DISTRICT`) oder eine Gemeinde (`CONGREGATION`). Derselbe Benutzer-Subject kann mehrere Mitgliedschaften besitzen, einschließlich Gemeinden in verschiedenen Bezirken und einer Kombination von Bezirks- und Gemeindemitgliedschaften. Eine Rolle gilt nur in ihrem Scope und entsprechend der bestehenden Rollen-/Scope-Hierarchie.

### Zuordnungen unabhängig verwalten

Eine neue Zuordnung ergänzt die bisherigen Mitgliedschaften. Änderung oder Entfernung einer Zuordnung betrifft nur diese. Eine erneute Zuweisung desselben Scopes aktualisiert die bestehende Zuordnung statt Duplikate anzulegen. Die bestehende DB-Constraint enthält zusätzlich `role` und lässt daher mehrere Rollen im selben Scope zu. Vor Einführung der neuen DB-Unique-Constraint `(user_sub, scope_type, scope_id)` konsolidiert eine Migration bestehende Same-Scope-Zuordnungen deterministisch auf die höchste bereits effektiv vorhandene Rolle (Rang nach RBAC-Hierarchie), bei Gleichstand anhand `updated_at` und stabiler ID. Entfallende Zeilen werden für Audit und reversiblen Downgrade gesichert, nicht still verworfen. Danach erfolgen Upserts transaktional; zwei parallele Requests dürfen keine zweite Scope-Zeile erzeugen. Nicht-Superadmins dürfen nur Rollen bis zur eigenen Berechtigungsstufe im verwalteten Scope vergeben; Gemeindeadmins können keine Bezirksmitgliedschaften erstellen. Superadmins verwalten Zuordnungen global; andere berechtigte Administratoren bleiben auf ihre bestehenden Verwaltungsrechte beschränkt.

### Superadmin ist ein globaler Benutzerstatus

`is_superadmin` ist unabhängig von Mitgliedschaften. Nur ein authentifizierter bestehender Superadmin darf den Status für einen registrierten, sicher mit einem Subject verknüpften Benutzer vergeben. Bestehende Superadmins können diesen Status auch wieder entziehen. Die letzte verbleibende Superadmin-Berechtigung darf nicht entzogen werden; die Prüfung muss parallele Entzüge transaktional absichern. Die bestehende Bootstrap-Funktion bleibt für die initiale Einrichtung gültig. Der Status ist in Benutzerverwaltung und Zugriffskontext sichtbar und Vergabe sowie Entzug werden gemäß bestehender Audit-Regeln erfasst. Maßgeblich ist nur der nach OIDC-Authentifizierung anhand des Subjects aus der Datenbank ermittelte Status, nie ein unverifizierter Token-Claim oder Frontend-Cache.

### Globalen Zugriff durchgängig anwenden

Superadmins können alle Einheiten, fachlichen Daten und Verwaltungsfunktionen lesen bzw. bedienen, auch ohne Mitgliedschaften. Das gilt für TenantValidationMiddleware vor dem Router, Backend-Berechtigungsprüfungen, Datenzugriff einschließlich transaktionslokaler RLS-Kontexte und die Anzeige im Frontend. Entzüge müssen spätestens bei der nächsten Request-Autorisierung gelten, ohne erneuten Login; bestehende normale Mitgliedschaften bleiben dabei erhalten. Ein ausgewählter Bezirk kann die Ansicht filtern, beschränkt aber keine Superadmin-Berechtigung. Authentifizierung und fachliche Validierungen gelten weiterhin.

## Risks / Trade-offs

- Zusätzliche Zuordnung ersetzt versehentlich eine bestehende: gezielte Regressionstests.
- Hohe Rolle in Einheit A wirkt in Einheit B: positive und negative Tests je Scope.
- Frontend zeigt globalen Zugriff, Backend/RLS blockiert ihn: beide Ebenen prüfen.
- Registrierungspayload setzt Superadmin-Status: nicht autorisierte Vergabe mit 403 ablehnen.
- Letzter Superadmin wird entzogen: transaktionale Sperre und negativer Paralleltest.
- Widerruf wirkt bei laufender Session nicht: jede Request-Autorisierung mit aktuellem Datenbankstatus und RLS absichern.
- Unverknüpfte Registrierung wird über uneindeutige E-Mail erhöht: sichere Kontoverknüpfung beibehalten.

## Validation

Ein Benutzer mit Rollen in mehreren Gemeinden/Bezirken, nachträgliches Hinzufügen und gezieltes Entfernen, unveränderte Scope-Grenzen für normale Benutzer, Superadmin-Vergabe durch berechtigte und unberechtigte Akteure sowie globaler Zugriff ohne Mitgliedschaften werden in API-, RLS- und UI-Tests geprüft.
