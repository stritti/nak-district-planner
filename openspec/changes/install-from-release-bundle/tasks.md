## 1. Paket

- [x] 1.1 `scripts/ops/build-bundle.sh` baut ein reproduzierbares Paket mit `VERSION`, `MANIFEST`, `install.sh` und `SHA256SUMS`
- [x] 1.2 `release.yml` lädt Paket, `install.sh` und `SHA256SUMS` vor der Veröffentlichung an den Release-Entwurf

## 2. Installation

- [x] 2.1 `scripts/ops/install.sh` mit `--version`, `--dir`, `--sha256`, `--bin-dir`, `--no-link`, `--dry-run`, `--yes` und `--help`
- [x] 2.2 Prüfsumme, Archiv-Einträge und `MANIFEST` werden vor jedem Schreibzugriff geprüft
- [x] 2.3 Update ersetzt nur Paketdateien, verlangt Bestätigung und lehnt git-Checkouts und fremde Verzeichnisse ab
- [x] 2.4 `nakctl deploy update` erkennt Paket-Installationen an `VERSION`
- [x] 2.5 Unter `sudo` gehört die Installation dem aufrufenden Benutzer (`--owner`), `MANIFEST` erlaubt nur kanonische Pfade

## 3. Tests und CI

- [x] 3.1 `scripts/ops/test_install.py`: Reproduzierbarkeit, Neuinstallation, Update, falsche Prüfsumme, `--sha256`, Pfad-Ausbruch, Links, git-Checkout, `--dry-run`, fremder `nakctl`, ungültige Eingaben
- [x] 3.2 `ops-scripts.yml`: ShellCheck für die neuen Skripte, Trigger für Compose-Dateien, `.env`-Vorlagen und `deploy/`

## 4. Dokumentation

- [x] 4.1 `docs/operations/production-compose.md`: Einrichtung ohne git
- [x] 4.2 `docs/operations/admin-scripts.md`: Installation und Update aus dem Release-Paket
