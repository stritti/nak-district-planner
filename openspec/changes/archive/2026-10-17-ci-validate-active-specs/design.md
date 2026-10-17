# Design

Das existierende required check `Build documentation` wird beibehalten. Der gepinnte OpenSpec-CLI-Aufruf in `.github/workflows/docs.yml` prüft mit `--all --strict --no-interactive` Baseline und alle aktiven Changes. Es wird weder ein neuer obligatorischer Check noch ein `continue-on-error` eingeführt.

Der `configVersion`-Abgleich im Frontend-Bun-Lockfile ändert lediglich das Lockfile-Formatflag. Bestehende Paketversionen und Integritätshashes bleiben unverändert. Die Doku beschreibt, dass ein späteres VitePress-Major-Upgrade einen gesonderten Compatibility- und Security-Review benötigt.

## Verification

- Der vorhandene PR-Check `Build documentation` besteht nur bei gültigen aktiven Changes.
- `bun install --frozen-lockfile` für Frontend und Root, Frontend-Tests und Dokumentations-Build bleiben grün.
- Die drei aktiven OpenSpec-PRs #525, #530 und #558 bleiben unabhängig von diesem Release-Wartungschange.
