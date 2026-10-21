### Amtsträger: mehrere Gemeinden und Beauftragungen je Person (Datenbankmigration)

**Betroffen:**

Alle Installationen, die auf das Release mit dem Datenmodell „Person–Gemeinde–Rolle“ aktualisieren. Eine Person hat jetzt eine oder mehrere Zuordnungen (Gemeinde oder Bezirksebene, optional mit Beauftragung, genau eine davon ist die Heimat); die Spalten `leaders.congregation_id` und `leaders.special_role` entfallen. Die Alembic-Revision `20261022_leader_assignments` legt die Tabelle `leader_assignments` an, übernimmt je Amtsträger die bisherige Gemeinde und Beauftragung als Heimat-Zuordnung, ersetzt die Zeilensicherheits-Policies der Tabelle `leaders` und legt drei `SECURITY DEFINER`-Funktionen an (`leader_assignment_member`, `leader_assigned_to`, `leader_subject_scope`). Das Backend beendet sich beim Start, wenn das Schema älter ist. **API-Änderung für eigene Clients:** Leader-Antworten und -Anfragen tragen `assignments` statt `congregation_id` und `special_role`; der Hinweis bei gleichnamigen Personen liefert `congregation_ids`. Die Beauftragung „Gemeindevorsteher“ gehört zu einer Gemeinde, „Bezirksvorsteher“ zur Bezirksebene; andere Kombinationen lehnt die API mit 422 ab, bereits gespeicherte bleiben unverändert.

**Vor dem Update:**

- Ein aktuelles Backup nach dem Produktions-Runbook erstellen.
- Die Migration **vor dem Start des neuen Backends und Workers** ausführen, zum Beispiel mit `docker compose -f docker-compose.yml run --no-deps --rm --build migrate`. Sie läuft in einer Transaktion und kann an bestehenden Daten nicht scheitern.
- Eigene API-Clients und Skripte, die `congregation_id` oder `special_role` an Amtsträgern lesen oder schreiben, vorher auf `assignments` umstellen.
- Das Zurücksetzen auf die vorherige Revision stellt Gemeinde und Beauftragung aus der Heimat-Zuordnung wieder her; **weitere Zuordnungen gehen dabei verloren.**

**Nach dem Update:**

- Prüfen, dass API, Worker und Beat starten (`alembic current` zeigt `20261022_leader_assignments` oder neuer).
- In der Amtsträger-Verwaltung prüfen, dass jede Person in ihrer bisherigen Gemeinde mit der bisherigen Beauftragung erscheint, und bei einer Person mit zwei Gemeinden die zweite Zuordnung im Bearbeiten-Dialog hinzufügen: die Person steht danach in beiden Gemeinden, die Heimat ist markiert.
- Die Matrix für einen Bezirk öffnen und prüfen, dass sie in der gewohnten Zeit lädt.
