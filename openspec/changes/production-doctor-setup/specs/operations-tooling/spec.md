## ADDED Requirements

### Requirement: Installation diagnostizieren
`nakctl doctor` SHALL ohne Änderungen Werkzeuge (Docker-Daemon, Compose, Python, openssl, gpg mit dem Backup-Schlüssel), Konfiguration (`.env`, `COMPOSE_FILE`, `APP_ENV`, `APP_VERSION`) und Netz (DNS von `APP_HOST`/`AUTH_HOST`, Ports bei eigenem Traefik) prüfen und danach `check all` ausführen. Jeder eigene Befund SHALL einen Hinweis zur Behebung enthalten. Ist Docker nicht nutzbar, SHALL der Exit-Code 3 sein.

#### Scenario: Docker-Daemon nicht erreichbar
- **GIVEN** der Docker-Daemon läuft nicht
- **WHEN** der Betreiber `nakctl doctor` ausführt
- **THEN** der Befund nennt den Daemon mit Hinweis zur Behebung, Netz- und Betriebsprüfungen entfallen und der Exit-Code ist 3

#### Scenario: Unvollständige Konfiguration
- **GIVEN** `.env` enthält weder `COMPOSE_FILE` noch `APP_ENV=production`
- **WHEN** der Betreiber `nakctl doctor --skip-checks` ausführt
- **THEN** beide Befunde erscheinen mit dem einzutragenden Wert und der Exit-Code ist 1

#### Scenario: Port belegt
- **GIVEN** der Stack bringt Traefik mit, Traefik läuft nicht und Port 80 ist belegt
- **WHEN** der Betreiber `nakctl doctor` ausführt
- **THEN** ein Befund nennt Port 80 mit Hinweis auf den Override für vorhandenen Traefik

### Requirement: Erstinstallation vorbereiten
`nakctl setup init` SHALL fehlende `.env`, `.env.db`, `.env.keycloak` und `.env.keycloak-db` aus ihren Vorlagen mit Rechten 0600 anlegen, darin zufällige Secrets erzeugen, `KC_DB_PASSWORD` gleich dem Keycloak-`POSTGRES_PASSWORD` setzen und `APP_ENV=production` sowie `COMPOSE_FILE` setzen. Vorhandene Dateien SHALL unverändert bleiben. Secrets SHALL weder ausgegeben noch als Prozessargument übergeben werden.

#### Scenario: Leeres Deploy-Verzeichnis
- **GIVEN** nur die `*.example`-Vorlagen liegen im Deploy-Verzeichnis
- **WHEN** der Betreiber `nakctl setup init --app-host planer.example.org --version 1.7.0` ausführt
- **THEN** vier Dateien mit Rechten 0600 entstehen, jedes Secret ist neu und nur das Keycloak-Datenbankpasswort steht in beiden Keycloak-Dateien, die Ausgabe nennt nur Schlüsselnamen und listet die nächsten Schritte

#### Scenario: Vorhandene Datei
- **GIVEN** `.env` existiert bereits
- **WHEN** der Betreiber `nakctl setup init` erneut ausführt
- **THEN** `.env` bleibt Byte für Byte unverändert

#### Scenario: Ungültige Eingabe
- **WHEN** der Betreiber `--app-host https://x/` oder `--version latest` angibt
- **THEN** das Werkzeug legt nichts an und endet mit Exit-Code 2
