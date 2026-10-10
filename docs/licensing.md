# Lizenzierung und Copyright

Der eigene Quellcode des NAK District Planner wird unter der **GNU Affero General Public License Version 3.0 only (AGPL-3.0-only)** bereitgestellt. Der vollständige, unveränderte Lizenztext steht unter [`LICENSE`](https://github.com/stritti/nak-district-planner/blob/main/LICENSE).

Für selbst gepflegte Quellcodedateien gelten die maschinenlesbaren Angaben `SPDX-FileCopyrightText: 2026 Stephan Strittmatter` und `SPDX-License-Identifier: AGPL-3.0-only`. Vorhandene Rechte anderer Mitwirkender oder Dritter bleiben unberührt. Die Copyright-Angabe bezeichnet nur solche Inhalte, an denen der Genannte die entsprechenden Rechte hält; Beiträge Dritter müssen mit ihrem eigenen Copyright versehen bleiben. Bei unklarer Herkunft ist die Lizenzzuordnung vor einer Kennzeichnung zu klären.

Unter `third_party/` und in importierten Agent-Skills können andere Lizenzen gelten. Insbesondere die Ponytail-Komponenten stehen unter der mitgelieferten MIT-Lizenz. Diese Dateien werden nicht pauschal auf AGPL umgestellt.

Neue oder geänderte Quelldateien müssen die SPDX-Header tragen. Zum Prüfen: `python3 scripts/license_headers.py --check`. Zum Ergänzen fehlender Header in eigenem Code: `python3 scripts/license_headers.py --fix`. Der Fixer verweigert eine automatische Änderung bei vorhandenen abweichenden Lizenz- oder Copyright-Hinweisen und verlangt eine Prüfung der Rechteinhaberschaft. Die CI testet den Prüfer und validiert die Header für alle erfassten getrackten Quellcodedateien.
