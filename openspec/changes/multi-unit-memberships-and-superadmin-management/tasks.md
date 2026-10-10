## 1. Mehrfachzuordnungen

- [ ] 1.1 Mitgliedschafts- und Benutzerverwaltung auf mehrere unabhängige Bezirk-/Gemeindezuordnungen pro Benutzer prüfen und vervollständigen.
- [ ] 1.2 Hinzufügen, Aktualisieren und Entfernen einzelner Zuordnungen ohne Verlust anderer Zuordnungen ermöglichen; alte rollenbasierte Unique-Constraint durch `(user_sub, scope_type, scope_id)` ersetzen. Vorher rollenverschiedene Same-Scope-Dubletten deterministisch auf höchste Rolle konsolidieren, entfallende Zeilen für Audit/Downgrade sichern und parallele Upserts testen.
- [ ] 1.3 Alle effektiven Mitgliedschaften und Rollen in Benutzerverwaltung und Zugriffskontext anzeigen.
- [ ] 1.4 Auswahl und Zugriff auf mehrere berechtigte Einheiten im Frontend prüfen.

## 2. Superadmin-Verwaltung

- [ ] 2.1 Vergabe und Entzug von is_superadmin an registrierte, sicher verknüpfte Benutzer durch bestehende Superadmins in API und UI ermöglichen, mit transaktionaler Sperre gegen den Entzug des letzten Superadmins.
- [ ] 2.2 Superadmin-Status im Zugriffskontext und der Benutzerverwaltung sichtbar machen; Änderungen auditieren.
- [ ] 2.3 Globalen Zugriff ohne Mitgliedschaften durch TenantValidationMiddleware, Rollenprüfungen, Datenzugriff/RLS und Frontend durchgängig sicherstellen; Entzug spätestens beim nächsten Request durchsetzen.
- [ ] 2.4 Freigabe-/Pending-Zustände mit der bestehenden Superadmin-Ausnahme vereinbaren.

## 3. Verifikation

- [ ] 3.1 Tests für mehrere Gemeinden/Bezirke, unterschiedliche Rollen, zusätzliche Zuordnung, Scope-Duplikate und gezieltes Entfernen ergänzen.
- [ ] 3.2 Negative Tests für Scope-Überschreitung und Superadmin-Vergabe durch Nicht-Superadmins ergänzen; Rollen-Eskalation und Gemeinde-zu-Bezirk-Vergabe abweisen.
- [ ] 3.3 Globalen Superadmin-Zugriff ohne Mitgliedschaften einschließlich RLS und UI testen, ebenso Revocation mit bestehender Session, Pending-Fallback, konkurrierenden Entzug des letzten Superadmins und Audit.
- [ ] 3.4 OpenSpec strikt validieren und relevante Backend-/Frontend-Checks ausführen.
