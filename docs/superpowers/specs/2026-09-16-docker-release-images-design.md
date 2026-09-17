# Docker-Images als Release-Bestandteil (Ansatz A) — Design

Datum: 2026-09-16
Status: approved (Ansatz A), Umsetzung freigegeben

## Ziel

Docker-Images für Backend + Frontend sind verlässlicher Bestandteil jedes
release-please-Releases in GHCR — ohne tar-Upload, ohne zweiten Workflow-Run,
ohne PAT-Pflicht.

## Befund

`release.yml:docker-build` läuft heute als zweiter, tag-getriggerter Run
(`on: tags: v*`). Erstellt release-please den Tag mit `GITHUB_TOKEN`
(Fallback seit `92c112b`), unterdrückt GitHub Folge-Runs — der Build startet
nicht. Images sind damit kein garantierter Release-Bestandteil.

## Design (Ansatz A)

### 1. Job-Graph & Trigger

- `release-please`-Step erhält `id: release` und schreibt Outputs.
- `docker-build` hängt an `needs: [release-please]`, Bedingung:
  `needs.release-please.outputs.releases_created == 'true' ||
   needs.release-please.outputs.release_created == 'true'`
  (Manifest vs. Simple-Output, linked-versions → Single-Release `vX.Y.Z`).
- `on:` bleibt `push: branches: [main]` (kein `tags`-Trigger mehr nötig);
  Tag-Push aus release-please löst keinen separaten Run mehr aus.
- Kein Release → Build skippt still. Build-Fehler → Run rot, Release bleibt
  bestehen (Retry via Re-Run des Workflow-Runs).

### 2. Version & Tag-Mapping

- Version aus `tag_name` (führendes `v` strippen: `v1.2.0` → `1.2.0`),
  Fallback `version`-Output.
- GHCR-Tags pro Service (`backend`, `frontend`):
  `1.2.0`, `1.2`, `1`, `latest` via `docker/metadata-action` mit
  `value=`-Override (kein Tag-Event-Kontext mehr).
- `build.yml` (Branch-/SHA-Tags bei jedem Push/PR) bleibt unverändert.

### 3. Secrets & Permissions

- Token: `secrets.RELEASE_PLEASE_TOKEN || secrets.GITHUB_TOKEN` (bereits so).
- Job-Permissions: `packages: write` (Top-Level bereits gesetzt),
  GHCR-Login mit `GITHUB_TOKEN`.
- PAT nur noch relevant, wenn nachgelagerte Workflows auf Release-Events
  triggern sollen — nicht mehr für Images erforderlich.

### 4. Verifikation & Doku

- YAML-Parse + `yamllint`/`actionlint` falls vorhanden.
- `docs/release-process.md`: Flussbild (ein Run statt Tag-Push-Kette) und
  Tag-Tabelle anpassen; Hinweis, dass Images aus demselben Run stammen.

## Nicht-Ziele (YAGNI)

- Kein `docker save` / `.tar.gz` als Release-Asset oder Actions-Artefakt.
- Keine neue Registry, keine SBOM/Signierung, keine Änderung an `build.yml`.
- Keine Anpassung der release-please-Changelog-Templates.

## Self-Review

- Keine TBD/TODO-Platzhalter.
- Konsistent: ein Run, eine Version, zwei Services, vier Tags.
- Scope: einzelne Änderung an `release.yml` + Doku-Absatz — kein Zerlegen nötig.
- Eindeutig: GHCR-Link-Modus, kein tar-Upload.
