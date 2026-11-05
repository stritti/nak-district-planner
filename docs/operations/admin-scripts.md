# Admin-Skripte (`nakctl`)

`scripts/ops/nakctl` bündelt die wiederkehrenden Handgriffe im Produktivbetrieb: Zustand prüfen, Celery-Warteschlange leeren, Backups, Log-Auswertung, Versionswechsel, Datenbankwartung und die Wiederherstellung des Superadmins. Das Werkzeug läuft auf dem Docker-Host im Release-Checkout, in dem auch `.env` liegt (siehe [Produktiv-Stack](/operations/production-compose)).

Voraussetzungen auf dem Host sind nur Docker Compose, Bash, Python 3.11 oder neuer und für `check certs` `openssl`. PostgreSQL- und Valkey-Clients laufen in den Containern.

```bash
cd /opt/nak-district-planner        # Release-Checkout mit .env
scripts/ops/nakctl                  # Übersicht
scripts/ops/nakctl queue --help     # Hilfe zu einem Bereich mit Optionen und Beispielen
scripts/ops/nakctl help backup      # dasselbe
```

`COMPOSE_FILE` aus `.env` gilt wie bei `docker compose`; mit `NAK_DEPLOY_DIR=/pfad` arbeitet `nakctl` in einem anderen Verzeichnis.

## Gemeinsame Regeln

| Regel | Bedeutung |
| --- | --- |
| `--dry-run` | Jeder ändernde Befehl zeigt nur, was er tun würde. |
| Bestätigung | Löschende und ändernde Befehle zeigen vorher, was betroffen ist, und fragen nach (`LEEREN` bzw. `ja`). Ohne Terminal brechen sie mit Exit-Code 4 ab, außer mit `--yes`. |
| Protokoll | Jede ausgeführte Änderung steht mit Zeit und Betriebssystem-Benutzer in `logs/nakctl.log`. |
| Keine Secrets | Passwörter erscheinen weder in der Ausgabe noch in Prozessargumenten. Valkey wird im Container über `REDISCLI_AUTH` angemeldet, `.env` wird gelesen, aber nie ausgeführt. |
| Keine Personendaten | Queue-Nachrichten zeigen nur Task-Namen, Logs und lange Abfragen werden redigiert. |

### Exit-Codes

| Code | Bedeutung |
| --- | --- |
| 0 | alles in Ordnung |
| 1 | Befund, z. B. Schwelle unterschritten, Fehler in den Logs, Hook fehlgeschlagen |
| 2 | Bedienfehler, z. B. unbekannte Option, unbekannte Version, unbekannte `sub` |
| 3 | Umgebung nicht nutzbar, z. B. Docker fehlt, Container läuft nicht, Valkey nicht erreichbar |
| 4 | abgebrochen, keine Bestätigung |

## Zustand und Prüfungen

```bash
scripts/ops/nakctl status          # Dienste laufen, /health, Alembic-Stand, Backup-Alter, Platz
scripts/ops/nakctl check certs     # TLS-Zertifikate von APP_HOST und AUTH_HOST (Befund unter 21 Tagen; ein Host ohne Antwort nach 15 s ist ebenfalls ein Befund)
scripts/ops/nakctl check disk      # freier Platz (Befund unter 15 %)
scripts/ops/nakctl check secrets   # .env-Dateien: Rechte 0600, Beispiel- und Standardwerte
scripts/ops/nakctl check all       # alles zusammen, für den täglichen Cron-Job
```

`check secrets` prüft `.env`, `.env.db`, `.env.keycloak` und `.env.keycloak-db` gegen ihre `*.example`-Dateien. Es meldet zu weite Rechte, übernommene Beispielwerte, Standardwerte wie `changeme`, Owner-Credentials (`POSTGRES_PASSWORD`, `MIGRATION_DATABASE_URL`) in der Laufzeit-`.env`, ein fehlendes `BACKUP_ENCRYPT_KEY` bei `APP_ENV=production` und fehlende Secrets, die das Beispiel vorbelegt. Bei `APP_ENV=production` muss `.env.db` vorhanden sein; die Keycloak-Dateien sind optional (externer Identity Provider). `KC_BOOTSTRAP_ADMIN_PASSWORD` darf nach der Keycloak-Einrichtung fehlen. Es nennt nur Schlüsselnamen, nie Werte.

## Celery-Warteschlange

Celery nutzt Valkey als Broker. In derselben Instanz liegen die Zähler des Rate-Limiters. `nakctl` löscht deshalb nur Celery-Schlüssel und verwendet nie `FLUSHALL` oder `FLUSHDB`.

