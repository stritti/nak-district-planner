# Konfliktregeln

Die Planung prüft Konflikte am Assignment-Einstiegspunkt. Das Erzeugen eines
PlanningSlots oder EventInstances weist noch keine Amtstragenden zu und löst daher
keine Leader-Konfliktprüfung aus.

## Schweregrade

- `BLOCK`: Die Zuweisung wird mit HTTP 409 abgelehnt.
- `WARN`: Die Zuweisung wird erst nach expliziter Bestätigung mit
  `confirm_warnings=true` gespeichert.
- Kein Ergebnis: Die Zuweisung kann gespeichert werden.

## Regeln

| Regel | Schweregrad | Bedeutung |
| --- | --- | --- |
| `no_double_booking` | `BLOCK` | Zeitliche Überschneidung mit einer bestehenden Zuweisung desselben Leaders. |
| `travel_time_check` | `WARN` | Zu wenig Zeit zwischen Terminen in verschiedenen Gemeinden. Der Wert kommt aus `MIN_TRAVEL_MINUTES` und beträgt standardmäßig 30 Minuten. |
| `role_requirement_check` | `BLOCK` | Der Leader besitzt nicht die erforderliche Amtsstufe. |
| `leader_available` | `BLOCK` | Der Termin überschneidet sich mit einer gepflegten Abwesenheit. |

`congregation_distance_check` ist keine eigene Regel. Gemeindewechsel werden
allein durch `travel_time_check` bewertet, damit keine doppelten Warnungen entstehen.

## API-Fehlerformat

```json
{
  "detail": {
    "conflicts": [
      {
        "rule_id": "no_double_booking",
        "severity": "BLOCK",
        "message": "Der Amtsträger ist bereits eingeplant.",
        "details": {}
      }
    ]
  }
}
```

Die Prüfung kann über `CONFLICT_CHECK_ENABLED=false` temporär deaktiviert werden.
