# Konfliktregeln der Dienstplanung

Die Konfliktprüfung läuft serverseitig vor jeder Zuweisung (`POST/PUT /api/v1/events/{event_id}/assignments`). Bei Konflikten antwortet der Backend mit **HTTP 409** und einer strukturierten Konfliktliste (`rule_id`, `severity`, `message`, `details`).

## Severities

| Severity | Verhalten im Frontend | Backend-Verhalten |
|---|---|---|
| `BLOCK` | Zuweisung nicht möglich; Submit-Button deaktiviert, Konfliktmeldung als Tooltip und Banner (rot) | 409 unabhängig von `confirm_warnings` |
| `WARN` | Bestätigungsdialog „Trotz Konflikt zuweisen?"; erst nach Bestätigung wird `confirm_warnings: true` mitgeschickt (gelb) | 409 nur wenn `confirm_warnings` nicht gesetzt |
| `PASS` | keine Anzeige | kein 409 |

## Regeln

| Regel-ID | Severity | Bedeutung |
|---|---|---|
| `no_double_booking` | BLOCK | Amtsträger ist im selben Zeitraum bereits anderweitig zugewiesen |
| `travel_time_check` | WARN | Unterschreitung der Mindest-Wechselzeit (`MIN_TRAVEL_MINUTES`, Default 30) zwischen zwei Terminen |
| `role_requirement_check` | BLOCK | Amtsträger erfüllt die erforderliche Rolle/Rang nicht |
| `leader_available` | BLOCK | Amtsträger ist im Zeitraum als abwesend markiert |

## Konfiguration

- `CONFLICT_CHECK_ENABLED` (Default: `true`) — schaltet die Prüfung ein/aus (Feature-Flag in den Backend-Settings)
- `MIN_TRAVEL_MINUTES` (Default: `30`) — Mindest-Wechselzeit für `travel_time_check`

## Frontend-Verhalten

1. Der Nutzer wählt im Assignment-Dialog eine:n Amtsträger:in und klickt auf „Zuweisen"
2. Bei 409 parst das Frontend die Konfliktliste (`ConflictError`) und zeigt sie im `ConflictBanner` an
3. **BLOCK**: Submit bleibt deaktiviert, Tooltip listet die Blockierungsgründe
4. **WARN**: Confirm-Dialog „Trotz Konflikt zuweisen?" — Bestätigen sendet die Zuweisung erneut mit `confirm_warnings: true`
5. Nach erfolgreichem Speichern wird die Matrix neu geladen

## E2E-Tests

Die Playwright-Suiten (`services/frontend/tests/e2e/`) sind in `tests/e2e/`-Setup unter dem Frontend-Verzeichnis organisiert; Konflikt-Szenarien werden in `conflict-assignment.spec.ts` abgedeckt.
