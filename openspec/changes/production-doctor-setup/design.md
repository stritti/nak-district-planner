## Context

`nakctl` liegt unter `scripts/ops/` und nutzt `lib.sh` und `nakops.py` (Python-Standardbibliothek). `status` und `check all` prüfen einen laufenden Stack. Die Einrichtung ist in `docs/operations/production-compose.md` beschrieben und besteht weitgehend aus Handgriffen.

## Goals / Non-Goals

**Goals:** eine Diagnose, die auch ohne laufenden Stack hilft und zu jedem Befund sagt, was zu tun ist; eine Erstinstallation ohne Secrets auf der Kommandozeile.

**Non-Goals:** siehe proposal.md.

## Decisions

1. **`doctor` baut auf `check all` auf.** Eigene Prüfungen nur für das, was `status`/`check` voraussetzen (Werkzeuge, Konfiguration, Netz). Ist Docker nicht nutzbar, endet `doctor` nach Werkzeugen und Konfiguration mit Exit-Code 3, weil weitere Prüfungen nur Folgefehler zeigen würden.
2. **Hinweise stehen direkt unter dem Befund** (`→ …`), damit die Ausgabe ohne Doku verständlich ist.
3. **Ports nur bei eigenem Traefik.** Steht `traefik` nicht in `docker compose config --services` (Override `existing-traefik.yml`), gehören 80/443 einem fremden Proxy, und das ist gewollt.
4. **Secrets entstehen in Python** (`nakops init-env`, `secrets.token_urlsafe(32)`, `SECRET_KEY` als `token_hex(32)`). Sie stehen damit nie in Prozessargumenten oder der Ausgabe. URL-sicher, weil `APP_DB_PASSWORD` und `VALKEY_PASSWORD` in Verbindungs-URLs stehen.
5. **Nur fehlende Dateien werden angelegt** (`O_EXCL`, Modus 0600). Eine vorhandene Datei bleibt unangetastet. Existiert eine der beiden Keycloak-Dateien schon, übernimmt die neue deren Datenbankpasswort.
6. **Werte setzen:** aktive Zeile ersetzen und spätere Duplikate entfernen, sonst die auskommentierte Beispielzeile (`# KEY=`) an ihrer Stelle einkommentieren, sonst anhängen.

## Risks / Trade-offs

- **DNS über `getent`** prüft die Auflösung auf dem Server, nicht von außen. Das genügt für Tippfehler und fehlende Einträge.
- **`ss` fehlt** auf manchen Minimal-Systemen; die Portprüfung entfällt dann still.