```bash
scripts/ops/nakctl queue status                 # Queue-Länge, unacked, Ergebnis-Schlüssel, worker
scripts/ops/nakctl queue inspect --limit 200    # Task-Namen zählen, ohne Argumente
scripts/ops/nakctl queue purge --dry-run        # zeigt, was gelöscht würde
docker compose stop beat                        # sonst plant Beat sofort neu ein
scripts/ops/nakctl queue purge                  # Eingabe LEEREN bestätigt
scripts/ops/nakctl queue purge-results          # nur celery-task-meta-*
docker compose start beat
```

Enthält die Queue Mail-Tasks (`dispatch_event_mail_hooks`, `check_due_reminders`, `scan_slot_gaps`), warnt `nakctl` vor dem Löschen. Diese Mails werden danach nie versendet. Kalender-Sync, Entwürfe und Lückenscan plant Beat beim nächsten Lauf ohnehin neu ein.

Unbestätigte Nachrichten (`unacked`) gehören einem laufenden Worker. `queue purge --include-unacked` löscht sie nur, wenn der `worker` gestoppt ist (`docker compose stop worker beat`), sonst bricht der Befehl mit Exit-Code 3 ab.

## Backups

```bash
scripts/ops/nakctl backup create --keycloak             # App- und Keycloak-Datenbank
scripts/ops/nakctl backup list --max-age-hours 26       # Exit 1, wenn kein vollständiges Backup jung genug ist
scripts/ops/nakctl backup verify backups/nak_planner_20261105_020000.dump.gpg
scripts/ops/nakctl backup restore backups/nak_planner_20261105_020000.dump.gpg
scripts/ops/nakctl backup restore backups/keycloak_20261105_020000.dump.gpg --keycloak
```

