# Lizenzierung und Copyright

Der eigene Quellcode des NAK District Planner wird unter der **GNU Affero General Public License Version 3.0 only (AGPL-3.0-only)** bereitgestellt. Der vollständige, unveränderte Lizenztext steht unter [`LICENSE`](https://github.com/stritti/nak-district-planner/blob/main/LICENSE).

Für selbst gepflegte Quellcodedateien gelten die maschinenlesbaren Angaben `SPDX-FileCopyrightText: 2026 Stephan Strittmatter` und `SPDX-License-Identifier: AGPL-3.0-only`. Vorhandene Rechte anderer Mitwirkender oder Dritter bleiben unberührt. Die Copyright-Angabe bezeichnet nur solche Inhalte, an denen der Genannte die entsprechenden Rechte hält; Beiträge Dritter müssen mit ihrem eigenen Copyright versehen bleiben. Bei unklarer Herkunft ist die Lizenzzuordnung vor einer Kennzeichnung zu klären.

Unter `third_party/` und in importierten Agent-Skills können andere Lizenzen gelten. Insbesondere die Ponytail-Komponenten stehen unter der mitgelieferten MIT-Lizenz. Diese Dateien werden nicht pauschal auf AGPL umgestellt.

Neue oder geänderte Quelldateien müssen die SPDX-Header tragen. Zum Prüfen: `python3 scripts/license_headers.py --check`. Zum Ergänzen fehlender Header in eigenem Code: `python3 scripts/license_headers.py --fix`. Der Fixer verweigert eine automatische Änderung bei vorhandenen abweichenden Lizenz- oder Copyright-Hinweisen und verlangt eine Prüfung der Rechteinhaberschaft. Die CI testet den Prüfer und validiert die Header für alle erfassten getrackten Quellcodedateien.

Die CI prüft zusätzlich die ursprünglichen Ausführungsrechte (`100755`) der Shell- und Setup-Skripte. Der Prüfer akzeptiert nur sprachgültige Kommentarheader und verweigert das Überschreiben vorhandener Angaben zu anderen Lizenzen. Python-Encoding-Cookies und CSS-`@charset`-Direktiven bleiben an ihrer vorgeschriebenen Position.

Generierte VitePress-Dateien unter `docs/.vitepress/dist/` sowie der Cache werden nicht als eigene Quelldateien klassifiziert; die gepflegten VitePress-Konfigurationsdateien bleiben prüfpflichtig.

## REUSE-Konformität

REUSE 3.3 definiert die maschinenlesbare Zuordnung **für sämtliche getrackten Projektdateien**. Die Zuordnung steht in `REUSE.toml` (Schema-Version 1), die vollständigen verwendeten Lizenztexte liegen in `LICENSES/AGPL-3.0-only.txt` und `LICENSES/MIT.txt`. Die zentrale `LICENSE` bleibt unverändert.

Die bestehenden SPDX-Header bleiben für selbst gepflegten Quellcode maßgeblich. Für Dokumentation, Konfiguration, Sperrdateien und nicht kommentierbare Assets dient der AGPL-Eintrag in `REUSE.toml` als Fallback (`precedence = "closest"`). Die im Repository mitgelieferten OpenSpec- und Ponytail-Agentdateien werden explizit mit ihren jeweiligen MIT-Rechten und Herkunftsangaben gekennzeichnet (`precedence = "override"`). Weitere als MIT ausgewiesene Skills haben eigene Zuordnungen. Eine REUSE-Zuordnung ersetzt **keine** Prüfung der tatsächlichen Urheber- und Nutzungsrechte.

Lokal prüfen:

```bash
python3 -m pip install reuse==6.2.0
reuse lint
python3 -m unittest discover -s scripts -p 'test_reuse_metadata.py' -v
python3 scripts/license_headers.py --check
```

Die CI prüft REUSE und die projektinternen SPDX-Regeln unabhängig voneinander. Neue Drittanbieterdateien benötigen eine belegbare Herkunft, korrekte SPDX-Zuordnung und gegebenenfalls eine neue Lizenzdatei unter `LICENSES/`.
