### Dienste, Amtsträger und Doppelbelegung: vier Datenbankmigrationen

**Betroffen:**

Alle Installationen, die von 1.3.x oder älter auf 1.4.0 oder neuer aktualisieren. Die neuen Funktionen für Dienste (Doppelbelegung über Gemeinden, Amtsträger als Dienst-Identität, Konfliktanzeige in der Matrix) brauchen die Alembic-Revisionen `20261019_duty_identity_schedule`, `20261020_duty_leader_identity`, `20261020_duty_account_leaders` und `20261021_duty_identity_interval`. Das Backend prüft beim Start den Alembic-Head und beendet sich bei einem älteren Schema; ein Backend 1.4.0 oder neuer ohne diese Migrationen startet nicht. Zusätzlich lehnt die API Bezirks- und Gemeindenamen ab, die es im selben Bezirk bereits gibt (HTTP 409, ohne Beachtung von Groß-/Kleinschreibung). Bestehende Duplikate bleiben unberührt.

**Vor dem Update:**

- Ein aktuelles Backup nach dem Produktions-Runbook erstellen.
- Die neue Version bereitstellen und die Migrationen **vor dem Start des neuen Backends und Workers** ausführen, zum Beispiel mit `docker compose -f docker-compose.yml run --no-deps --rm --build migrate`.
- Die Migrationen legen eine Spalte (`event_duty_assignments.leader_id`), einen eindeutigen Index und `SECURITY DEFINER`-Funktionen an. Sie ändern keine bestehenden Zeilen. Das Zurücksetzen auf eine ältere Revision löscht Dienste, die einem Amtsträger zugeordnet wurden, weil sie keinen Namen und kein Konto haben.

**Nach dem Update:**

- Prüfen, dass API, Worker und Beat starten (`alembic current` zeigt `20261021_duty_identity_interval` oder neuer).
- Im Dienst-Panel eines Termins einen Dienst einem Amtsträger zuordnen und im Dialog zur Gottesdienstzuweisung prüfen, dass ein überlappender Dienst desselben Amtsträgers abgelehnt wird.
- Das Anlegen eines Bezirks oder einer Gemeinde mit bereits vergebenem Namen muss mit einer verständlichen Meldung abgelehnt werden.
