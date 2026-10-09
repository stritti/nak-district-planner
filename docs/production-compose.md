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

- Nur Traefik veröffentlicht Ports (80/443). Kein Container bekommt den Docker-Socket: Die Routen stehen statisch in `deploy/traefik/dynamic/routes.yml`, siehe `docs/security-baseline.md`.
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

Auf dem Server werden nur die Compose-Datei, `deploy/` und die Env-Vorlagen gebraucht. Am einfachsten ist ein Checkout des Release-Tags:

```bash
git clone --branch v1.0.0-rc.2 https://github.com/stritti/nak-district-planner.git
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

Danach die Anwendungswerte setzen, wie in der Checkliste in `docs/production-runbook.md`, Abschnitt 1.1:

- `APP_ENV=production`
- `SECRET_KEY` (mindestens 32 Zeichen)
- `APP_DB_PASSWORD`
- `SMTP_*` und `EMAIL_FROM_ADDRESS`
- `BACKUP_ENCRYPT_KEY`
- `SUPERADMIN_SUB` vor der ersten Migration, siehe Runbook Abschnitt 2.1

Für die OIDC-Werte (`OIDC_*`) zuerst Keycloak einrichten (Abschnitt 4).

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

### 3. Start

```bash
docker compose pull
docker compose up -d
docker compose ps
```

Der Ablauf beim Start:
1. `migrate` läuft einmal durch und beendet sich.
2. Danach starten Backend, Worker, Beat und Frontend.
3. Traefik holt die Zertifikate beim ersten Aufruf der Hostnamen.

### 4. Keycloak einrichten

1. `https://<AUTH_HOST>/admin/` aus einem Netz in `KEYCLOAK_ADMIN_ALLOWED_IPS` öffnen und mit dem Bootstrap-Admin anmelden.
2. Einen dauerhaften Admin-Benutzer im Realm `master` anlegen, dann den Bootstrap-Admin löschen. Danach `KC_BOOTSTRAP_ADMIN_*` aus `.env.keycloak` entfernen.
3. Realm `nak` anlegen und darin einen Client `nak-planner`:
   - Client authentication: **an** (confidential; das Backend tauscht den Code mit dem Secret)
   - Standard flow: an
   - PKCE-Methode: `S256`
   - Valid redirect URIs: `https://<APP_HOST>/auth/callback`
   - Valid post logout redirect URIs: `https://<APP_HOST>/*`
   - Web origins: `https://<APP_HOST>`
4. Das Client-Secret in `.env` als `OIDC_CLIENT_SECRET` eintragen und die Anwendung neu starten: `docker compose up -d backend worker beat`

Optional kann das Backend freigegebene Registrierungen direkt in Keycloak anlegen („IdP-Provisioning“). Es spricht die Admin-API dann intern an, ohne den Umweg über Traefik und die Admin-Allowlist:

```dotenv
IDP_PROVISIONING_ENABLED=true
IDP_PROVISIONING_PROVIDER=keycloak
IDP_PROVISIONING_KEYCLOAK_BASE_URL=http://keycloak:8080
IDP_PROVISIONING_KEYCLOAK_REALM=nak
```

Details zu Rollen, Mappern und Fehlerbildern stehen in `idp-deploy/keycloak/OIDC-SETUP.md`.

## Update auf eine neue Version

```bash
# in .env: APP_VERSION=<neue Version>
docker compose pull
docker compose up -d
```

`migrate` läuft vor den Laufzeitdiensten automatisch mit. Vorher ein Backup ziehen (`scripts/backup.sh`, Runbook Abschnitt 4).

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

## Hinweise

- **Lokaler Test ohne öffentliches DNS:** Ohne erreichbare Hostnamen kann Let's Encrypt kein Zertifikat ausstellen; Traefik liefert dann ein selbstsigniertes. Das Backend lehnt dieses Zertifikat bei der OIDC-Discovery bewusst ab, die TLS-Prüfung bleibt also an.
- **Client-IP:** Ein Client kann die Adresse für Rate-Limiting und Audit-Log nicht fälschen:
  - Traefik verwirft ein vom Client mitgeschicktes `X-Forwarded-For`.
  - nginx übernimmt die Client-IP nur vom `edge`-Netz.
  - Das Backend vertraut nur nginx (`TRUSTED_PROXIES`, Default `172.16.0.0/12`). `EDGE_SUBNET` und `APP_SUBNET` müssen deshalb innerhalb dieses Bereichs bleiben.
- **Zusätzliche Härtung** (Read-only-Root-Filesystem, unprivilegiertes nginx, Valkey-Passwort) ist in #472 geplant.
