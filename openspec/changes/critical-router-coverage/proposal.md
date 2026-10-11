# Change: Kritische Backend-Router gezielt absichern

## Why
Bei der stabilen 1.0.0 wurden 88 Prozent globale Backend-Unit-Coverage gemessen, aber vier sicherheits- und mandantenkritische Router lagen deutlich darunter (#507). Der globale Durchschnitt verdeckt nicht ausgeübte Fehler- und Autorisierungspfade.

## What Changes
- Verhaltenstests für Authentifizierung/OIDC, Dienstleiter-Abwesenheiten, Planungsserien und Versionsprüfung.
- Fehlerpfade (403, 404, 422, ungültige OIDC-Daten, IdP-Ausfälle), Scope-Grenzen und Berechtigungen mit echten Guard-Funktionen testen.
- Ein Datei-bezogenes 80-Prozent-Line-Coverage-Gate für genau diese vier Router zusätzlich zum unveränderten globalen Coverage-Gate einführen.
- OpenSpec-Testqualitätsbaseline und Coverage-Dokumentation synchronisieren.

## Non-goals
Keine fachliche API-Neugestaltung, kein Wechsel des Coverage-Messverfahrens auf Branch Coverage und keine Schwächung bestehender Schwellenwerte.
