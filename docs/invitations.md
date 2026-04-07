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

- Einladungen werden event-basiert ueber den Zellkontext gepflegt:
  - Matrix oeffnet den Gottesdienst-Dialog
  - Dialog speichert Einladung ueber `POST /api/v1/events/{event_id}/invitations`
  - Keine gemeindeweite Matrix-Route fuer Einladungsziele

## Event Read Erweiterungen

`GET /api/v1/events` liefert bei eingeladenen Ziel-Events zusaetzlich:

- `invitation_source_congregation_id`
- `invitation_source_congregation_name`
- `invitation_source_event_id`

`GET /api/v1/districts/{district_id}/matrix` liefert zusaetzlich pro Zelle:

- `assignment_event_id` (Host-Event fuer Dienstleiterpflege)
- `invitation_source_congregation_name` (Anzeige in der eingeladenen Zelle)
- `is_assignment_editable` (`false` in eingeladenen Zellen)

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
