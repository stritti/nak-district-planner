## ADDED Requirements

### Requirement: Installation aus einem geprüften Release-Paket
Jedes Release SHALL ein reproduzierbares Deploy-Paket, `install.sh` und `SHA256SUMS` anhängen. `install.sh --version <version>` SHALL das Paket des festen Releases laden, die Prüfsumme prüfen und erst danach installieren. Das Paket SHALL keine `.env`-Dateien mit Werten, Logs, Backups oder Quellcode enthalten.

#### Scenario: Neuinstallation
- **GIVEN** das Zielverzeichnis existiert nicht
- **WHEN** der Betreiber `install.sh --version 1.8.0` ausführt
- **THEN** Compose-Datei, `.env`-Vorlagen, `deploy/` und `nakctl` liegen im Zielverzeichnis
- **AND** `nakctl` ist als Befehl aufrufbar

#### Scenario: Falsche Prüfsumme
- **GIVEN** das Paket passt nicht zu `SHA256SUMS` oder zu `--sha256`
- **WHEN** der Betreiber `install.sh` ausführt
- **THEN** nichts wird geschrieben und der Exit-Code ist 3

#### Scenario: Unsicherer Archiv-Eintrag
- **GIVEN** das Paket enthält einen Link oder einen Pfad außerhalb des Release-Verzeichnisses
- **WHEN** der Betreiber `install.sh` ausführt
- **THEN** nichts wird geschrieben und der Exit-Code ist 3

#### Scenario: Reproduzierbares Paket
- **WHEN** der Release-Workflow für dasselbe Tag erneut läuft
- **THEN** Paket und `SHA256SUMS` sind byte-gleich

### Requirement: Update einer Paket-Installation
Auf einer vorhandenen Paket-Installation SHALL `install.sh --version <version>` nur die Dateien aus dem `MANIFEST` des Pakets ersetzen und eine Bestätigung oder `--yes` verlangen. `.env`-Dateien, `logs/` und `backups/` SHALL unverändert bleiben. Git-Checkouts und fremde, nicht leere Verzeichnisse SHALL abgelehnt werden.

#### Scenario: Update behält Betreiberdaten
- **GIVEN** eine Installation von 1.8.0 mit `.env` und Backups
- **WHEN** der Betreiber `install.sh --version 1.9.0 --yes` ausführt
- **THEN** Compose-Datei und Skripte entsprechen 1.9.0
- **AND** `.env` und `backups/` sind unverändert

#### Scenario: Update ohne Bestätigung
- **WHEN** der Betreiber das Update ohne `--yes` und ohne Terminal startet
- **THEN** nichts wird geändert und der Exit-Code ist 4

#### Scenario: Git-Checkout
- **GIVEN** das Zielverzeichnis ist ein git-Checkout
- **WHEN** der Betreiber `install.sh` ausführt
- **THEN** das Skript verweist auf `git checkout` und ändert nichts
