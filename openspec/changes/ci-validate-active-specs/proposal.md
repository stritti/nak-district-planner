# Change: CI validiert aktive OpenSpec-Spezifikationen

## Why
Der Dokumentationsworkflow prüft aktuell nur die Baseline. Ungültige aktive Changes können deshalb trotz erfolgreichem Quality Gate nach `main` gelangen (Issue #473).

## What Changes
- Der bestehende CI-Job validiert Baseline und aktive Changes streng mit `validate --all --strict --no-interactive`.
- Ein eingefrorenes Bun-Lockfile bleibt Voraussetzung für den Frontend-Build; die beiden Lockfiles verwenden dasselbe Format.
- Das Release-Handbuch dokumentiert die erfolgte v1.0.0-Promotion und die eigenständige, prüfbare VitePress-Upgrade-Strategie.

## Impact
Keine Änderung an Runtime-APIs, Rollen oder fachlichen Daten. Ein bislang ungültiger aktiver OpenSpec-Change blockiert nun den Dokumentations-Check, bis er korrigiert ist.
