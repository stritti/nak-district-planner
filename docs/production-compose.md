# Produktiver Betrieb mit Traefik und Keycloak

`docker-compose.prod.yml` startet den kompletten Produktions-Stack auf einem einzelnen Docker-Host:

- **Traefik** terminiert TLS mit Let's Encrypt und routet nach Hostnamen.
- **Keycloak** ist der OIDC-Provider und hat eine eigene Datenbank.
- **NAK District Planner** läuft aus den **veröffentlichten GHCR-Images**: Frontend, Backend, Worker, Beat und der Migrationsschritt. Auf dem Server wird nichts gebaut.

Für die Entwicklung bleibt `docker-compose.yml` (mit `docker-compose.override.yml`) unverändert.

## Architektur

```text
Internet ──80/443──> traefik ──┬─ Host(APP_HOST)  ──> frontend (nginx) ──/api──> backend ──┬─ db (PostgreSQL)
                               │                                                          └─ valkey
                               └─ Host(AUTH_HOST) ──> keycloak ──> keycloak-db
                                  /admin, /realms/master nur aus KEYCLOAK_ADMIN_ALLOWED_IPS
```

| Netz | Mitglieder | Zweck |
|---|---|---|
| `edge` (fest `172.30.250.0/24`) | traefik, frontend, keycloak | Proxy-Hop. nginx (`NGINX_REAL_IP_FROM`) und Keycloak (`KC_PROXY_TRUSTED_ADDRESSES`) vertrauen nur diesem Netz. |
| `app` (fest `172.30.251.0/24`) | traefik, frontend, backend, worker, beat | API-Verkehr und ausgehender Internetzugang (OIDC, Kalender-Sync, SMTP). Traefik ist hier unter `AUTH_HOST` erreichbar, damit das Backend Keycloak ohne Umweg über das Internet findet. |
| `data` (`internal`) | db, valkey, migrate, backend, worker, beat | Datenbank und Cache, ohne Route nach außen |
| `idp` (`internal`) | keycloak, keycloak-db, backend | Keycloak-Datenbank; Admin-API für das optionale IdP-Provisioning |

Sicherheitsregeln, die die Tests in `tests/unit/test_production_compose.py` absichern:

- Nur Traefik veröffentlicht Ports (80/443). Kein Container bekommt den Docker-Socket: Die Routen stehen statisch in `deploy/traefik/dynamic/` (`app.yml`, `keycloak.yml`), siehe `docs/security-baseline.md`.
- Jedes Secret erreicht nur den Container, der es braucht:
  - `.env.db` (PostgreSQL-Owner): nur `db` und `migrate`
  - `.env.keycloak`: nur `keycloak`
  - `.env.keycloak-db`: nur `keycloak-db`
- Die Laufzeitdienste starten erst nach dem einmaligen Migrationsschritt (siehe `docs/deployment-migrations.md`).
- Die Images werden über `APP_VERSION` auf ein Release festgelegt, nie `latest` oder `main`.
- Für alle Container gilt `no-new-privileges`, die Logs werden rotiert (5 × 10 MB).
- HSTS setzt Traefik. CSP und die übrigen Header setzt das Frontend-nginx.

## Voraussetzungen

- Docker Engine mit Compose v2
- Zwei DNS-Namen, die auf den Server zeigen, z. B. `planer.example.org` (`APP_HOST`) und `auth.example.org` (`AUTH_HOST`)
- Eingehende Ports 80 (ACME-HTTP-Challenge, Redirect) und 443
- SMTP-Zugang und ein GPG-Schlüssel für verschlüsselte Backups (vom `production_guard` erzwungen)
- Ein vorhandenes Release-Image in GHCR, z. B. `ghcr.io/stritti/nak-district-planner/backend:1.0.0-rc.2`.
  - Ist das Paket privat: vorher `docker login ghcr.io` mit einem Token mit Recht `read:packages`.

## Einrichtung

Auf dem Server werden nur die Compose-Datei, `deploy/`, `scripts/` und die Env-Vorlagen gebraucht. Am einfachsten ist ein Checkout eines Release-Tags, der `docker-compose.prod.yml` enthält. Das ist das erste Release nach `v1.0.0-rc.2`. Bis dahin `main` auschecken; die Images bleiben trotzdem über `APP_VERSION` auf ein Release festgelegt.

