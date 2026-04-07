# Einladungen zwischen Gemeinden

Diese Erweiterung fuehrt ein Einladungsmodell ein, bei dem ein Termin aus einer Einladungs-Gemeinde in eingeladenen Gemeinden sichtbar ist und kontrolliert synchronisiert werden kann.

## API Uebersicht

- `POST /api/v1/events/{event_id}/invitations`
  - Legt Einladungsziele fuer ein Quell-Event an.
  - Interne Ziele (`DISTRICT_CONGREGATION`) erzeugen verknuepfte Ziel-Events.
  - Externe Ziele (`EXTERNAL_NOTE`) speichern nur Freitext-Hinweise.

- `GET /api/v1/invitations/overwrite-requests?district_id=<uuid>`
  - Listet offene Ueberschreibungsanfragen (`PENDING_OVERWRITE`) fuer einen Bezirk.
  - Enthalten sind aktuelle und vorgeschlagene Eventwerte.

- `POST /api/v1/invitations/overwrite-requests/{request_id}/decision`
  - Akzeptiert `ACCEPTED` oder `REJECTED`.
  - Bei `ACCEPTED` wird das Ziel-Event mit den vorgeschlagenen Werten ueberschrieben.

- `PATCH /api/v1/districts/{district_id}/matrix/invitation-targets/{congregation_id}`
  - Setzt Matrix-Einladungsziele je Gemeinde.
  - Gueltige Typen:
    - `DISTRICT_CONGREGATION` mit `invitation_target_congregation_id`
    - `EXTERNAL_NOTE` mit `invitation_external_note`

## Event Read Erweiterungen

`GET /api/v1/events` liefert bei eingeladenen Ziel-Events zusaetzlich:

- `invitation_source_congregation_id`
- `invitation_source_congregation_name`
- `invitation_source_event_id`

Damit kann das Frontend den Hinweis "Einladung von <Gemeinde>" anzeigen.

## Migration

Neue Alembic-Revision: `b15c9d3e4f21_invitation_workflow.py`

Schema-Erweiterungen:

- Neue Tabellen:
  - `congregation_invitations`
  - `invitation_overwrite_requests`
- Neue Enums:
  - `invitation_target_type`
  - `overwrite_decision_status`
- Neue Felder:
  - `events.invitation_source_congregation_id`
  - `events.invitation_source_event_id`
  - `congregations.invitation_target_type`
  - `congregations.invitation_target_congregation_id`
  - `congregations.invitation_external_note`
