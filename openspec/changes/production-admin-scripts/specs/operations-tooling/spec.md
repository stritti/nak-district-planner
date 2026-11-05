## ADDED Requirements

### Requirement: Einheitlicher Einstiegspunkt für Betriebsaufgaben
Das Repository SHALL `scripts/ops/nakctl` mit den Bereichen `queue`, `backup`, `logs`, `status`, `check`, `deploy`, `db`, `superadmin` und `cleanup` als Shell-Skript bereitstellen. Das Werkzeug SHALL `COMPOSE_FILE` und `.env` des Deploy-Verzeichnisses verwenden, `.env` nicht ausführen und nur Docker Compose, Bash und Python 3 auf dem Host voraussetzen.

#### Scenario: Produktions-Compose-Datei wird verwendet
- **GIVEN** `.env` enthält `COMPOSE_FILE=docker-compose.prod.yml`
- **WHEN** der Betreiber `scripts/ops/nakctl status` ausführt
- **THEN** alle Compose-Aufrufe beziehen sich auf den Produktions-Stack

#### Scenario: Hilfe zu einem Bereich
- **WHEN** der Betreiber `nakctl queue --help`, `nakctl queue purge -h` oder `nakctl help queue` aufruft
- **THEN** das Werkzeug zeigt Befehle, Optionen und Beispiele des Bereichs, ändert nichts und endet mit Exit-Code 0

#### Scenario: Aufruf ohne Argumente
- **WHEN** der Betreiber `nakctl` ohne Argumente aufruft
- **THEN** das Werkzeug zeigt die Übersicht aller Bereiche, gemeinsamen Optionen und Exit-Codes

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

### Requirement: Backup an Off-Site-Ziel übergeben
Ist `BACKUP_POST_HOOK` gesetzt, SHALL `backup create` nach einem vollständigen Backup diese Datei direkt, ohne Shell, mit den Archivpfaden aufrufen. Eine für andere schreibbare Hook-Datei SHALL abgelehnt werden. `OFFSITE_*`-Werte aus `.env` SHALL der Hook erhalten, andere `.env`-Werte nicht. Schlägt der Hook fehl, SHALL das lokale Backup erhalten bleiben und der Exit-Code 1 sein.

#### Scenario: Hook schlägt fehl
- **GIVEN** `BACKUP_POST_HOOK` zeigt auf ein Skript, das mit Fehler endet
- **WHEN** der Betreiber `backup create` ausführt
- **THEN** beide Archive liegen im Backup-Verzeichnis
- **AND** der Befehl endet mit Exit-Code 1

#### Scenario: Unsichere Hook-Datei
- **GIVEN** die Hook-Datei ist für alle schreibbar
- **WHEN** der Betreiber `backup create` ausführt
- **THEN** der Hook wird nicht ausgeführt und das Werkzeug meldet den Grund

### Requirement: Betriebsprüfungen für Zertifikate, Platz und Secrets
`check certs` SHALL die Restlaufzeit der TLS-Zertifikate von App- und Keycloak-Host melden, `check disk` den freien Platz von Host, Volumes und Backup-Verzeichnis, `check secrets` Dateirechte 0600, gesetzte Pflichtwerte und übernommene Beispielwerte. Unterschreitet ein Wert seinen Schwellwert, SHALL der Exit-Code 1 sein. Secret-Werte SHALL nie ausgegeben werden.

#### Scenario: Zertifikat läuft bald ab
- **GIVEN** das Zertifikat des App-Hosts läuft in 10 Tagen ab
- **WHEN** der Betreiber `check certs` ausführt
- **THEN** der Befund nennt Host und Restlaufzeit und der Exit-Code ist 1

#### Scenario: Beispielwert in der Produktion
- **GIVEN** ein Pflichtwert in `.env` entspricht dem Wert aus der Beispieldatei
- **WHEN** der Betreiber `check secrets` ausführt
- **THEN** der Befund nennt nur den Schlüsselnamen, nicht den Wert

### Requirement: Versionswechsel mit Backup und Rückweg
`deploy update <version>` SHALL prüfen, dass das Image-Tag existiert, die laufende Version merken, ein Backup erstellen, migrieren, starten und auf `/health` warten. `deploy rollback` SHALL die gemerkte Version nur setzen, wenn deren Alembic-Head zum Datenbankstand passt; sonst SHALL er ohne Änderung abbrechen und auf Restore oder Downgrade verweisen.

#### Scenario: Unbekannte Version
- **WHEN** der Betreiber `deploy update v9.9.9` für ein nicht veröffentlichtes Tag aufruft
- **THEN** nichts wird geändert und der Exit-Code ist 2

#### Scenario: Rollback nach Migration
- **GIVEN** die neue Version hat die Datenbank über den Head der Vorversion hinaus migriert
- **WHEN** der Betreiber `deploy rollback` ausführt
- **THEN** `APP_VERSION` bleibt unverändert
- **AND** die Meldung verweist auf `backup restore` oder `alembic downgrade`

### Requirement: Datenbankwartung ohne Personendaten
`db stats` SHALL Tabellengrößen, Verbindungen, lange Abfragen, Sperren und Autovacuum-Zeitpunkte zeigen und Abfragetexte ohne Literale ausgeben. `db vacuum` SHALL nach Bestätigung `VACUUM (ANALYZE)` ausführen und nie `VACUUM FULL`.

#### Scenario: Lange Abfrage mit E-Mail-Adresse
- **GIVEN** eine laufende Abfrage enthält eine E-Mail-Adresse als Literal
- **WHEN** der Betreiber `db stats` ausführt
- **THEN** die Abfrage erscheint ohne die E-Mail-Adresse

#### Scenario: Lange Abfrage mit Dollar-Quoting
- **GIVEN** eine laufende Abfrage enthält `$$private Notiz$$`
- **WHEN** der Betreiber `db stats` ausführt
- **THEN** der Abfragetext ist vor dem Dollar-Quote abgeschnitten und die Notiz erscheint nicht

### Requirement: Superadmin nach Subject-Wechsel wiederherstellen
`superadmin set-sub <sub>` SHALL nur einen vorhandenen Benutzer-Subject akzeptieren, die Änderung vor der Bestätigung zeigen und dann `app_superadmin_config.superadmin_sub` setzen sowie `bootstrap_completed_at` zurücksetzen. Der Wert SHALL als psql-Variable übergeben werden.

#### Scenario: Unbekannter Subject
- **WHEN** der Betreiber `superadmin set-sub` mit einer `sub` ohne Benutzer aufruft
- **THEN** nichts wird geändert und der Exit-Code ist 2

### Requirement: Alte Images aufräumen
`cleanup images` SHALL lokale Images älterer App-Versionen nach Bestätigung entfernen, die laufende und die gemerkte Vorversion behalten und nie Volumes löschen.

#### Scenario: Vorversion bleibt erhalten
- **GIVEN** lokal liegen Images von drei App-Versionen
- **WHEN** der Betreiber `cleanup images --yes` ausführt
- **THEN** nur das Image der ältesten Version wird entfernt
