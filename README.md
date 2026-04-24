# NAK Bezirksplaner

Planungswerkzeug für Gottesdienste und Veranstaltungen in NAK-Bezirken.
Verwaltet Gemeinden, Termine und Dienstzuweisungen; exportiert Kalender als ICS-Feed.

## Dokumentation

Die Projektdokumentation befindet sich unter `docs/`.

- Einstieg: `docs/documentation-map.md`
- Architekturstatus: `docs/architecture-status.md`
- Engineering Standards: `docs/engineering-standards.md`
- Security Baseline: `docs/security-baseline.md`
- Production Runbook: `docs/production-runbook.md`

Historische Inhalte wurden in die strukturierte Projektdokumentation ueberfuehrt.

---

## Voraussetzungen

| Tool | Mindestversion |
|------|---------------|
| Docker | 24+ |
| Docker Compose | v2 (Plugin, nicht Standalone) |
| Python | 3.11+ (nur für lokale Alembic-Migrationen außerhalb Docker) |
| bun | 1.x (nur für lokale Frontend-Entwicklung außerhalb Docker) |

---

## Entwicklung

### 1. Erstkonfiguration

```bash
cp .env.example .env
```

`.env` öffnen und die Platzhalter ersetzen:

```dotenv
POSTGRES_PASSWORD=ein-sicheres-passwort
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
API_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

> `DATABASE_URL` und `REDIS_URL` müssen nicht geändert werden — sie verweisen auf die
> Docker-internen Hostnamen (`db`, `redis`), die im Compose-Netzwerk aufgelöst werden.

---

### 2. Stack starten

```bash
docker compose up -d
```

`docker-compose.override.yml` wird automatisch zusammengeführt und aktiviert:

- **Hot-Reload** für Backend (`--reload`) und Worker
- Den Backend-Quellcode (`services/backend/app/`) als Volume-Mount, damit Änderungen
  sofort wirken ohne Rebuild
- Exponierte Ports für direkten Zugriff von außen:

| Service  | Port (Host) | Beschreibung |
|----------|-------------|--------------|
| Frontend | 80          | Vue-App via nginx |
| Backend  | 8000        | FastAPI (direkt erreichbar) |
| DB       | 5432        | PostgreSQL |
| Redis    | 6379        | Redis |

---

### 3. Datenbank-Migrationen

Beim ersten Start und nach jeder neuen Migrationsdatei:

```bash
docker compose run --no-deps --rm backend alembic upgrade head
```

Neue Migration erstellen (nach ORM-Änderungen):

```bash
docker compose run --no-deps --rm backend alembic revision --autogenerate -m "kurze beschreibung"
```

> Die Migrationsdatei wird unter `services/backend/alembic/versions/` erzeugt.
> Vor dem Commit immer prüfen, dass sie korrekt ist — Autogenerate erkennt z. B.
> keine Spalten-Reihenfolgeänderungen und keine serverseitigen Defaults.

Schneller per Makefile:

```bash
make migrate
```

---

### 3a. Testdaten seeden (Bezirke, Gemeinden, Amtsträger)

```bash
make seed
```

Optional ohne persistente Änderungen:

```bash
make seed-dry-run
```

---

### 4. Logs & Status

```bash
docker compose ps                  # Überblick aller Container
docker compose logs -f backend     # Backend-Logs (live)
docker compose logs -f worker      # Celery-Worker-Logs
docker compose logs -f frontend    # nginx-Logs
```

---

### 5. Backend-Tests

```bash
docker compose run --no-deps --rm backend pytest
docker compose run --no-deps --rm backend pytest tests/unit/
docker compose run --no-deps --rm backend pytest tests/integration/ -v
```

---

### 6. Lokale Entwicklung (ohne Docker für Frontend / Backend)

Auch bei lokaler Entwicklung werden **PostgreSQL** und **Redis** als Docker-Container benötigt:

```bash
docker compose up -d db redis
```

> Beim ersten Start ggf. vorher `cp .env.example .env` ausführen und die
> Platzhalter ersetzen (siehe [Erstkonfiguration](#1-erstkonfiguration)).
> Für die lokale Entwicklung `DATABASE_URL` und `REDIS_URL` auf `localhost`
> anpassen, z. B.:
>
> ```dotenv
> DATABASE_URL=postgresql+asyncpg://nak:<passwort>@localhost:5432/nak_planner
> REDIS_URL=redis://localhost:6379/0
> ```

#### Backend (Python / uv)

```bash
cd services/backend
uv sync                              # Abhängigkeiten installieren
uv run alembic upgrade head          # Migrationen anwenden
uv run uvicorn app.main:app --reload # http://localhost:8000
```

#### Frontend (bun / Vite)

Der Vite-Dev-Server proxyt `/api` automatisch auf `localhost:8000`
(Backend muss laufen):

```bash
cd services/frontend
bun install                          # Abhängigkeiten installieren
bun run dev                          # http://localhost:5173
bun run lint
```

#### Dokumentation (VitePress)

Die Projekt-Dokumentation basiert auf VitePress und befindet sich im Ordner `docs`.

```bash
bun install                          # Abhängigkeiten installieren (im Hauptverzeichnis)
bun run docs:dev                     # Entwicklungs-Server unter http://localhost:5173
bun run docs:build                   # Dokumentation bauen
```

---

### 7. Stack stoppen

```bash
docker compose down          # Container stoppen und entfernen
docker compose down -v       # zusätzlich Volumes löschen (DB-Daten weg!)
```

---

## Deployment (Produktion)

### Unterschied zu Entwicklung

In der Produktion wird **kein** `docker-compose.override.yml` eingebunden.
Das bedeutet:

- Kein Volume-Mount für den Quellcode (Code liegt im Image)
- Kein `--reload`; uvicorn läuft im stabilen Produktionsmodus
- Port 8000 ist **nicht** nach außen exponiert; der Zugriff erfolgt nur über nginx
- Port 5432 und 6379 sind **nicht** nach außen exponiert

### Ablauf

#### 1. Images bauen

```bash
docker compose -f docker-compose.yml build
```

> Explizit `-f docker-compose.yml` angeben, damit das Override nicht eingemischt wird.

#### 2. `.env` für Produktion befüllen

Auf dem Server eine `.env` anlegen — **niemals** die Dev-Werte übernehmen:

```dotenv
POSTGRES_USER=nak
POSTGRES_PASSWORD=<starkes-passwort>
POSTGRES_DB=nak_planner
DATABASE_URL=postgresql+asyncpg://nak:<passwort>@db:5432/nak_planner
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<64-zeichen-hex>
API_KEY=<64-zeichen-hex>
APP_ENV=production
```

Schlüssel erzeugen:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 3. Datenbank migrieren

```bash
docker compose -f docker-compose.yml run --no-deps --rm backend alembic upgrade head
```

#### 4. Stack starten

```bash
docker compose -f docker-compose.yml up -d
```

#### 5. Health-Check

```bash
curl http://localhost/api/health
# → {"status":"ok"}
```

---

### Reverse Proxy (empfohlen)

Für HTTPS und einen öffentlichen Domainnamen einen vorgelagerten nginx oder Caddy
einsetzen. Der interne nginx-Container lauscht auf Port 80 und übernimmt:

- Vue-SPA-Routing (`try_files $uri /index.html`)
- API-Proxy (`/api/` → `backend:8000`)

Beispiel-Konfiguration für einen vorgelagerten nginx:

```nginx
server {
    listen 443 ssl;
    server_name planer.example.de;

    ssl_certificate     /etc/letsencrypt/live/planer.example.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/planer.example.de/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:80;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
    }
}
```

---

### Updates einspielen

```bash
# 1. Neuen Code holen
git pull

