# Keycloak Deployment Guide

Keycloak ist ein separater Stack, der unabhängig vom NAK-Planner läuft und von mehreren Projekten wiederverwendet werden kann.

## Vorbedingungen

- VPS mit Docker + Docker Compose
- Traefik läuft bereits und managed `auth.5tritti.de`
- Traefik-Netzwerk heißt `traefik` (oder anpassen in `docker-compose.yml`)
- Python 3 (für automatisiertes Setup)

## Quick Start (Automatisiert)

Das ist die empfohlene Methode. Das Script führt einen Build-Schritt durch und konfiguriert alles automatisch:

```bash
# Auf dem VPS
cd /opt/keycloak-deploy  # oder anderer Ort
cp keycloak-deploy/* .

# Oder wenn du schon eine Kopie hast:
./deploy_keycloak.sh /opt/keycloak-deploy https://auth.5tritti.de <admin-password>
```

Das Script macht alles:
1. ✓ Keycloak Build (mit PostgreSQL-Optimierung)
2. ✓ Docker Compose Up
3. ✓ Wartet bis Keycloak ready ist
4. ✓ Erstellt Realm "nak-planner"
5. ✓ Erstellt Client "nak-planner-api"
6. ✓ Erstellt Test-User
7. ✓ Zeigt Client Secret (zum Copy-Paste)
8. ✓ Exportiert Realm-Config

**Nach dem Script:** Kopiere den angezeigten CLIENT_SECRET in deine NAK-Planner `.env`.

---

## Manual Setup (falls Automatisierung nicht funktioniert)

### Schritt 1: Keycloak-Stack vorbereiten

```bash
# Auf dem VPS
cd /opt/keycloak-deploy  # oder anderer Ort

# Option A: Aus Git
git clone <dein-repo> .

# Option B: Datei für Datei kopieren
cp keycloak-deploy/* /opt/keycloak-deploy/
```

### Schritt 2: Umgebungsvariablen setzen

```bash
cp .env.example .env
```

Bearbeite `.env` und setze starke Passwörter:

```bash
KEYCLOAK_ADMIN_PASSWORD=<starkes-passwort>
KEYCLOAK_DB_PASSWORD=<starkes-passwort>
```

### Schritt 3: Keycloak Build (Optimierung)

**Wichtig für Keycloak 26+:** Der Build-Schritt optimiert Keycloak für Deployment.

```bash
docker compose run --rm keycloak build --db=postgres
```

Dies wird vom automatisierten Script (`deploy_keycloak.sh`) bereits erledigt.

### Schritt 4: Docker-Compose starten

```bash
docker compose up -d
```

Verifiziere, dass Keycloak startet:

```bash
docker compose logs -f keycloak
```

Warte bis diese Nachricht erscheint:
```
Keycloak ... version X.X.X is now running
```

## Schritt 5: Keycloak Admin Console erreichbar?

Öffne in deinem Browser:
```
https://auth.5tritti.de/admin/
```

Login mit:
- Username: `admin` (oder `KEYCLOAK_ADMIN` aus `.env`)
- Password: `changeme` (oder `KEYCLOAK_ADMIN_PASSWORD` aus `.env`)

## Schritt 6: Realm erstellen

1. Klick auf "Keycloak" (oben links) → "Create Realm"
2. Name: `nak-planner`
3. Click "Create"

## Schritt 7: Client erstellen

1. Im Realm `nak-planner`: Geh zu "Clients"
2. Click "Create client"
3. Client ID: `nak-planner-api`
4. Client type: OpenID Connect
5. Next
6. Turn on: "Client authentication" (Confidential)
7. Click "Save"

### Redirect URIs konfigurieren

Im gerade erstellten Client → Tab "Settings":

**Valid redirect URIs:**
```
https://planner.5tritti.de/auth/callback
http://localhost:3000/auth/callback
```

**Valid post logout redirect URIs:**
```
https://planner.5tritti.de/
http://localhost:3000/
```

Save.

### Client Secret kopieren

Tab "Credentials" → Copy `Client secret`

Diesen Wert speicherst du für die NAK-Planner `.env`:
```
KEYCLOAK_CLIENT_SECRET=<copied-secret>
```

## Schritt 8: Test User erstellen

1. Im Realm `nak-planner`: Geh zu "Users"
2. Click "Add user"
3. Username: `test`
4. Email: `test@example.com`
5. Email verified: ON
6. Save

### Password setzen

Im gerade erstellten User → Tab "Credentials":
- Click "Set password"
- Password: `test-password`
- Temporary: OFF
- Save

## Schritt 9: JWKS-Endpoint verifizieren

Öffne in deinem Browser oder curl:

```bash
curl https://auth.5tritti.de/realms/nak-planner/.well-known/jwks.json
```

Du solltest ein JSON mit `keys: [...]` sehen.

## Schritt 10: Keycloak Realm exportieren (Backup)

Admin Console → Realm settings → Action dropdown → "Export"

Speichere die JSON-Datei unter `config/realm-export.json`.

Dies ermöglicht Wiederherstellung ohne manuelles Setup.

## Troubleshooting

### Keycloak startet nicht

```bash
docker compose logs keycloak | tail -50
```

Häufige Fehler:
- PostgreSQL nicht erreichbar: `db` im compose erreichbar?
- Port 8080 belegt: Änder Port in compose

### Traefik findet Keycloak nicht

```bash
docker compose logs keycloak | grep "traefik"
docker network inspect traefik  # Ist keycloak-Container im Netzwerk?
```

### JWKS-Endpoint 404

```bash
curl -v https://auth.5tritti.de/realms/nak-planner/.well-known/openid-configuration
```

Realm existiert? Client existiert?

## Wartung

### Keycloak aktualisieren

```bash
docker compose pull
docker compose up -d
```

### Backup-Strategie

PostgreSQL-Volume ist persistent:
```bash
docker compose exec db pg_dump -U keycloak keycloak > backup.sql
```

### Logs anschauen

```bash
docker compose logs -f keycloak
docker compose logs -f db
```

## Nächste Schritte

Jetzt mit NAK-Planner-Backend konfigurieren:

```bash
# In nak-district-planner/.env:
KEYCLOAK_URL=https://auth.5tritti.de
KEYCLOAK_REALM=nak-planner
KEYCLOAK_CLIENT_ID=nak-planner-api
KEYCLOAK_CLIENT_SECRET=<from-step-6>
```

Dann Backend deployen (Tasks 2–4 in Phase 4a).
