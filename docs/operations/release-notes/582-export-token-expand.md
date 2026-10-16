### Kalender-Export: Datenbankmigration und einmalig sichtbare Kalenderlinks

**Betroffen:**

Bestehende Installationen mit öffentlichen, internen oder persönlichen Kalenderabonnements. Dieses Update ergänzt eine nullable `token_hash`-Spalte, bewahrt aber sämtliche bisherigen Klartext-Tokens. Der Schutz gegen einen Datenbank-Leak ist erst nach einer gesonderten Contract-Migration vollständig; die Folgearbeit wird in [#602](https://github.com/stritti/nak-district-planner/issues/602) nachverfolgt.

**Vor dem Update:**

- Noch benötigte Kalenderlinks aus der bisherigen Anwendung kopieren und sicher verwahren. Nach dem Update liefern Listen nur Metadaten; bestehende Links lassen sich dort nicht erneut anzeigen.
- Ein aktuelles Backup nach dem Produktions-Runbook erstellen.
- Die neue Version bereitstellen und ihre Migration **vor dem Start des neuen Backends/Workers** ausführen, beispielsweise mit `docker compose -f docker-compose.yml run --no-deps --rm --build migrate`. Die Revision `20261015_hash_export_tokens` ergänzt Hashes, ohne bisherige Secrets zu verändern.
- Keine Klartextspalte löschen oder manuell durch Hashes ersetzen. Die aktuelle Anwendung und ihre RLS-Regeln benötigen weiterhin den ursprünglichen Wert.

**Nach dem Update:**

- Ein bestehendes Kalenderabonnement mit seiner bisherigen URL prüfen. Es muss unverändert funktionieren; eine Neuanlage oder Rotation ist für bereits eingerichtete Abonnements nicht erforderlich.
- Einen neuen Kalenderlink erstellen und die vollständige URL sofort kopieren. Sie bleibt bei Datumsänderungen in derselben Ansicht verfügbar, wird jedoch nach Neuladen, Navigation oder Identitäts-/Bezirkswechsel nicht erneut angezeigt.
- Falls ein Link bisher nicht kopiert wurde, einen neuen Link erstellen, den Kalenderclient umstellen und den nicht mehr benötigten Token widerrufen. Einen noch genutzten Token erst nach erfolgreicher Umstellung löschen.
- Bei einem Anwendungs-Rollback darf die erweiterte Tabelle bestehen bleiben: ältere Leser und Schreiber verwenden weiterhin `token`; fehlende Hashes neuer Altversions-Zeilen werden erst im Contract-Follow-up nachgetragen. Falls zusätzlich das Schema zurückgesetzt werden muss, zuerst alle hash-schreibenden Prozesse beenden und einen Migrator verwenden, der die neue Revision kennt. Der Downgrade entfernt nur Hash-Spalte und Index.
- Vor dem späteren Entfernen des Klartexts müssen Rollback-Fenster, Hash-Backfill und sämtliche hashfähigen RLS-/Anwendungsleser gesondert freigegeben sein.