`backup create` ruft `scripts/backup.sh` mit Datenbank, Container, `BACKUP_ENCRYPT_KEY` und `BACKUP_DIR` (Standard: `backups/` im Deploy-Verzeichnis) aus dem Deploy-Verzeichnis auf; ein vollständiges Backup besteht aus Datenbank- und Rollenarchiv (siehe [Runbook, Abschnitt 5](/operations/production-runbook#_5-backup-und-restore)). `backup list` markiert unvollständige Paare, leere Archive (etwa nach einem abgebrochenen Lauf) und unverschlüsselte Archive; leere Archive zählen nicht als vollständiges Backup. Die Zeitstempel im Dateinamen sind UTC.

### Off-Site-Kopie mit `BACKUP_POST_HOOK`

Ist `BACKUP_POST_HOOK` in `.env` oder der Umgebung gesetzt, ruft `backup create` nach jedem vollständigen Backup diese Datei mit zwei Argumenten auf: Pfad des Datenbankarchivs und Pfad des Rollenarchivs. Die Datei wird direkt ausgeführt, nicht über eine Shell. Sie muss dem aktuellen Benutzer oder root gehören und darf nicht für Gruppe oder andere schreibbar sein. Schlägt der Hook fehl, bleibt das lokale Backup erhalten und `backup create` endet mit Exit-Code 1.

Einstellungen für den Hook beginnen mit `OFFSITE_` (z. B. `OFFSITE_TARGET`, `OFFSITE_SSH_KEY`). `nakctl` übergibt sie aus `.env` an den Hook; ein in der Umgebung gesetzter Wert geht vor. Andere Werte aus `.env`, etwa Secrets, erhält der Hook nicht.

Die Vorlage `scripts/ops/examples/backup-post-hook-rsync.sh` kopiert nur verschlüsselte Archive per `rsync` über SSH:

```bash
cp scripts/ops/examples/backup-post-hook-rsync.sh /opt/nak/backup-offsite.sh
chmod 700 /opt/nak/backup-offsite.sh
# in .env:
#   BACKUP_POST_HOOK=/opt/nak/backup-offsite.sh
#   OFFSITE_TARGET=backup@backup.example.org:/srv/nak/
```

## Logs

```bash
scripts/ops/nakctl logs analyze                                   # letzte 24 Stunden, alle Dienste
scripts/ops/nakctl logs analyze --since 2h --service backend --service worker
scripts/ops/nakctl logs analyze --since 1h --fail-on-errors --json
scripts/ops/nakctl logs export --since 6h --output /tmp/nak-logs.txt
```

`logs analyze` zählt Warnungen und Fehler je Dienst, zeigt die häufigsten Meldungen in normalisierter Form (UUIDs, Zahlen und IP-Adressen als Platzhalter) und erkennt HTTP-5xx, fehlgeschlagene und wiederholte Celery-Tasks, Zeitlimits, Rate-Limiter-Fallbacks und -Überschreitungen, Audit-Fehler, Datenbank- und Valkey-Verbindungsfehler sowie ein nicht passendes Schema.

Vor jeder Ausgabe werden Export-Tokens (`/api/v1/export/…`), Bearer- und Basic-Credentials, Passwörter in URLs, Werte von Schlüsseln wie `password`, `secret`, `token`, OAuth-Parameter (`code`, `state`) und E-Mail-Adressen maskiert. `logs export` schreibt in eine neue Datei mit Rechten 0600. Die Maskierung erkennt nur bekannte Formate; einen Export vor dem Teilen trotzdem durchsehen.

## Versionswechsel

```bash
git fetch --tags && git checkout v1.7.0
scripts/ops/nakctl deploy update 1.7.0 --dry-run
scripts/ops/nakctl deploy update 1.7.0
scripts/ops/nakctl deploy rollback
```

`deploy update` prüft, dass Backend- und Frontend-Image zur Version veröffentlicht sind, erstellt ein Backup, merkt die laufende Version in `logs/nakctl.state`, setzt `APP_VERSION` in `.env`, zieht die Images, führt den `migrate`-Dienst aus, startet den Stack und wartet bis zu zwei Minuten auf `/health`. Schlägt ein Schritt nach der Migration fehl, rollt `nakctl` nicht automatisch zurück, sondern nennt den nächsten Schritt.

`deploy rollback` setzt die gemerkte Vorversion nur, wenn deren Alembic-Head genau dem Datenbankstand entspricht. Hat die neue Version die Datenbank schon weiter migriert, bricht der Befehl ohne Änderung ab. Dann zuerst ein Backup einspielen oder mit dem neueren Image `alembic downgrade <revision>` ausführen (siehe [Runbook, Abschnitt 4](/operations/production-runbook#_4-rollback)).

## Datenbankwartung

```bash
scripts/ops/nakctl db stats                       # Größe, Tabellen, Verbindungen, lange Abfragen, Sperren
scripts/ops/nakctl db stats --long-seconds 5
scripts/ops/nakctl db vacuum --table planning_slots
```

`db stats` läuft als Datenbank-Owner im `db`-Container. Abfragetexte langer Abfragen werden auf 80 Zeichen gekürzt; Zeichenketten, Zahlen und Parameter darin erscheinen als `?`. Ab dem ersten Kommentar, Dollar-Quoting (`$$…$$`) oder Backslash wird der Text abgeschnitten (`…`), damit auch diese Literalformen nicht erscheinen. `db vacuum` führt `VACUUM (ANALYZE)` aus, nie `VACUUM FULL`.

## Superadmin wiederherstellen

Wechseln Realm oder Identity Provider, hat dieselbe Person eine neue `sub` und ist nicht mehr Superadmin ([Runbook, Abschnitt 2.3](/operations/production-runbook#_2-3-neuer-benutzer-subject-realm-oder-keycloak-wechsel)). Gibt es noch einen anderen Superadmin, ernennt er das neue Konto in der Benutzerverwaltung. Sonst:

```bash
scripts/ops/nakctl superadmin list                 # Superadmins, Bootstrap-Subject, zuletzt angelegte Benutzer
scripts/ops/nakctl superadmin list --email anna@   # Kandidaten nach E-Mail-Teil filtern
scripts/ops/nakctl superadmin set-sub <neue-sub>   # nur für eine vorhandene sub
```

Die Person meldet sich dazu einmal mit dem neuen Konto an, damit die `sub` existiert, und nach `set-sub` erneut. Die `sub` wird als psql-Variable übergeben, nicht in SQL eingesetzt.

## Aufräumen

```bash
scripts/ops/nakctl cleanup images --dry-run
scripts/ops/nakctl cleanup images
```

Entfernt lokale Backend- und Frontend-Images alter App-Versionen. Behalten werden `APP_VERSION` und die gemerkte Vorversion (ohne gemerkte die jüngste andere), damit ein Rollback ohne erneuten Download möglich bleibt. Volumes werden nie gelöscht.

## Cron-Beispiel

```text
# /etc/cron.d/nak-district-planner (Benutzer mit Docker-Rechten, hier: nak)
MAILTO=ops@example.org
15 2 * * *  nak  cd /opt/nak-district-planner && scripts/ops/nakctl backup create --keycloak
0  7 * * *  nak  cd /opt/nak-district-planner && scripts/ops/nakctl check all >/dev/null || scripts/ops/nakctl check all
*/30 * * * * nak cd /opt/nak-district-planner && scripts/ops/nakctl logs analyze --since 30m --fail-on-errors >/dev/null || scripts/ops/nakctl logs analyze --since 30m
```

Cron verschickt nur Ausgaben; mit `>/dev/null || …` kommt eine Mail nur bei einem Befund.

## Nicht enthalten

- **Rotation von `ENCRYPTION_KEY`:** Die Anwendung kennt nur einen Fernet-Schlüssel. Eine Rotation braucht Änderungen im Backend und ist ein eigener Change.
- **Benutzerverwaltung in Keycloak:** Dafür gibt es die Keycloak-Konsole und die Benutzerverwaltung der Anwendung.
- **Priorisierte Celery-Queues:** Die Anwendung nutzt keine Task-Prioritäten; `nakctl` betrachtet nur die Queue `celery`.
