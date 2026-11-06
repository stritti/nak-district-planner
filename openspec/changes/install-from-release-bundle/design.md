## Context

`nakctl` und `scripts/backup.sh`/`restore.sh` finden ihr Deploy-Verzeichnis relativ zum Skript (`scripts/ops/../..`). Die Produktions-Compose-Datei bindet `deploy/traefik/dynamic/*.yml` ein und liest `.env.docker*`. Ein Paket muss deshalb genau die Struktur des Repository-Wurzelverzeichnisses für diese Dateien behalten.

## Decisions

1. **Release-Asset statt GitHub-Quellarchiv.** GitHub garantiert keine stabilen Bytes für automatisch erzeugte Quellarchive, und diese enthielten den gesamten Quellcode. Ein eigenes, reproduzierbares Paket (`tar --sort=name --mtime=@<commit-zeit> --owner=0 --group=0`, `gzip -n`) hat stabile Prüfsummen, auch wenn der Release-Workflow erneut läuft.
2. **Prüfsumme vor jedem Schreibzugriff.** `install.sh` arbeitet in einem temporären Verzeichnis: Download, Prüfsumme gegen `SHA256SUMS` und optional `--sha256`, dann Prüfung der Archiv-Einträge (nur Dateien und Verzeichnisse unter `nak-district-planner-<version>/`, kein `..`), dann Entpacken, dann Prüfung von `MANIFEST` und `VERSION`. Erst danach wird das Ziel verändert. Jede Datei wird über eine temporäre Datei mit `mv` ersetzt.
3. **Vertrauensbasis.** `SHA256SUMS` kommt aus demselben Release wie das Paket. Die Prüfsumme schützt also vor beschädigten oder abgeschnittenen Downloads und vor einem vertauschten Paket. Gegen ein kompromittiertes GitHub-Konto schützt sie nicht. Wer die Prüfsumme über einen zweiten Kanal kennt, gibt sie mit `--sha256` an. Eine Signatur ist ein Non-Goal dieses Changes.
4. **Kein `curl | sh`.** Die Dokumentation lädt `install.sh` und `SHA256SUMS` als Dateien, prüft mit `sha256sum -c --ignore-missing` und führt das Skript erst danach aus. Für Updates liegt `install.sh` bereits im Paket.
5. **Betreiberdaten sind nie Teil des Pakets.** `MANIFEST` darf `.env`, `.env.db`, `.env.keycloak`, `.env.keycloak-db`, `logs/` und `backups/` nicht nennen. `install.sh` lehnt ein solches Paket ab. Ein Update ersetzt nur die Dateien aus `MANIFEST`.
6. **Wrapper statt Symlink.** `nakctl` findet `lib.sh` über seinen eigenen Pfad. Ein Symlink in `/usr/local/bin` würde das brechen, deshalb legt `install.sh` dort ein zweizeiliges Shell-Skript mit `exec` an. Eine vorhandene fremde Datei `nakctl` bleibt unverändert.

## Risks / Trade-offs

- Dateien, die in einer neuen Version wegfallen, bleiben bei einem Update liegen. Das ist harmlos, solange `COMPOSE_FILE` auf die aktuelle Datei zeigt.
- Die Paketliste steht in `build-bundle.sh`. Fehlt eine neue Datei, die die Compose-Datei braucht, fällt das nur im Betrieb auf. `ops-scripts.yml` läuft deshalb auch bei Änderungen an Compose-Dateien, `.env`-Vorlagen und `deploy/`, und der Build bricht ab, wenn eine gelistete Datei fehlt.
