# Production Runbook

Dieses Runbook beschreibt den operativen Mindestablauf fuer produktive Deployments des NAK District Planner. Maßgeblich sind die tatsächlich ausgerollte Image-Version, der [Produktiv-Stack](/operations/production-compose) und das [stabile Release v1.0.0](https://github.com/stritti/nak-district-planner/releases/tag/v1.0.0).

## 1. Voraussetzungen

- Gueltige Produktionskonfiguration ohne Development-Secrets: `.env` fuer die Anwendung und `.env.db` mit dem PostgreSQL-Owner-Passwort (nur fuer `db`/`migrate`, siehe `docs/operations/deployment-migrations.md`)
  - Beim Upgrade einer bestehenden Installation `POSTGRES_PASSWORD` (und ggf. `MIGRATION_DATABASE_URL`) aus `.env` entfernen und nach `.env.db` verschieben. Mit `APP_ENV=production` verweigern API und Worker sonst den Start (`production_guard`).
- TLS-Termination am Reverse Proxy; der Anwendungseinstieg ist nicht direkt oeffentlich exponiert
- PostgreSQL und Valkey/Redis nur im internen Netz erreichbar
- Verschluesselte PostgreSQL-Backups und ein getesteter Restore-Pfad
- OIDC-Provider erreichbar und Redirect-URIs auf HTTPS begrenzt

### 1.1 Production-Config-Checkliste

| Pruefung | Erwartung |
|---|---|
| `APP_ENV=production` | Production Guard ist aktiv |
| `SECRET_KEY` | mindestens 32 Zeichen, kein Platzhalter |
| `OIDC_CLIENT_SECRET` | echter Provider-Wert |
| `OIDC_DISCOVERY_URL` | produktive HTTPS-URL |
| `OIDC_CLIENT_ID` | produktiver Client |
| Debug-Modus | deaktiviert |
| CORS | kein Wildcard-Origin in Produktion |
| `CONFLICT_CHECK_ENABLED` | standardmaessig aktiv |
| IDP-Provisioning | bei Aktivierung HTTPS-Endpunkt und Secret gesetzt |
| `SUPERADMIN_SUB` | bei frischer leerer Installation vor der Migration gesetzt |
| `BACKUP_ENCRYPT_KEY` | fuer verschluesselte Backups gesetzt |
| `CALENDAR_ALLOW_INSECURE_URLS` | `false` (in Produktion erzwungen; Start von API, Worker und Beat schlaegt sonst fehl) |
| `CALENDAR_NAT64_PREFIXES` | Nur bei IPv6-only-Hosts mit DNS64/NAT64 und netzspezifischem Praefix (RFC 6052) setzen: kommagetrennte IPv6-CIDRs der Laenge 32/40/48/56/64/96, z. B. `2001:db8:64::/96`. Ohne Eintrag koennten Kalender-URLs ueber das NAT64-Praefix interne IPv4-Ziele erreichen (SSRF). `64:ff9b::/96` und `64:ff9b:1::/48` werden immer geprueft. Ungueltige Werte verhindern den Start. |

Der Production Guard verhindert den Start bei kritischen unsicheren Werten.

### 1.2 Reverse Proxy und Client-IP

Rate Limiting und Audit-Log verwenden dieselbe Client-IP. Die Vertrauenskette ist:

```text
Client -> externer TLS-Proxy -> 127.0.0.1:80 -> frontend-nginx -> backend:8000
```

- **Externer TLS-Proxy** muss die Client-IP anhaengen und das Schema setzen:
  `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` und
  `proxy_set_header X-Forwarded-Proto https;`
- **frontend-nginx** uebernimmt die Client-IP aus `X-Forwarded-For` nur von Peers in
  `NGINX_REAL_IP_FROM` (Default `127.0.0.1/32 172.16.0.0/12`: Loopback und Docker-Bridge,
  weil der Proxy ueber den Docker-Port-Proxy auf `127.0.0.1:80` ankommt). Erreicht der
  Proxy nginx von einer anderen Adresse (z. B. eigener Host oder Container-Netz
  ausserhalb `172.16.0.0/12`), muss diese ergaenzt werden — sonst sehen alle Nutzer die
  Proxy-IP und teilen sich einen Rate-Limit-Bucket.
- nginx gibt an das Backend nur `X-Real-IP` und ein bereinigtes `X-Forwarded-For`
  (jeweils die ermittelte Client-IP) weiter; eine vom Client gelieferte Kette wird nie
  durchgereicht.
- **Backend** vertraut `X-Real-IP` nur, wenn der TCP-Peer in `TRUSTED_PROXIES` liegt
  (Default `127.0.0.0/8,::1/128,172.16.0.0/12`, also der frontend-nginx-Container);
  sonst gilt die Peer-Adresse. `X-Forwarded-For` wird im Backend nie ausgewertet.
  uvicorn laeuft mit `--no-proxy-headers`, damit die IP nicht doppelt umgeschrieben wird.
- Pruefen: Zwei Clients von verschiedenen IPs erscheinen im Audit-Log mit
  unterschiedlicher `ip_address`; ein mitgeschicktes `X-Forwarded-For: 1.2.3.4` taucht
  dort nicht auf.

## 2. Superadmin-Bootstrap

Der Superadmin-Bootstrap ist owner-controlled. Die Anwendung darf sich keinen Superadmin selbst verleihen.

### 2.1 Frische leere Installation

Vor der Migration `0017` muss `SUPERADMIN_SUB` auf den exakten, case-sensitiven OIDC-`sub` des initialen Superadmins gesetzt werden. Alternativ kann der Datenbank-Owner danach `app_superadmin_config.superadmin_sub` provisionieren.

Wenn die Migration auf einer leeren Installation ohne konfigurierten Subject laeuft, wird **kein** erster Login automatisch zum Superadmin. Bis der DB-Owner einen Subject provisioniert, vergibt `grant_bootstrap_superadmin(TEXT)` keine neue Berechtigung.

### 2.2 Upgrade einer bestehenden Installation

Wenn `SUPERADMIN_SUB` gesetzt ist, wird genau dieser Subject als Superadmin erzwungen. Bei Rotation werden veraltete persistierte Superadmin-Flags fuer andere Subjects entfernt.

Wenn beim Upgrade kein `SUPERADMIN_SUB` gesetzt ist, pinnt die Migration deterministisch einen bereits vorhandenen Superadmin oder ersatzweise den fruehesten bestehenden Benutzer. Dadurch entscheidet nicht die Login-Reihenfolge nach dem Deployment ueber die Berechtigung.

`app_superadmin_config` ist nur fuer den Datenbank-Owner bestimmt. Die Runtime-Rolle darf die Tabelle weder lesen noch schreiben und erhaelt nur den eng begrenzten EXECUTE-Zugriff auf die SECURITY-DEFINER-Funktion.

### 2.3 Neuer Benutzer-Subject (Realm- oder Keycloak-Wechsel)

Der Superadmin ist an den OIDC-`sub` gebunden. Wechselt der Realm oder der Identity Provider (oder wird der Benutzer in Keycloak neu angelegt), hat dieselbe Person danach eine **neue** `sub`. Die gespeicherte gehört dann zum alten Konto, und der Login ist kein Superadmin mehr, bis der Datenbank-Owner den neuen Subject einträgt. `SUPERADMIN_SUB` in der `.env` hilft dabei nicht: Der Wert wird nur einmal übernommen, wenn die Migration `0017` läuft.

Nach dem ersten Login mit dem neuen Konto:

```bash
# 1. Neue sub ablesen (Spalte sub der neuesten Zeile, case-sensitiv)
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT sub, email, is_superadmin, created_at FROM users ORDER BY created_at;"

# 2. Als Superadmin eintragen
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "UPDATE app_superadmin_config SET superadmin_sub='<SUB>' WHERE id = 1;"
```

Danach abmelden und neu anmelden; beim nächsten Login setzt das Backend `is_superadmin` und entzieht es allen anderen Subjects. Es gibt genau einen Superadmin. Mitgliedschaften und Zuordnungen des alten Kontos hängen an der alten `sub` und gehen nicht automatisch über, der Superadmin kann sie neu vergeben.

## 3. Standard-Deployment

> **Empfohlen:** der fertige Produktiv-Stack `docker-compose.prod.yml` mit Traefik (TLS/Let's Encrypt), Keycloak und den veröffentlichten GHCR-Images. Er ersetzt den externen TLS-Proxy aus 1.2 und den Image-Build auf dem Server; Einrichtung und Update siehe `docs/operations/production-compose.md`. Die folgenden Schritte beschreiben den Betrieb mit `docker-compose.yml` und eigenem Reverse Proxy.

1. Release-Tag bzw. freigegebenen `main`-Stand bereitstellen.
2. Images reproduzierbar mit den committed Lockfiles bauen: `docker compose -f docker-compose.yml build`
3. Vor jeder Schemaaenderung ein Backup erstellen.
4. Migrationen ueber den dedizierten Deployment-/`migrate`-Schritt ausfuehren:

   ```bash
   docker compose -f docker-compose.yml run --no-deps --rm migrate
   ```

   Der Schritt verwendet das in Schritt 2 gebaute Image (Details in `docs/operations/deployment-migrations.md`).

5. Erst nach erfolgreicher Migration API, Worker und Beat aktualisieren:

   ```bash
   docker compose -f docker-compose.yml up -d
   ```

6. Readiness/Health pruefen und anschliessend Login, Eventliste, Matrix und Export als Smoke-Test ausfuehren.

Die API-Runtime ist **nicht** Owner des Migrations-Lifecycles. Ein Anwendungsstart darf keine `alembic upgrade`-Operation als Seiteneffekt ausfuehren; vor dem Traffic muss das Schema durch den Deployment-Schritt auf dem erwarteten Stand sein.

**Update-Hinweis in der App:** Die Anwendung zeigt Administratoren nur an, dass eine
neuere Version verfügbar ist (Banner mit Link auf die Release Notes). Sie führt
selbst **keine** Updates aus — ein Update ist immer das obige Standard-Deployment
mit dem neuen Release-Tag. Versionsvergleich nach SemVer 2.0 (inkl. Prereleases wie
`1.0.0-rc.1`; PEP-440-Versionen wie `1.0.0rc1` werden normalisiert). Prereleases
werden nur angeboten, wenn bereits eine Prerelease läuft; eine stabile Installation
sieht nur stabile Releases. Ältere Versionen werden nie als Update angezeigt.

### 3.1 Laufende Services

| Service | Aufgabe | Hinweise |
|---------|---------|----------|
| `backend` | API | `restart: unless-stopped` |
| `worker` | Celery-Tasks | `restart: unless-stopped` |
| `beat` | Periodische Jobs (`celery_app.beat_schedule`: Kalender-Sync, Erinnerungen, Draft-Generierung, Lueckenscan, ...) | **Genau eine Instanz** — jede weitere Replik loest jeden Job erneut aus; nie mit `--scale beat=N` skalieren. Schedule-Datei im Volume `beat_schedule`. |
| `frontend`, `db`, `valkey` | Web, Datenbank, Rate-Limiting | `restart: unless-stopped` |
| `migrate` | One-shot-Migration | Kein Restart; Runtime-Services starten erst nach Erfolg |
| `db-test` | Nur lokale Tests | Profil `test`: `docker compose --profile test up -d db-test` |

Worker und Beat pruefen beim Start den Alembic-Head und beenden sich bei Abweichung. Pruefen, dass Beat laeuft: `docker compose logs beat | grep "beat: Starting"`.

### 3.2 Image-Tags

Pushes auf `main`/`develop` veroeffentlichen nur `<branch>`- und `sha-<commit>`-Tags. `latest`, `<major>` und `<major>.<minor>` setzt ausschliesslich der Release-Workflow fuer stabile Releases (keine Prereleases). Produktion pinnt eine Release-Version, nicht `main`.

### 3.3 Backend startet nicht: `password authentication failed for user "nak_app"`

Das Backend bricht beim Start mit `Could not read database schema version from alembic_version` ab, in der Ursache steht `password authentication failed for user "nak_app"`. Das passiert nach dem Upgrade einer Installation, die vor der Rollentrennung (Laufzeit-Benutzer `nak_app`, Besitzer `nak`) aufgesetzt wurde: Die Migration `0016_create_app_role` setzt das Passwort aus `APP_DB_PASSWORD` nur **einmal**, wenn sie erstmals läuft. `migrate` hat danach nichts mehr zu tun und setzt es nicht neu. Rolle und Rechte sind in Ordnung, nur das Passwort stimmt nicht mit der `.env` überein.

Passwort als Owner nachsetzen (interaktiv, die Eingabe erscheint weder im Terminal noch in der Shell-Historie):

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
\password nak_app
\q
docker compose up -d --force-recreate backend worker beat
```

Das Passwort muss exakt `APP_DB_PASSWORD` aus der `.env` entsprechen. Wird `APP_DB_PASSWORD` geändert, in der Datenbank und in der `.env` gemeinsam ändern und die Dienste mit `up -d --force-recreate` neu erzeugen; `docker compose restart` liest die `.env` nicht neu ein. Am einfachsten sind Passwörter ohne Sonderzeichen (`openssl rand -hex 24`), weil sie in der Datenbank-URL stehen.

## 4. Rollback

1. Fehlerbild und betroffene Version dokumentieren.
2. Auf das letzte stabile Release zurueckrollen. Hat das fehlerhafte Release bereits migriert, startet das aeltere Image nicht (Schema-Guard, fail closed): zuerst Backup einspielen oder mit dem neueren Image `alembic downgrade <revision>` ausfuehren.
3. Datenbank nur dann zurueckrollen/restaurieren, wenn die Migration nicht vorwaertskompatibel ist und ein validiertes Backup vorliegt.
4. Health- und Smoke-Tests wiederholen.
5. Ursache und Folgemassnahmen dokumentieren.

## 5. Backup und Restore

Zielwerte: RPO maximal 24 Stunden, RTO maximal 4 Stunden.

### 5.1 Backup

```bash
BACKUP_ENCRYPT_KEY=<gpg-recipient> ./scripts/backup.sh
```

- `pg_dump -Fc` wird verschluesselt abgelegt.
- Standard-Retention: 30 Tage (`BACKUP_RETENTION_DAYS`).
- `BACKUP_DIR` muss zusaetzlich extern gesichert werden.

### 5.2 Restore

```bash
./scripts/restore.sh <backup>.dump.gpg --dry-run
./scripts/restore.sh <backup>.dump.gpg
```

Der Dry-Run validiert das Archiv ohne Datenveraenderung. Nach dem Restore folgen Health-Check und Smoke-Test.

### 5.3 Automatisierter Restore-Drill

`.github/workflows/restore-drill.yml` prueft Backup, GPG-Verschluesselung, Restore in eine getrennte PostgreSQL-18-Zieldatenbank, Datenvergleich und einen Korruptions-Negativtest. Ein erfolgreicher CI-Drill ersetzt nicht den vierteljaehrlichen Restore eines echten Produktionsbackups in Staging.

## 6. Monitoring und Security Operations

Mindestens ueberwachen:

- Container-Restarts und Health/Readiness
- OIDC-Erreichbarkeit und Tokenfehler
- Datenbank- und Valkey/Redis-Erreichbarkeit
- Audit- und Autorisierungsfehler
- Rate-Limiter-Fallbacks
- Backup-/Restore-Fehler

### 6.1 Rate-Limiter-Fallback

Normale Routen koennen bei Valkey-Ausfall gemaess Betriebsstrategie weiterlaufen; der OIDC-Token-Exchange (`POST /api/v1/auth/oidc/token`, 30/min) und die oeffentliche Selbstregistrierung (`POST /api/v1/districts/{id}/registrations`, 10/min) werden waehrend eines Fail-Open durch einen lokalen Fallback-Limiter je Client-Identitaet begrenzt. Dieser Limiter ist **pro Prozess**: Die effektive Grenze betraegt `Limit × Worker-Prozesse × Backend-Replikas`, und der Zaehler beginnt bei jedem Neustart wieder bei null. Er ist eine Notbremse, kein Ersatz fuer den Valkey-Limiter. Jeder Fallback muss operational sichtbar sein und als Degradation beobachtet werden.

Bei einem Fallback-Ereignis:

1. Valkey-Erreichbarkeit, DNS, Credentials und Connection-Limits pruefen.
2. Backend-Logs/Metriken korrelieren.
3. Nach Wiederherstellung kontrollierten Request ausfuehren und weitere Fallbacks ausschliessen.
4. Ursache und Dauer im Betriebstagebuch dokumentieren.

### 6.2 Secrets

- Secrets nur ueber Secret-Management bereitstellen, niemals committen.
- `SECRET_KEY`, OIDC-Client-Secret und Provisioning-Credentials regelmaessig rotieren.
- Eine `SECRET_KEY`-Rotation kann bestehende verschluesselte Anwendungsdaten/Sessions beeinflussen und muss geplant erfolgen.

### 6.3 OIDC-Session-Schutz

Provider-Refresh-Credentials duerfen nicht in JavaScript-zugaenglichem persistentem Speicher liegen. Der RC-2-Zielstand haelt die Refresh-Credential serverseitig in einem Secure/HttpOnly/SameSite-Cookie; die SPA haelt nur kurzlebige Access-/ID-Sessiondaten im Speicher und kann eine Session ueber den serverseitigen Refresh-Pfad wiederherstellen.

## 7. Release-Disziplin

Produktive Deployments erfolgen aus versionierten Releases. Vor einem Release Candidate muessen alle verpflichtenden Status Checks auf dem finalen Head erfolgreich sein.

### 7.1 Aktives `main`-Ruleset

Ruleset `main` (ID `13623643`) ist aktiv. Es erzwingt Pull Requests, strict Required Status Checks, verhindert Branch-Loeschung und Non-Fast-Forward-Updates und besitzt keinen Bypass-Akteur.

Aktuell verpflichtende Check-Namen:

- `Backend — Unit Tests & Coverage`
- `Encrypted Backup & Isolated Restore`
- `Frontend Dependency Audit (bun audit)`
- `Frontend — E2E Tests`
- `Frontend — Unit Tests`
- `Migration Graph & FK Names`
- `Dependency Review`
- `Python Dependency Audit (pip-audit)`
- `CodeQL Analysis (javascript-typescript)`
- `CodeQL Analysis (python)`
- `MegaLinter`
- `Build Backend Image`
- `Build Frontend Image`
- `Build documentation`

`Backend — Unit Tests & Coverage` muss die Projektgrenze von mindestens 80 Prozent einhalten. Der Frontend-Unit-Job muss die reale Production-Source-Coverage ebenfalls mit mindestens 80 Prozent fuer Statements, Branches, Functions und Lines durchsetzen.

Das Ruleset verlangt derzeit `0` approving Reviews und keine verpflichtende Review-Thread-Aufloesung. Das ist fuer RC-2 kein technischer CI-Blocker, bleibt aber ein Governance-Haertungspunkt vor dem finalen 1.0.0-Release (mindestens eine Freigabe, stale-review dismissal und Thread-Resolution pruefen).

### 7.2 Release-Gate

Vor RC-2 pruefen:

1. alle oben genannten Required Checks auf dem finalen Head erfolgreich;
2. Backend- und Frontend-Coverage jeweils >80 Prozent ohne kuenstliche Production-Code-Ausnahmen;
3. Migration/Restore-Drill erfolgreich;
4. CodeQL und Dependency Audits ohne blockierende Findings;
5. OpenSpec-Changes fuer den Releaseumfang verifiziert und erledigte Changes archiviert;
6. Architektur- und Security-Dokumentation entspricht dem ausgelieferten Code.


## Calendar sync diagnostics (#470)

Celery uses VALKEY_URL as its Redis-protocol broker and result backend. The
calendar sync task has a 240-second soft limit, 300-second hard limit, late task ACKs and
prefetch multiplier 1. Valkey availability is required for dispatch and results.

For a calendar integration, `last_attempt_at` denotes the latest scheduled or
started attempt, `last_synced_at` the most recent successful run, and
`last_sync_error` a sanitized failure class. Failed event changes roll back,
while the error is committed separately. Success clears the error.

Beat avoids scheduling a second retry chain for at least 30 minutes after a
failed attempt. Running integrations are protected by a transaction-scoped
`pg_try_advisory_xact_lock`; a busy lock causes an immediate logged skip.
Manual triggers still use the lock but bypass Beat's cooldown. Check logs for
`Calendar sync skipped` and `Calendar sync failed` when investigating errors.


## Upgrade: SQL-Celery-Broker auf Valkey umstellen (#470)

Der bisherige PostgreSQL-Kombu-Broker kann noch nicht verarbeitete Nachrichten in
`public.kombu_message` enthalten. Die neue Celery-Version liest ausschließlich
Valkey. **Vor dem Upgrade** müssen deshalb alte Aufträge abgearbeitet werden.

1. Vor dem Umschalten den **alten Beat-Prozess anhalten**, damit keine neuen SQL-Aufträge entstehen. Die alten SQL-basierten Worker zunächst weiterlaufen lassen.
2. Mit einer Datenbankverbindung mit Leserecht auf `kombu_message` prüfen:
   `SELECT COUNT(*) FROM public.kombu_message;` Die Zahl muss **0** sein.
   Auch unsichtbare/reservierte Einträge zählen: Sie dürfen bei einer Umstellung nicht verloren gehen.
3. Wenn Nachrichten verbleiben, die alten Worker weiterarbeiten lassen und laufende Aufgaben abschließen. Zustellung, Fehler und Wiederholungsversuche anhand der alten Worker-Logs abgleichen. Bei festhängenden Aufgaben die Arbeit anhand des bestehenden fachlichen Status sicher wiederherstellen; SQL-Nachrichten nicht blind löschen oder ungeprüft in Valkey importieren, insbesondere nicht für E-Mails.
4. **Erst bei leerer Tabelle** alte Worker stoppen, das Datenbank-Backup anfertigen, Migrationen ausführen und die neuen Valkey-Worker und Beat starten.
5. Kontrollieren, dass keine Nachricht verloren ging (insbesondere E-Mail-Aufträge und synchronisierte Kalender). Bei nicht leerem Legacy-Broker verweigern neue Worker und Beat den Start mit einem eindeutigen Fehler.

Die Tabellen bleiben vorerst zur forensischen Prüfung bestehen; ein Downgrade darf keine wartenden Aufträge still löschen.

## 4. Container-Haertung und Valkey-Zugang

Mit Issue #472 laufen Frontend, Backend, Worker, Beat und der Migrationsschritt im
veroeffentlichten Produktions-Compose mit schreibgeschuetztem Root-Dateisystem,
ohne Linux-Capabilities und mit begrenzten PIDs und Speicherkontingenten.
Schreibbare Pfade sind ausschliesslich tmpfs (`/tmp`) und das
`beat_schedule`-Volume. Nicht jeder Datenbank- und Proxy-Dienst ist
`read_only`: PostgreSQL, Valkey, Keycloak und Traefik benoetigen schreibbare
Daten-, Cache- oder Zertifikatsverzeichnisse. Ihre Netz- und Secret-Grenzen
bleiben bestehen. Das interne Nginx lauscht unprivilegiert auf Port 8080;
nur der externe Proxy nimmt HTTPS auf 443 an.

Vor dem Deployment `VALKEY_PASSWORD` in `.env` auf einen neuen, URL-sicheren
Zufallswert setzen, zum Beispiel mit `openssl rand -hex 32`. Der
`production_guard` verweigert den Start bei fehlendem oder bekannten
Standardwerten von `APP_DB_PASSWORD` und `VALKEY_PASSWORD` sowie bei
URL-reservierten und nicht-ASCII-Zeichen im Valkey-Passwort. Zulaessig sind
Buchstaben, Ziffern, Punkt, Unterstrich, Tilde und Bindestrich.
Die Valkey-Start- und Healthcheck-Kommandos verwenden die geschuetzte
Variablenexpansion im Container statt das Passwort als Shell-Code einzusetzen.
`.env.docker` setzt daraus eine authentifizierte `VALKEY_URL` fuer
API, Worker und Beat. **Bestehende Valkey-Nachrichten und Celery-Jobs
vor einem Passwortwechsel auslaufen lassen oder die Credentials bei
einem Rolling Update koordiniert umstellen.** Das Passwort wird fuer den
Valkey-Prozess als Environment-Wert konfiguriert: Nur befugte Betreiber
duerfen Docker-Metadaten und Compose-Dateien lesen. Nie `.env` committen.

`services/frontend/.dockerignore` und
`services/backend/.dockerignore` schliessen lokale Env-Dateien,
Abhaengigkeiten und Build-Artefakte von Image-Build-Kontexten aus.
`index.html` und `sw.js` werden nicht zwischengespeichert.
Direkte `/api/*`- und `/health`-Navigationen sind vom PWA-App-Shell-Fallback
ausgenommen. Die bestehende CSP erlaubt `style-src 'unsafe-inline'`
wegen der verwendeten UI-Styles und `img-src https:` fuer externe Bilder;
ein Entfernen erfordert vorherige Browser-/E2E-Regressionstests.

### Standalone-IDPs

Die separaten `idp-deploy/keycloak/`- und
`idp-deploy/authentik/`-Stacks erfordern gesetzte,
nicht-leere Credentials und HTTPS-Hostnamen. Bei Keycloak:
`KEYCLOAK_HOSTNAME=auth.example.org` und
`KC_BOOTSTRAP_ADMIN_PASSWORD` / `KEYCLOAK_DB_PASSWORD`.
Bei Authentik:
`AUTHENTIK_HOSTNAME=auth.example.org`,
`AUTHENTIK_SECRET_KEY` und `AUTHENTIK_POSTGRES_PASSWORD`.
Die Einstellungen aus `*.env.example` muessen ersetzt werden.
TLS endet am vorgeschalteten Reverse Proxy; HTTP der Backends bleibt intern.
Ein vorhandener Keycloak/Traefik wird gemaess
[Produktions-Compose](/operations/production-compose) eingebunden.

## 5. Backup inklusive Rollen und Wiederherstellung

`scripts/backup.sh` erstellt nun zwei zusammengehoerige Archive:
`<datenbank>_<zeit>.dump.gpg` (Schema und Daten) und
`<datenbank>_<zeit>.roles.sql.gpg` (globale Rollen, **ohne Passworthashes**).
Beide werden im verschluesselten Modus ueber Pipes erstellt; kein
unverschluesselter Dump wird auf dem Host zwischengespeichert.

Bei einer Wiederherstellung in einen **neuen, isolierten PostgreSQL-Cluster**
zuerst Rollen einspielen, **danach** das Datenbankarchiv wiederherstellen.
Die Rollenliste kann auch die urspruengliche Besitzerrolle enthalten.
Diese Rollen duerfen im Ziel nicht bereits existieren; fuer solche
Neuinstallationen eignet sich ein separater Bootstrap-Superuser.
Auf einem bestehenden Ziel Rollen selektiv und nach manueller
Konfliktpruefung einspielen.

```bash
gpg --decrypt backups/nak_planner_YYYYMMDD_HHMMSS.roles.sql.gpg \
  | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1
./scripts/restore.sh backups/nak_planner_YYYYMMDD_HHMMSS.dump.gpg --dry-run
./scripts/restore.sh backups/nak_planner_YYYYMMDD_HHMMSS.dump.gpg
```

Nach dem Restore unbedingt die Passwoerter fuer alle benoetigten Rollen
aus dem sicheren Secret-Store neu setzen (`\password nak_app` in psql)
und mit `APP_DB_PASSWORD` und `POSTGRES_PASSWORD` synchronisieren.
Die verschluesselte Rollen-SQL enthaelt bewusst keine Passwort-Hashes.
Vor Freigabe Daten, Alembic-Revision, RLS-Policies,
`SECURITY DEFINER`-Funktionen, Grants und Anwendungsgesundheit pruefen.
Der CI-Restore-Drill startet jetzt mit einem migrierten Quell-Schema und
prueft die Wiederherstellung dieser Sicherheitsmerkmale in einem
unabhaengigen Ziel-Cluster. Die Probe-Tabelle und der Test gegen
beschaedigte Archive bleiben erhalten.
