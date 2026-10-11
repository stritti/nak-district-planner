# Design

## Verifikation

Die API-Unit-Tests verwenden real erzeugte Memberships und die unveränderten `require_role_in_district`- beziehungsweise `require_superadmin`-Checks. Externe Provider, Repository-Methoden und transaktionssteuernde DB-Sessions werden an ihren Schnittstellen gemockt; 401/403 und RLS-Mandantenszenarien werden zusätzlich in den vorhandenen Integrationstests verifiziert.

Die bestehende CI-Backend-Unit-Suite erzeugt `coverage.xml`. Direkt nach dem globalen `>=80%`-Gate liest `scripts/check_critical_router_coverage.py` die vier Router-Klassen und prüft deren jeweilige `line-rate >= 0.80`. Fehlende Einträge, mehrdeutige Dateinamen und Unterschreitungen liefern einen fehlerhaften Exit-Code. Ein unabhängiger Test prüft Schwellenwert und fehlende Dateien.

## Kompatibilität

Keine Änderung an Produktionscode, Datenbank oder API; das Gate ist additiv. Die bestehenden Integrations- und E2E-Gates laufen unverändert.