# 2. Images neu bauen
docker compose -f docker-compose.yml build

# 3. Migrationen anwenden (falls neue Dateien vorhanden)
docker compose -f docker-compose.yml run --no-deps --rm backend alembic upgrade head

# 4. Stack neu starten (rollendes Neustarten ohne Downtime nicht ohne Orchestrator)
docker compose -f docker-compose.yml up -d
```

---

### Datensicherung

Die einzige persistente State-Quelle ist das PostgreSQL-Volume `postgres_data`.

```bash
# Backup erstellen
docker exec nak-district-planner-db-1 \
  pg_dump -U nak -d nak_planner -Fc \
  > backup_$(date +%Y%m%d_%H%M%S).dump

# Backup einspielen (Stack stoppen, dann:)
docker exec -i nak-district-planner-db-1 \
  pg_restore -U nak -d nak_planner --clean < backup.dump
```

---

## Projektstruktur (Kurzübersicht)

```text
nak-district-planner/
├── docker-compose.yml           # Produktion
├── docker-compose.override.yml  # Dev-Ergänzungen (automatisch)
├── .env.example                 # Vorlage — nach .env kopieren
└── services/
    ├── backend/                 # FastAPI + Celery (Python 3.11)
    │   ├── app/
    │   │   ├── domain/          # Pure-Python-Entitäten & Ports (ABCs)
    │   │   ├── application/     # Use Cases & Celery-Tasks
    │   │   └── adapters/        # FastAPI-Router, SQLAlchemy-Repos, Kalender
    │   ├── alembic/             # Datenbankmigrationen
    │   └── tests/
    └── frontend/                # Vue 3 + Tailwind (gebaut mit bun)
        └── src/
