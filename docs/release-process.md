# Release-Prozess

Der NAK District Planner verwendet eine vollautomatisierte **Semantic Versioning (SemVer)** Release-Pipeline, die auf [Conventional Commits](https://www.conventionalcommits.org/de/) und [release-please](https://github.com/googleapis/release-please) basiert.

---

## Versionierungsschema (SemVer)

Versionen folgen dem Format **`MAJOR.MINOR.PATCH`** (z. B. `1.2.3`):

| Segment | Bedeutung | Auslöser |
|---------|-----------|---------|
| `MAJOR` | Inkompatible API-Änderungen | Commit mit `BREAKING CHANGE:` im Footer |
| `MINOR` | Neue, abwärtskompatible Features | Commit mit Präfix `feat:` |
| `PATCH` | Fehlerbehebungen | Commit mit Präfix `fix:` oder `perf:` |

> **Hinweis:** Solange das Projekt die Version `0.x.y` hat, löst ein `feat:`-Commit einen Minor-Bump (z. B. `0.1.0 → 0.2.0`) und ein `BREAKING CHANGE` ebenfalls nur einen Minor-Bump aus, um die Vorab-Phase zu respektieren.

---

## Conventional Commits

Alle Commits auf dem `main`-Branch **müssen** dem [Conventional Commits Standard](https://www.conventionalcommits.org/de/) folgen, damit die automatische Versionierung korrekt funktioniert.

### Format

```
<type>(<scope>): <kurze Beschreibung>

[optionaler Body]

[optionaler Footer: BREAKING CHANGE: ...]
```

### Zulässige Typen

| Typ | Wirkung auf Version | Sichtbar im CHANGELOG |
|-----|--------------------|-----------------------|
| `feat` | Minor-Bump | ✅ ja (Features) |
| `fix` | Patch-Bump | ✅ ja (Bug Fixes) |
| `perf` | Patch-Bump | ✅ ja (Performance) |
| `revert` | Patch-Bump | ✅ ja (Reverts) |
| `docs` | Patch-Bump | ✅ ja (Documentation) |
| `refactor` | Patch-Bump | ✅ ja (Code Refactoring) |
| `chore` | kein Bump | ❌ ausgeblendet |
| `style` | kein Bump | ❌ ausgeblendet |
| `test` | kein Bump | ❌ ausgeblendet |
| `build` | kein Bump | ❌ ausgeblendet |
| `ci` | kein Bump | ❌ ausgeblendet |

### Beispiele

```bash
# Neues Feature → Minor-Bump (0.1.0 → 0.2.0)
git commit -m "feat(matrix): Gottesdienst-Zuweisung per Drag & Drop"

# Fehlerbehebung → Patch-Bump (0.1.0 → 0.1.1)
git commit -m "fix(api): Datumsformat bei ICS-Export korrigiert"

# Breaking Change → Major-Bump (1.0.0 → 2.0.0)
git commit -m "feat(auth)!: JWT-basiertes Auth erfordert Header-Änderung

BREAKING CHANGE: X-API-Key Header wurde durch Authorization: Bearer ersetzt"

# Nur Doku, kein Version-Bump wird erzeugt (nur Patch)
git commit -m "docs: Release-Prozess dokumentiert"
```

---

## Wie die Pipeline funktioniert

Die Release-Pipeline besteht aus zwei GitHub Actions Workflows:

### 1. `release.yml` – Kern der Release-Automatisierung

```
Push auf main
     │
     ▼
googleapis/release-please-action
     │
     ├─── Kein neuer Commit mit relevantem Typ
     │         → Nichts passiert
     │
     └─── Neuer relevantem Commit erkannt
               │
               ├─── Release-PR existiert noch nicht
               │         → Release-PR wird erstellt / aktualisiert
               │           (CHANGELOG.md + Versions-Bump in Dateien)
               │
               └─── Release-PR wird gemergt
                         → GitHub Release + Git-Tag (z. B. v1.2.3)
                         → Docker-Images mit Versions-Tag veröffentlicht
```

### 2. `build.yml` – Kontinuierlicher Docker-Build

Dieser Workflow wird bei jedem Push auf `main` oder `develop` sowie bei Pull Requests ausgeführt und veröffentlicht Docker-Images mit Branch- und SHA-Tags (z. B. `main`, `sha-abc1234`).

---

## Release-PR Workflow

1. Entwickler pushen Feature-Branches und erstellen Pull Requests auf `main`.
2. Nach dem Merge in `main` analysiert **release-please** alle neuen Commits seit dem letzten Release.
3. release-please erstellt oder aktualisiert automatisch einen **Release-PR** mit dem Titel z. B. `chore(main): release 1.2.0`.
4. Dieser PR enthält:
   - Aktualisiertes `CHANGELOG.md`
   - Versions-Bump in `package.json` (root + frontend)
   - Versions-Bump in `services/backend/pyproject.toml`
5. Ein Maintainer **prüft den Release-PR** und **mergt** ihn.
6. release-please erstellt automatisch:
   - Einen Git-Tag (z. B. `v1.2.0`)
   - Einen GitHub Release mit dem CHANGELOG als Beschreibung
7. Der `release-docker`-Job baut und veröffentlicht Docker-Images mit Versions-Tags.

---

## Automatisch aktualisierte Dateien

release-please aktualisiert bei einem Release die Versions-Angaben in folgenden Dateien:

| Datei | Format |
|-------|--------|
| `package.json` | `"version": "1.2.0"` |
| `services/frontend/package.json` | `"version": "1.2.0"` |
| `services/backend/pyproject.toml` | `version = "1.2.0"` (unter `[project]`) |
| `CHANGELOG.md` | Neuer Abschnitt mit allen Änderungen |

---

## Docker-Image-Tags bei einem Release

Nach einem erfolgreichen Release werden Docker-Images für Backend und Frontend mit folgenden Tags veröffentlicht:

| Tag | Beispiel | Bedeutung |
|-----|---------|-----------|
| `{{version}}` | `1.2.0` | Exakte Version |
| `{{major}}.{{minor}}` | `1.2` | Minor-Stream |
| `{{major}}` | `1` | Major-Stream |
| `latest` | `latest` | Neueste stabile Version |

Die Images werden in der **GitHub Container Registry (GHCR)** veröffentlicht:

```
ghcr.io/stritti/nak-district-planner/backend:1.2.0
ghcr.io/stritti/nak-district-planner/frontend:1.2.0
```

---

## Manuelles Auslösen

Die Release-Pipeline läuft vollautomatisch bei jedem Push auf `main`. Es ist **kein manuelles Eingreifen** erforderlich, außer dem Mergen des Release-PRs.

Ein direktes Auslösen über die GitHub-UI ist derzeit nicht konfiguriert; Releases werden ausschließlich durch Pushes auf `main` gestartet.

---

## Konfiguration

Die Release-Pipeline wird durch folgende Dateien konfiguriert:

| Datei | Zweck |
|-------|-------|
| `release-please-config.json` | Pakete, Changelog-Abschnitte, Extra-Dateien |
| `.release-please-manifest.json` | Aktuelle Versions-Stände (nicht manuell bearbeiten) |
| `.github/workflows/release.yml` | GitHub Actions Workflow |

---

## Weiterführende Links

- [Conventional Commits Spezifikation (DE)](https://www.conventionalcommits.org/de/)
- [Semantic Versioning 2.0.0](https://semver.org/lang/de/)
- [release-please Dokumentation](https://github.com/googleapis/release-please)
- [release-please-action](https://github.com/googleapis/release-please-action)
