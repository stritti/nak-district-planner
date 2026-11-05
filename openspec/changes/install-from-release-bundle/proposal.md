## Why

Heute kommt `nakctl` mit Compose-Dateien, `.env`-Vorlagen und Traefik-Konfiguration nur über `git clone` eines Release-Tags auf den Produktionsserver. Damit liegt der gesamte Quellcode auf dem Server, `git` ist Pflicht, und ein Update der Compose-Dateien heißt `git checkout`. Betreiber fragen nach einer Installation per `curl`. Ein blindes `curl … | sh` von einem beweglichen Branch wäre dafür aber der falsche Weg: ungeprüfter Code von einem Ziel, das sich jederzeit ändern kann, läuft dann direkt als root.

## What Changes

- Jedes Release hängt drei Dateien an: `nak-district-planner-deploy-<version>.tar.gz` (nur das, was der Server braucht: `docker-compose.prod.yml`, `.env`-Vorlagen, `.env.docker*`, `deploy/`, `scripts/backup.sh`, `scripts/restore.sh`, `scripts/ops/` ohne Tests, Lizenzen, `VERSION`, `MANIFEST`), `install.sh` und `SHA256SUMS`.
- Das Paket entsteht reproduzierbar (`scripts/ops/build-bundle.sh`), damit ein erneuter Lauf des Release-Workflows identische Bytes hochlädt.
- `scripts/ops/install.sh --version <version>` lädt Paket und `SHA256SUMS` des festen Releases, prüft die Prüfsumme (optional zusätzlich gegen `--sha256`), lehnt Links, absolute Pfade und `..` im Archiv ab und installiert erst danach nach `/opt/nak-district-planner` (`--dir`). Es legt einen kleinen `nakctl`-Befehl in `/usr/local/bin` an (`--bin-dir`, `--no-link`).
- Auf einer vorhandenen Installation ersetzt derselbe Aufruf nur die Paketdateien. `.env`, `.env.db`, `.env.keycloak`, `.env.keycloak-db`, `logs/` und `backups/` bleiben unberührt. Das Update verlangt eine Bestätigung oder `--yes`. Git-Checkouts und fremde, nicht leere Verzeichnisse werden abgelehnt.
- `nakctl deploy update` erkennt eine Paket-Installation an `VERSION` und warnt, wenn das Paket nicht zur Zielversion passt.
- Die Dokumentation zeigt den Weg ohne Pipe: `install.sh` und `SHA256SUMS` herunterladen, mit `sha256sum -c` prüfen, lesen, dann ausführen.

## Capabilities

### New Capabilities
- keine

### Modified Capabilities
- `operations-tooling`: Installation und Update aus einem geprüften Release-Paket.

## Impact

- Neue Dateien: `scripts/ops/install.sh`, `scripts/ops/build-bundle.sh`, Tests `scripts/ops/test_install.py`.
- `scripts/ops/nakctl`: Versionsprüfung in `deploy update` und Hilfetext.
- CI: `release.yml` baut das Paket und lädt es vor der Veröffentlichung an den Release-Entwurf (`gh release upload --clobber`); `ops-scripts.yml` prüft die neuen Skripte mit ShellCheck und läuft auch bei Änderungen an Compose-Dateien, `.env`-Vorlagen und `deploy/`.
- Dokumentation: `docs/operations/production-compose.md` (Einrichtung ohne git) und `docs/operations/admin-scripts.md` (Installation und Update per Paket). Der Demo-Bezirk ist nicht betroffen.
- Keine Änderung an Backend, Frontend, Datenbankschema oder Compose-Dateien.

## Non-Goals

- Kein `curl … | sh`-Einzeiler in der Dokumentation.
- Keine Signatur des Pakets (z. B. GitHub Artifact Attestations oder GPG); die Vertrauensbasis bleibt HTTPS zu GitHub plus das feste Release. Eine Signatur kann später ergänzt werden.
- Keine Paketverwaltung (deb/rpm) und kein Entfernen veralteter Paketdateien bei einem Update.
