## Why

Benutzer koennen sich bereits registrieren und sich per OIDC authentifizieren. Es fehlt jedoch ein verbindlicher Freigabeprozess, der steuert, wann ein Benutzer produktiven Zugriff erhaelt und auf welche Bezirke oder Gemeinden sich dieser Zugriff beschraenkt.

## What Changes

- Fuehre ein freigabegesteuertes Onboarding ein: Anmeldung ueber IDP bleibt moeglich, aber Fachzugriff wird erst nach interner Freigabe gewaehrt.
- Erweitere die Freigabe so, dass bei Approval eine explizite Rollen- und Scope-Zuweisung (Bezirk/Gemeinde) gesetzt wird.
- Stelle sicher, dass unfreigegebene Benutzer trotz erfolgreichem Login keine geschuetzten Fach-Endpunkte nutzen koennen.
- Verknuepfe den Registrierungs-/Freigabeflow robust mit `user_sub`, inklusive validierter Token-Verarbeitung beim Self-Registration-Flow.
- Ergaenze API- und UI-Signale fuer den Zustand "Freigabe ausstehend".
- Fuehre optionales IDP-Provisioning bei Genehmigung ein (Invite/Create via konfigurierbarem Provisioning-Endpoint) und speichere Provisioning-Status in der Registrierung.
- Zeige Superadmins und Bezirksadministratoren direkt nach Login eine prominente Anzeige fuer offene Registrierungen.

## Capabilities

### New Capabilities
- `approved-user-onboarding`: Registrierung, Admin-Freigabe und Aktivierung von Benutzerzugriff als durchgaengiger Workflow.
- `scoped-membership-enforcement`: Zugriff wird ausschliesslich ueber zugewiesene Memberships (Role + ScopeType + ScopeId) gesteuert und begrenzt.

### Modified Capabilities

## Impact

- Backend: Registrierung/Freigabe-Endpunkte, Membership-Zuweisung, Authorisierungsguards.
- Domain/DB: Erweiterte Freigabe-Metadaten, Zuordnungsfelder und IDP-Provisioning-Status in Registration.
- Frontend: Admin-Freigabemaske mit Rollen-/Scope-Auswahl, Provisioning-Status und Benutzerstatus "Freigabe ausstehend".
- Security: Strikter Zugriff erst nach Freigabe, klare Scope-Grenzen pro Bezirk/Gemeinde.
- Tests/Dokumentation: Neue Unit-, Integrations- und E2E-Faelle fuer Approval- und Scope-Verhalten.