├── docs/                        # Projekt-Dokumentation (VitePress)
│   ├── .vitepress/              # Konfiguration und Themes
│   ├── index.md                 # Startseite
│   ├── getting-started.md       # Erste Schritte
│   └── use-cases.md             # Anwendungsfälle
```

## API-Nutzung (Kurzreferenz)

Alle Endpunkte unter `/api/v1/` erfordern den Header `X-API-Key`.

```bash
# Health (kein Key nötig)
curl http://localhost/api/health

# Event anlegen
curl -X POST http://localhost/api/v1/events \
  -H "X-API-Key: <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Gottesdienst",
    "start_at": "2026-03-08T09:30:00Z",
    "end_at":   "2026-03-08T11:00:00Z",
    "district_id": "<uuid>",
    "category": "Gottesdienst"
  }'

# Events auflisten
curl "http://localhost/api/v1/events?district_id=<uuid>&limit=50" \
  -H "X-API-Key: <api-key>"

# Eigenen Benutzer mit Amtstraeger verknuepfen (OIDC Bearer)
curl -X POST "http://localhost:8000/api/v1/districts/<district_id>/leaders/link-self" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"leader_id":"<leader_uuid>"}'

# Aktuelle eigene Zuordnung abfragen
curl -X GET "http://localhost:8000/api/v1/districts/<district_id>/leaders/link-self" \
  -H "Authorization: Bearer <token>"
```

Interaktive API-Dokumentation (nur Entwicklung): <http://localhost:8000/docs>

---

## Phase 4b: OIDC Authentication

NAK Planner supports OpenID Connect (OIDC) authentication with a choice of two identity providers:

- **Keycloak** — Mature, feature-rich Java-based IAM
- **Authentik** — Modern, lightweight Python-based authentication platform

Both support the **Authorization Code Flow with PKCE** for secure frontend authentication.

### Quick Start

#### 1. Choose an Identity Provider

**Option A: Keycloak** (recommended for enterprises)
```bash
cd idp-deploy/keycloak
docker compose up -d
python3 setup_keycloak_realm.py --keycloak-url http://localhost:8080 --admin-password admin_dev_pw
```

**Option B: Authentik** (recommended for simple setups)
```bash
cd idp-deploy/authentik
docker compose up -d
python3 setup_authentik_oauth2.py --authentik-url http://localhost:9000 --bootstrap-token akadmin:insecure
```

#### 2. Configure Frontend

Copy OIDC settings from setup script output to `services/frontend/.env.local`:

```env
VITE_OIDC_DISCOVERY_URL=http://localhost:8080/realms/nak-planner/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=nak-planner-frontend
VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback
```

#### 3. Start Frontend

```bash
cd services/frontend
bun install
bun run dev
```

Open <http://localhost:5173/login> and click "Login with OIDC"

Test credentials: `testuser` / `testpassword123`

### Production Deployment

#### Keycloak Production
```bash
bash idp-deploy/keycloak/deploy_keycloak.sh \
  /opt/keycloak \
  https://auth.example.com \
  your_secure_admin_password
```

#### Authentik Production
```bash
SECRET_KEY=$(openssl rand -base64 32)
bash idp-deploy/authentik/deploy_authentik.sh \
  /opt/authentik \
  https://auth.example.com \
  "$SECRET_KEY"
```

### Documentation

- **Detailed Configuration**: See `idp-deploy/CONFIGURATION.md`
- **Keycloak Setup**: See `idp-deploy/keycloak/OIDC-SETUP.md`
- **Authentik Setup**: See `idp-deploy/authentik/OIDC-SETUP.md`
- **Frontend OIDC**: See `services/frontend/src/composables/useOIDC.ts`

### Features

- ✅ **PKCE Flow** (RFC 7636) for secure SPAs
- ✅ **Automatic Token Refresh** (5 min before expiry)
- ✅ **401 Error Handling** with silent token refresh
- ✅ **Logout with Token Revocation**
- ✅ **JWT Token Parsing** for user claims
- ✅ **Session Storage** for PKCE verifier (auto-cleared on close)
- ✅ **IDP-Agnostic** (works with both Keycloak and Authentik)

### Erster Benutzer / Superadmin

- Wenn `SUPERADMIN_SUB` **gesetzt** ist, bekommt genau dieser OIDC-`sub` globale Superadmin-Rechte.
- Wenn `SUPERADMIN_SUB` **nicht gesetzt** ist, wird automatisch der **erste jemals angemeldete Benutzer** Superadmin.
- Superadmin darf alle Bezirks-/Gemeinde-Operationen ohne explizite Memberships ausführen.