```bash
git clone --branch <Release-Tag oder main> https://github.com/stritti/nak-district-planner.git
cd nak-district-planner
cp .env.example .env
cp .env.db.example .env.db
cp .env.keycloak.example .env.keycloak
cp .env.keycloak-db.example .env.keycloak-db
chmod 600 .env .env.db .env.keycloak .env.keycloak-db
```

### 1. `.env`

Den Abschnitt „Production stack“ am Ende von `.env.example` einkommentieren und ausfüllen:

```dotenv
COMPOSE_FILE=docker-compose.prod.yml
APP_VERSION=1.0.0-rc.2
APP_HOST=planer.example.org
AUTH_HOST=auth.example.org
ACME_EMAIL=ops@example.org
KEYCLOAK_ADMIN_ALLOWED_IPS=203.0.113.10/32
```

Mit `COMPOSE_FILE` benutzen auch `docker compose ...`, `make migrate` und `scripts/backup.sh` die Produktionsdatei.

`ACME_EMAIL` ist optional; Let's Encrypt stellt auch ohne Kontaktadresse aus. `KEYCLOAK_ADMIN_ALLOWED_IPS` ist ebenfalls optional: Ohne Wert gilt `127.0.0.1/32`, die Adminkonsole ist dann von außen gesperrt.

Danach die Anwendungswerte setzen, wie in der Checkliste in `docs/production-runbook.md`, Abschnitt 1.1:

- `APP_ENV=production`
- `SECRET_KEY` (mindestens 32 Zeichen)
- `APP_DB_PASSWORD`
- `SMTP_*` und `EMAIL_FROM_ADDRESS`
- `BACKUP_ENCRYPT_KEY`
- `SUPERADMIN_SUB` vor der ersten Migration, siehe Runbook Abschnitt 2.1

Die OIDC-Werte (`OIDC_*`) gibt es erst nach Abschnitt 3. Mit `APP_ENV=production` lehnt die Anwendung Platzhalter ab; vorher startet also auch `migrate` nicht.

Die OIDC-URLs zeigen auf den öffentlichen Keycloak-Host:

```dotenv
OIDC_DISCOVERY_URL=https://auth.example.org/realms/nak/.well-known/openid-configuration
OIDC_CLIENT_ID=nak-planner
OIDC_CLIENT_SECRET=<aus Keycloak, Credentials-Tab>
```

### 2. Passwörter

Lange Zufallswerte setzen, z. B. mit `openssl rand -base64 32`:

- `.env.db`: `POSTGRES_PASSWORD` (Owner der Anwendungsdatenbank)
- `.env.keycloak`: `KC_BOOTSTRAP_ADMIN_PASSWORD` und `KC_DB_PASSWORD`
- `.env.keycloak-db`: `POSTGRES_PASSWORD`, **derselbe Wert** wie `KC_DB_PASSWORD`

### 3. Keycloak starten und einrichten

Zuerst nur Traefik und Keycloak starten (die Keycloak-Datenbank startet mit):

```bash
docker compose pull
docker compose up -d traefik keycloak
```

Traefik holt die Zertifikate beim ersten Aufruf der Hostnamen.

