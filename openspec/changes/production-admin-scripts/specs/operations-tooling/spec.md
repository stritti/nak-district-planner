## ADDED Requirements

### Requirement: Einheitlicher Einstiegspunkt für Betriebsaufgaben
Das Repository SHALL `scripts/ops/nakctl` mit den Bereichen `queue`, `backup`, `logs` und `status` bereitstellen. Das Werkzeug SHALL `COMPOSE_FILE` und `.env` des Deploy-Verzeichnisses verwenden, `.env` nicht ausführen und nur Docker Compose, Bash und Python 3 auf dem Host voraussetzen.

#### Scenario: Produktions-Compose-Datei wird verwendet
- **GIVEN** `.env` enthält `COMPOSE_FILE=docker-compose.prod.yml`
- **WHEN** der Betreiber `scripts/ops/nakctl status` ausführt
- **THEN** alle Compose-Aufrufe beziehen sich auf den Produktions-Stack

#### Scenario: Unbekannter Befehl
- **WHEN** der Betreiber einen unbekannten Unterbefehl aufruft
- **THEN** das Werkzeug zeigt die Hilfe und endet mit Exit-Code 2

### Requirement: Destruktive Befehle sind abgesichert
Jeder ändernde Befehl SHALL `--dry-run` unterstützen. Destruktive Befehle SHALL vor der Ausführung zeigen, was betroffen ist, und eine ausdrückliche Bestätigung oder `--yes` verlangen. Ohne Bestätigung SHALL nichts geändert werden und der Exit-Code 4 sein. Ausgeführte Änderungen SHALL in `logs/nakctl.log` protokolliert werden.

#### Scenario: Abbruch ohne Bestätigung
- **WHEN** der Betreiber `queue purge` aufruft und die Bestätigung verweigert
- **THEN** die Warteschlange bleibt unverändert
- **AND** der Befehl endet mit Exit-Code 4

#### Scenario: Trockenlauf
- **WHEN** der Betreiber `queue purge --dry-run` aufruft
- **THEN** das Werkzeug zeigt die betroffenen Nachrichten an und löscht nichts

### Requirement: Keine Secrets in Ausgaben und Prozessargumenten
Das Werkzeug SHALL Passwörter und Tokens weder ausgeben noch als Kommandozeilenargument übergeben. Valkey SHALL über `REDISCLI_AUTH` innerhalb des Containers authentifiziert werden.

#### Scenario: Valkey-Abfrage
- **WHEN** `queue status` Valkey abfragt
- **THEN** `VALKEY_PASSWORD` erscheint weder in der Ausgabe noch in den Prozessargumenten des Hosts

### Requirement: Celery-Warteschlange gezielt prüfen und leeren
`queue status` SHALL Queue-Länge, unbestätigte Nachrichten und Ergebnis-Schlüssel zeigen; `queue inspect` SHALL nur Task-Namen zählen, nie Argumente. `queue purge` SHALL nur Celery-Nachrichten löschen und vor Mail-Tasks warnen; `queue purge-results` nur `celery-task-meta-*`. `FLUSHALL` und `FLUSHDB` SHALL nie verwendet werden.

#### Scenario: Rate-Limit-Zähler bleiben erhalten
- **GIVEN** Valkey enthält Celery-Nachrichten und Rate-Limit-Schlüssel
- **WHEN** der Betreiber `queue purge --yes` ausführt
- **THEN** die Celery-Warteschlange ist leer
- **AND** die Rate-Limit-Schlüssel sind unverändert

#### Scenario: Mail-Tasks in der Warteschlange
- **GIVEN** die Warteschlange enthält Mail-Tasks
- **WHEN** der Betreiber `queue purge` aufruft
- **THEN** das Werkzeug weist vor der Bestätigung darauf hin, dass diese Mails nicht versendet werden

#### Scenario: Unbestätigte Nachrichten bei laufendem Worker
- **GIVEN** ein Worker läuft
- **WHEN** der Betreiber `queue purge --include-unacked` aufruft
- **THEN** der Befehl bricht ohne Änderung mit Exit-Code 3 ab

### Requirement: Backups erstellen, auflisten und prüfen
`backup create`, `verify` und `restore` SHALL `scripts/backup.sh` und `scripts/restore.sh` verwenden; `--keycloak` SHALL die Keycloak-Datenbank sichern. `backup list` SHALL je Zeitstempel Datenbank- und Rollenarchiv, Größe und Alter zeigen und mit `--max-age-hours` Exit-Code 1 liefern, wenn kein vollständiges Backup jung genug ist.

#### Scenario: Veraltetes Backup
- **GIVEN** das jüngste vollständige Backup ist 30 Stunden alt
- **WHEN** der Betreiber `backup list --max-age-hours 26` ausführt
- **THEN** der Befehl endet mit Exit-Code 1

#### Scenario: Unvollständiges Paar
- **GIVEN** zu einem Datenbankarchiv fehlt das Rollenarchiv
- **WHEN** der Betreiber `backup list` ausführt
- **THEN** dieser Eintrag ist als unvollständig markiert

### Requirement: Logs redigiert analysieren
`logs analyze` SHALL für einen Zeitraum Fehler und Warnungen je Dienst, häufigste normalisierte Meldungen, HTTP-5xx, fehlgeschlagene und wiederholte Celery-Tasks, Rate-Limiter-Fallbacks und Audit-Schreibfehler zusammenfassen, als Text oder JSON. Vor jeder Ausgabe, auch bei `logs export`, SHALL es Export-Tokens, Bearer-Tokens, Passwörter, Secrets und E-Mail-Adressen maskieren.

#### Scenario: Export-Token in einer Logzeile
- **GIVEN** eine Logzeile enthält `/api/v1/export/abc123/calendar.ics`
- **WHEN** der Betreiber `logs analyze` oder `logs export` ausführt
- **THEN** die Ausgabe enthält `abc123` nicht

#### Scenario: Fehlschlag für Monitoring
- **GIVEN** die Logs der letzten Stunde enthalten einen ERROR des Backends
- **WHEN** der Betreiber `logs analyze --since 1h --fail-on-errors` ausführt
- **THEN** der Befehl endet mit Exit-Code 1

### Requirement: Zustand des Stacks lesend prüfen
`status` SHALL ohne Änderungen Container-Zustand, `/health`, Alembic-Stand gegenüber dem Image-Head, Volume-Belegung und Backup-Alter zeigen und bei einem Befund Exit-Code 1 liefern.

#### Scenario: Ausstehende Migration
- **GIVEN** die Datenbank steht nicht auf dem Alembic-Head des Images
- **WHEN** der Betreiber `status` ausführt
- **THEN** die Abweichung wird gemeldet und der Exit-Code ist 1
