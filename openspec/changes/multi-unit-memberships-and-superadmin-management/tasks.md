## 1. Mehrfachzuordnungen

- [ ] 1.1 Mitgliedschafts- und Benutzerverwaltung auf mehrere unabhängige Bezirk-/Gemeindezuordnungen pro Benutzer prüfen und vervollständigen.
- [ ] 1.2 Hinzufügen, Aktualisieren und Entfernen einzelner Zuordnungen ohne Verlust anderer Zuordnungen ermöglichen; alte rollenbasierte Unique-Constraint durch `(user_sub, scope_type, scope_id)` ersetzen. Vorher rollenverschiedene Same-Scope-Dubletten deterministisch auf höchste Rolle konsolidieren, entfallende Zeilen für Audit/Downgrade sichern und parallele Upserts testen.
- [ ] 1.3 Alle effektiven Mitgliedschaften und Rollen in Benutzerverwaltung und Zugriffskontext anzeigen.
- [ ] 1.4 Auswahl und Zugriff auf mehrere berechtigte Einheiten im Frontend prüfen.

## 2. Superadmin-Verwaltung

- [ ] 2.1 Vergabe und Entzug von is_superadmin an registrierte, sicher verknüpfte Benutzer durch bestehende Superadmins in API und UI ermöglichen, mit transaktionaler Sperre gegen den Entzug des letzten Superadmins.
- [ ] 2.2 Superadmin-Status im Zugriffskontext und der Benutzerverwaltung sichtbar machen; Änderungen auditieren.
- [ ] 2.3 Globalen Zugriff ohne Mitgliedschaften durch verifizierte API-RBAC-Dependencies, Datenzugriff/RLS und Frontend durchgängig sicherstellen; Entzug spätestens beim nächsten Request durchsetzen.
- [ ] 2.4 Freigabe-/Pending-Zustände mit der bestehenden Superadmin-Ausnahme vereinbaren.
- [ ] 2.5 Neue Alembic-Migration für `grant_bootstrap_superadmin`: einmalige initiale, owner-kontrollierte Vergabe mit persistiertem Abschlusszustand; niemals bei Logins delegierte Grants entziehen oder einen explizit entzogenen Bootstrap-Subject wieder erhöhen. Bestandsdaten und Recovery-/Rotation-Verfahren absichern.
- [ ] 2.6 `get_current_user` muss nach dem Bootstrap den aktuellen persistierten `users.is_superadmin`-Wert autorisieren statt den Funktionsrückgabewert. Vergabe/Entzug über eng berechtigten DB-Schreibpfad trotz Runtime-Update-Sperre; atomare Letzter-Superadmin-Sperre und Audit überprüfen.

## 3. Verifikation

- [ ] 3.1 Tests für mehrere Gemeinden/Bezirke, unterschiedliche Rollen, zusätzliche Zuordnung, Scope-Duplikate und gezieltes Entfernen ergänzen.
- [ ] 3.2 Negative Tests für Scope-Überschreitung und Superadmin-Vergabe durch Nicht-Superadmins ergänzen; Rollen-Eskalation und Gemeinde-zu-Bezirk-Vergabe abweisen.
- [ ] 3.3 Globalen Superadmin-Zugriff ohne Mitgliedschaften einschließlich RLS und UI testen, ebenso Revocation mit bestehender Session, Pending-Fallback, konkurrierenden Entzug des letzten Superadmins und Audit.
- [ ] 3.4 OpenSpec strikt validieren, relevante Backend-/Frontend-Checks und RLS-Integrationstests ausführen; >80 % Coverage erhalten und Ausnahmefälle, Race Conditions, 403-/Audit-Fehlerpfade abdecken.
- [ ] 3.5 Bootstrap-Regressionstests: Ernennung eines fremden Subjects bleibt über dessen Login und Bootstrap-Login bestehen; Entzug des initial konfigurierten Subjects bleibt über Login/Neustart wirksam; fehlkonfigurierte/leere Ersteinrichtung bleibt fail-closed; Bestandssuperadmins werden bei Migration nicht überschrieben.
- [ ] 3.6 `tenant-isolation`-Delta und die verbindliche `docs/roles.md` mit Cross-District-Mitgliedschaften synchron halten. Die entfernte `TenantValidationMiddleware` nicht als aktive Autorisierungsgrenze dokumentieren; Sicherheits-Doku nach Implementierung gegen tatsächlich registrierte Middleware prüfen.