Mit den Overrides aus [Bestehenden Traefik oder Keycloak einbinden](#bestehenden-traefik-oder-keycloak-einbinden) nur die Dienste nennen, die der Stack noch selbst mitbringt. Compose startet einen per Profil abgeschalteten Dienst sonst trotzdem, sobald er im Befehl steht:

| Override | Startbefehl in diesem Schritt |
|---|---|
| keiner | `docker compose up -d traefik keycloak` |
| `existing-traefik.yml` | `docker compose up -d keycloak` |
| `existing-keycloak.yml` | entfällt; den Client im vorhandenen Keycloak anlegen (Schritte 3–4 unten) |
| beide | entfällt; wie bei `existing-keycloak.yml` |

1. `https://<AUTH_HOST>/admin/` aus einem Netz in `KEYCLOAK_ADMIN_ALLOWED_IPS` öffnen und mit dem Bootstrap-Admin anmelden.
2. Einen dauerhaften Admin-Benutzer im Realm `master` anlegen, dann den Bootstrap-Admin löschen. Danach `KC_BOOTSTRAP_ADMIN_*` aus `.env.keycloak` entfernen.
3. Realm `nak` anlegen und darin einen Client `nak-planner`:
   - Client authentication: **an** (confidential; das Backend tauscht den Code mit dem Secret)
   - Standard flow: an
   - PKCE-Methode: `S256`
   - Valid redirect URIs: `https://<APP_HOST>/auth/callback`
   - Valid post logout redirect URIs: `https://<APP_HOST>/*`
   - Web origins: `https://<APP_HOST>`
   - Unter *Client scopes → nak-planner-dedicated* einen Mapper **Audience** hinzufügen:
     - Included Client Audience: `nak-planner`
     - Add to access token: an

     Ohne diesen Mapper enthält das Access-Token nur `aud=account`. Das Backend lehnt dann jede API-Anfrage mit 401 ab, obwohl die Anmeldung klappt.
4. Das Client-Secret in `.env` als `OIDC_CLIENT_SECRET` eintragen, dazu `OIDC_DISCOVERY_URL` und `OIDC_CLIENT_ID` (siehe Abschnitt 1).

Optional kann das Backend freigegebene Registrierungen direkt in Keycloak anlegen („IdP-Provisioning“). Es spricht die Admin-API dann intern an, ohne den Umweg über Traefik und die Admin-Allowlist. Es meldet sich mit einem Benutzer des Realms `master` an (Client `admin-cli`). Dafür einen eigenen Benutzer anlegen, nicht den Bootstrap-Admin:

1. Im Realm `master` einen Benutzer `nak-provisioning` mit Passwort anlegen.
2. Unter *Role mapping → Assign role → Client roles* nur die Rolle `manage-users` des Clients `nak-realm` zuweisen. Das reicht zum Suchen und Anlegen von Benutzern im Realm `nak`; andere Realms bleiben gesperrt.
3. Einladungs-Mails versendet Keycloak selbst, nicht die Anwendung. Dafür im Realm `nak` unter *Realm settings → Email* einen SMTP-Server und eine Absenderadresse eintragen. Ohne SMTP legt Keycloak den Benutzer zwar an, die Einladung scheitert aber, und die Freigabe wird als fehlgeschlagen protokolliert. Wer keine Einladungs-Mails will, setzt `IDP_PROVISIONING_KEYCLOAK_INVITE_ON_APPROVAL=false`.

Der `production_guard` verlangt alle vier Keycloak-Werte:

```dotenv
IDP_PROVISIONING_ENABLED=true
IDP_PROVISIONING_PROVIDER=keycloak
IDP_PROVISIONING_KEYCLOAK_BASE_URL=http://keycloak:8080
IDP_PROVISIONING_KEYCLOAK_REALM=nak
IDP_PROVISIONING_KEYCLOAK_ADMIN_USERNAME=nak-provisioning
IDP_PROVISIONING_KEYCLOAK_ADMIN_PASSWORD=<langes Zufallspasswort>
```

Details zu Rollen, Mappern und Fehlerbildern stehen in `idp-deploy/keycloak/OIDC-SETUP.md`.

### 4. Anwendung starten

```bash
docker compose up -d
docker compose ps
```

`migrate` läuft einmal durch und beendet sich. Danach starten Backend, Worker, Beat und Frontend.

## Update auf eine neue Version

```bash
# in .env: APP_VERSION=<neue Version>
docker compose pull
docker compose up -d
```

`migrate` läuft vor den Laufzeitdiensten automatisch mit. Vorher beide Datenbanken sichern (Abschnitt „Backup“).

## Backup

`scripts/backup.sh` sichert die Anwendungsdatenbank und verschlüsselt sie mit `BACKUP_ENCRYPT_KEY` aus `.env` (Runbook Abschnitt 4).

Realm, Benutzer und Client-Konfiguration liegen in der Keycloak-Datenbank. Sie wird mit demselben Skript gesichert, nur mit anderem Container und anderen Zugangsdaten (Werte aus `.env.keycloak-db`):

```bash
./scripts/backup.sh
DB_CONTAINER="$(docker compose ps -q keycloak-db)" POSTGRES_USER=keycloak POSTGRES_DB=keycloak ./scripts/backup.sh
```

Die Dateien landen in `backups/` (`nak_planner_*.dump.gpg`, `keycloak_*.dump.gpg`). Beide regelmäßig sichern, z. B. per Cron, und außerhalb des Servers aufbewahren.

Wiederherstellen geht genauso mit `scripts/restore.sh`; vorher Keycloak stoppen:

```bash
docker compose stop keycloak
DB_CONTAINER="$(docker compose ps -q keycloak-db)" POSTGRES_USER=keycloak POSTGRES_DB=keycloak \
  ./scripts/restore.sh backups/keycloak_<Zeitstempel>.dump.gpg
docker compose start keycloak
```

Mit `existing-keycloak.yml` entfällt das; dann sichert der Betreiber des vorhandenen Keycloak.

Rollback: `APP_VERSION` zurücksetzen. Das klappt nur, wenn die neue Version keine Migrationen mitgebracht hat; sonst gilt der Restore-Pfad aus dem Runbook.

## Prüfen nach dem Deployment

```bash
curl -I http://<APP_HOST>/                 # 301 nach https
curl -s https://<APP_HOST>/health          # Backend-Health über nginx
curl -sI https://<APP_HOST>/ | grep -i strict-transport-security
curl -s https://<AUTH_HOST>/realms/nak/.well-known/openid-configuration | grep issuer
curl -o /dev/null -w '%{http_code}\n' https://<AUTH_HOST>/admin/   # 403 von außerhalb der Allowlist
```

Das Backend prüft die Token gegen `https://<AUTH_HOST>/realms/nak`. Der Issuer in der Discovery-Antwort muss **genau** diese URL sein. Keycloak leitet sie aus `KC_HOSTNAME` ab.

## Bestehenden Traefik oder Keycloak einbinden

Läuft auf dem Server schon ein Traefik oder ein Keycloak, ersetzen zwei Override-Dateien in `deploy/compose/` den jeweils mitgelieferten Dienst. Sie werden über `COMPOSE_FILE` zugeschaltet (Trenner `:`) und brauchen Docker Compose ≥ 2.24.4 (`!override`).

| Vorhanden auf dem Server | `COMPOSE_FILE` in `.env` |
|---|---|
| nichts (Standard) | `docker-compose.prod.yml` |
| Keycloak | `docker-compose.prod.yml:deploy/compose/existing-keycloak.yml` |
| Traefik | `docker-compose.prod.yml:deploy/compose/existing-traefik.yml` |
| beides | `docker-compose.prod.yml:deploy/compose/existing-keycloak.yml:deploy/compose/existing-traefik.yml` |

Prüfen, was tatsächlich startet: `docker compose config --services`

### Vorhandener Keycloak (oder anderer OIDC-Provider)

`deploy/compose/existing-keycloak.yml` legt `keycloak` und `keycloak-db` hinter das Profil `bundled-keycloak`, damit sie nicht starten. Außerdem:
- Der mitgelieferte Traefik bekommt die Keycloak-Routen (`keycloak.yml`) nicht.
- Der interne Alias `AUTH_HOST` → Traefik entfällt, damit das Backend den echten Provider über DNS erreicht.
- Das Backend verlässt das `idp`-Netz.

1. `AUTH_HOST` auf den Hostnamen des vorhandenen Providers setzen (z. B. `sso.example.org`).
2. Im vorhandenen Keycloak einen Client `nak-planner` anlegen, wie in Abschnitt „3. Keycloak starten und einrichten“ beschrieben (einschließlich Audience-Mapper), und `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID` und `OIDC_CLIENT_SECRET` in `.env` eintragen.
3. Der Issuer in der Discovery-Antwort muss über HTTPS mit einem öffentlich gültigen Zertifikat erreichbar sein. Das Backend prüft TLS und übernimmt den Issuer aus der Discovery-Antwort.
4. `.env.keycloak` und `.env.keycloak-db` werden nicht gebraucht.
5. Für das IdP-Provisioning die Admin-API des vorhandenen Keycloak verwenden (`IDP_PROVISIONING_KEYCLOAK_BASE_URL=https://sso.example.org`) und dort einen Benutzer im Realm `master` mit der Rolle `manage-users` des Clients `<Realm>-realm` anlegen, wie oben beschrieben. Für Einladungs-Mails braucht der Realm einen SMTP-Server.

### Vorhandener Traefik

`deploy/compose/existing-traefik.yml` legt den mitgelieferten Traefik hinter das Profil `bundled-traefik`, damit er nicht startet. Frontend und Keycloak hängen sich an das externe Netz des vorhandenen Traefik und veröffentlichen ihre Routen über **Docker-Labels**: App, Keycloak, Admin-Allowlist (`/admin`, Realm `master`) und HSTS, genau wie im mitgelieferten Stack.

Voraussetzungen am vorhandenen Traefik:
- Docker-Provider aktiv, am besten mit `exposedByDefault=false`
- ein HTTPS-Entrypoint
- ein ACME-Resolver
- ein externes Docker-Netz, an das er angeschlossen ist

Die Namen in `.env` angeben, falls sie von den Defaults abweichen:

```dotenv
TRAEFIK_NETWORK=traefik_net          # externes Netz des vorhandenen Traefik
TRAEFIK_ENTRYPOINT=websecure         # HTTPS-Entrypoint
TRAEFIK_CERTRESOLVER=letsencrypt     # ACME-Resolver
TRAEFIK_PROXY_SUBNET=172.18.0.0/16   # Subnetz von TRAEFIK_NETWORK
```

So findest du das Subnetz heraus:

```bash
docker network inspect traefik_net --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

Wichtig für die Vertrauenskette der Client-IP und der Forwarded-Header:
- Keycloak vertraut Forwarded-Headern nur aus `TRAEFIK_PROXY_SUBNET` (Default `172.16.0.0/12`).
- Das Frontend-nginx übernimmt die Client-IP nur von `NGINX_REAL_IP_FROM` (Default `127.0.0.1/32 172.16.0.0/12`). Liegt das Traefik-Netz außerhalb davon, z. B. in `192.168.0.0/16`, beide Werte in `.env` setzen. Sonst teilen sich alle Nutzer die Proxy-IP und damit einen Rate-Limit-Bucket.
- Der vorhandene Traefik muss das `X-Forwarded-For` von Clients verwerfen, nicht übernehmen. Das ist der Default ohne `forwardedHeaders.trustedIPs`.

Der Docker-Socket gehört hier dem vorhandenen Traefik; dieser Stack mountet ihn weiterhin nicht. Arbeitet der vorhandene Traefik nur mit dem File-Provider, statt der Labels die Dateien aus `deploy/traefik/dynamic/` in dessen Konfiguration übernehmen:
- Hostnamen eintragen
- Service-URLs auf `http://nak-frontend:80` und `http://nak-keycloak:8080` ändern; das sind die eindeutigen Aliase im gemeinsamen Netz.

Das Backend erreicht `AUTH_HOST` ohne den mitgelieferten Traefik über das öffentliche DNS, also über den Router des Servers. Unterstützt das Netz kein Hairpin-NAT, `AUTH_HOST` per `extra_hosts` auf den Host zeigen lassen, z. B. in einer weiteren Override-Datei:

```yaml
services:
  backend:
    extra_hosts:
      - "${AUTH_HOST}:host-gateway"
```

Das funktioniert nur, wenn Keycloak hinter demselben Traefik läuft.

## Hinweise

- **Lokaler Test ohne öffentliches DNS:** Ohne erreichbare Hostnamen kann Let's Encrypt kein Zertifikat ausstellen; Traefik liefert dann ein selbstsigniertes. Das Backend lehnt dieses Zertifikat bei der OIDC-Discovery bewusst ab, die TLS-Prüfung bleibt also an.
- **Client-IP:** Ein Client kann die Adresse für Rate-Limiting und Audit-Log nicht fälschen:
  - Traefik verwirft ein vom Client mitgeschicktes `X-Forwarded-For`.
  - nginx übernimmt die Client-IP nur vom `edge`-Netz.
  - Das Backend vertraut nur nginx (`TRUSTED_PROXIES`, Default `172.16.0.0/12`). `EDGE_SUBNET` und `APP_SUBNET` müssen deshalb innerhalb dieses Bereichs bleiben.
- **Zusätzliche Härtung** (Read-only-Root-Filesystem, unprivilegiertes nginx, Valkey-Passwort) ist in #472 geplant.
