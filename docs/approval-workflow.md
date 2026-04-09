# Freigabe-Workflow fuer IDP-Benutzer

Dieses Dokument beschreibt den produktiven Onboarding-Ablauf fuer Benutzer, die sich ueber OIDC/IDP anmelden.

## Ziel

- Anmeldung bleibt IDP-basiert (OIDC).
- Fachzugriff wird erst nach interner Freigabe aktiviert.
- Zugriff wird strikt auf den zugewiesenen Scope (Bezirk oder Gemeinde) begrenzt.

## Ablauf

1. Benutzer registriert sich ueber die oeffentliche Registrierungsseite.
2. Optional mitgesendeter Bearer-Token wird validiert; bei ungueltigem Token wird `401` geliefert.
3. Registrierung landet als `PENDING` im Bezirk.
4. Bezirksadministrator genehmigt mit:
   - `role` (`DISTRICT_ADMIN`, `CONGREGATION_ADMIN`, `PLANNER`, `VIEWER`)
   - `scope_type` (`DISTRICT` oder `CONGREGATION`)
   - `scope_id` (UUID des Bezirkes oder der Gemeinde)
5. Bei genehmigter Registrierung wird eine Membership erzeugt oder aktualisiert.
6. Nach Login ist der Benutzer aktiv, sobald mindestens eine Membership vorhanden ist.

## Wichtige Regeln

- Pro Approval wird initial genau eine Membership gesetzt.
- Standardrolle im Freigabe-Dialog ist `PLANNER`.
- Benutzer ohne Membership erhalten auf geschuetzten Endpunkten `403` mit Hinweis auf ausstehende Freigabe.
- `superadmin` ist von der Membership-Pflicht ausgenommen.

## API-Hinweise

- `GET /api/v1/auth/me`: liefert Identitaet (auch vor Freigabe nutzbar)
- `GET /api/v1/auth/access`: liefert effektive Memberships und Status
  - `ACTIVE`: Zugriff freigegeben
  - `PENDING_APPROVAL`: angemeldet, aber keine Membership vorhanden

## Betrieb / Rollout

- Vor Aktivierung des Membership-Gates bestehende Benutzer pruefen und ggfs. backfillen.
- Siehe Runbook: `docs/membership-backfill-runbook.md`.
