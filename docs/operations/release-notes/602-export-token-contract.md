### Export-Tokens: endgültige Hash-only-Migration (einmalig, nicht umkehrbar)

**Betroffen:**

Alle Installationen mit Kalenderabonnements (PUBLIC, INTERNAL, personenbezogen). Die Revision `20261016_contract_export_tokens` entfernt die Klartextspalte `export_tokens.token` nach dem Backfill aller Hashes. Ältere Backend-Versionen fragen `export_tokens.token` ab und sind danach nicht mehr lauffähig. Die Migration baut auf `20261015_hash_export_tokens` und `20261016_notif_user_state` auf.

**Vor dem Update:**

- Ein Wartungsfenster einplanen und ein verschlüsseltes Backup erstellen und prüfen (Restore getestet).
- API, Worker und Beat stoppen, die Migration mit dem **neuen** Artefakt ausführen und erst danach starten. SQL-RLS, `SECURITY DEFINER`-Funktionen, Repository und ORM müssen gemeinsam ausgerollt werden.
- Ein abweichender Hash einer bestehenden Zeile bricht die Transaktion ab. Die Ursache klären, keinen Token stillschweigend ersetzen.

**Nach dem Update:**

- Je ein bestehendes PUBLIC-, INTERNAL- und personenbezogenes ICS-Abonnement, einen widerrufenen und einen unbekannten Token prüfen. Bestehende URLs bleiben unverändert gültig.
- Ein Rollback ist nicht möglich: Der Alembic-Downgrade schlägt absichtlich fehl, weil sich der Klartext aus SHA-256 nicht rekonstruieren lässt. Nötig sind das verschlüsselte Backup und die passende alte Anwendungsversion, mit Verlust der Schreibvorgänge seit dem Backup. Lässt sich kein Backup einspielen, vor dem Start einer älteren Version die betroffenen Abonnements rotieren und neu verteilen.
- Das Entfernen der Spalte bereinigt weder WAL, alte Backups, Datenbankseiten noch zentrale Access-Logs. Konfigurierte Aufbewahrungsfristen und bereinigtes Logging anwenden, bei Bedarf die Tabelle im Wartungsfenster physisch neu schreiben. Rohe Tokens gehören nicht in Audit-Logs.
