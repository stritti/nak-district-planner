### #472: Härtung der produktiven Docker-Installation

**Betroffen:** Bestehende Installationen mit `docker-compose.prod.yml` oder `docker-compose.yml`. Die Hinweise zu Keycloak/Authentik gelten zusätzlich nur, wenn deren eigenständige Compose-Stacks unter `idp-deploy/` betrieben werden.

**Vor dem Update:**

1. **Pflicht: `VALKEY_PASSWORD` setzen.** In der produktiven `.env` einen neuen, URL-sicheren Zufallswert hinterlegen, beispielsweise mit `openssl rand -hex 32`. Der Beispielwert `changeme` ist nicht zulässig. **Der Start wird ohne diesen Wert verweigert.** Dieselbe aktualisierte Compose-Konfiguration muss Valkey und die Anwendung versorgen. Die neue `.env.docker` verwendet das Passwort für die `VALKEY_URL`. Auch `APP_DB_PASSWORD` darf kein Platzhalter sein.
2. **Aktive Celery-Aufträge berücksichtigen.** Vor der Umstellung laufende Aufträge beenden und bestehende Queue-Inhalte überprüfen. Änderungen der Valkey-Zugangsdaten bei laufenden Clients müssen koordiniert werden, damit keine Aufträge verloren gehen. Anschließend eine verschlüsselte Datenbanksicherung erstellen.
3. **Individuelle Proxy-Konfiguration prüfen.** Das Frontend-Nginx lauscht im Container jetzt auf **Port 8080 statt 80**. Die mitgelieferten Traefik-Routen und die Host-Port-Zuordnung sind angepasst. Nur individuelle Routen, die unmittelbar den Container-Port 80 ansprechen, müssen umgestellt werden. Die öffentliche HTTPS-Adresse bleibt unverändert.
4. **Nur bei separatem Identity Provider:** Für `idp-deploy/keycloak/` sind `KEYCLOAK_HOSTNAME`, `KEYCLOAK_DB_PASSWORD` und `KC_BOOTSTRAP_ADMIN_PASSWORD` korrekt zu setzen; für `idp-deploy/authentik/` insbesondere `AUTHENTIK_HOSTNAME`, `AUTHENTIK_POSTGRES_PASSWORD` und `AUTHENTIK_SECRET_KEY`. Die öffentlichen Hostnamen müssen per HTTPS erreichbar sein. Der Authentik-Port 9000 ist nur noch an die lokale Host-Adresse gebunden. Die jeweiligen `.env.example`-Dateien dienen als Vorlage, nicht als produktive Konfiguration.

**Nach dem Update:**

1. Die Compose-Konfiguration mit `docker compose config --quiet` beziehungsweise `docker compose -f docker-compose.prod.yml config --quiet` prüfen. Anschließend gemäß [Produktions-Runbook](https://github.com/stritti/nak-district-planner/blob/main/docs/operations/production-runbook.md) deployen und Healthchecks, Login und Hintergrundverarbeitung testen.
2. **Sicherungen zusammen aufbewahren:** `scripts/backup.sh` erzeugt künftig eine verschlüsselte Datenbankdatei (`*.dump.gpg`) **und** eine verschlüsselte Rollenliste (`*.roles.sql.gpg`). Bei Wiederherstellung in einen neuen Cluster werden Rollen vor dem Datenbankdump eingespielt; Passwörter werden danach separat neu gesetzt. Details enthält das [Runbook zum Restore](https://github.com/stritti/nak-district-planner/blob/main/docs/operations/production-runbook.md#5-backup-inklusive-rollen-und-wiederherstellung).
3. Bei Problemen nicht einfach auf ein älteres Image zurückwechseln: Die Kompatibilität des Datenbankschemas prüfen und gegebenenfalls anhand des vorherigen Backups wiederherstellen.
