# Rundgang mit dem Demo-Bezirk

Der **Demo-Bezirk Aremorica** zeigt alle Planungsschritte an einem durchgängigen Beispiel. Er enthält je ein Beispiel für jede Planungssituation, die die Matrix kennt: freigegebene und geplante Gottesdienste, Lücken, Doppelbelegung, zu kurze Wechselzeit, Abwesenheit und einen kollidierenden Organistendienst. Dazu kommen Feiertage und ein Kalender-Abo. Dieser Rundgang geht die Schritte der Startseite **Erste Schritte** der Reihe nach durch.

## Demo-Bezirk anlegen

```bash
make seed              # legt den Demo-Bezirk einmalig an
make seed-reset-demo   # löscht ihn und legt ihn für die aktuellen Wochen neu an
```

Die Planungsdaten beginnen am Montag der laufenden Woche und reichen sechs Wochen weit. Vor einer Vorführung legt `make seed-reset-demo` den Bezirk neu an, damit die Beispiele in den kommenden Wochen liegen.

Den Demo-Bezirk sieht jeder Superadmin. Andere Personen brauchen eine Mitgliedschaft im Bezirk, etwa als `PLANNER` oder `DISTRICT_ADMIN` (siehe [Rollenkonzept](/features/roles)).

## 1. Bezirk und 2. Gemeinden mit Gottesdienstzeiten

Der Bezirk liegt in Baden-Württemberg (`BW`) und hat vier Gemeinden:

| Gemeinde | Gottesdienstzeiten |
|---|---|
| Gallisches Dorf | Sonntag 09:30, Mittwoch 20:00 |
| Babaorum | Sonntag 09:30 |
| Aquarium | Sonntag 11:15 |
| Laudanum | Sonntag 10:00, Donnerstag 20:00 |

Die Gottesdienstzeiten stehen unter **Bezirke & Gemeinden**. Aus ihnen entstehen im nächsten Schritt die Entwürfe. Aquarium beginnt absichtlich nur 15 Minuten nach dem Ende des Gottesdienstes im Gallischen Dorf. Ein Gottesdienst dauert 90 Minuten.

## 3. Amtsträger

| Amtsträger | Amt | Gemeinde | Aufgabe |
|---|---|---|---|
| Miraculix | Bezirksältester | Bezirk | Bezirksvorsteher |
| Majestix | Priester | Gallisches Dorf | Gemeindevorsteher |
| Asterix | Evangelist | Gallisches Dorf | Mittwochsgottesdienste |
| Obelix | Priester | Babaorum | Gemeindevorsteher |
| Methusalix | Priester | Aquarium | Gemeindevorsteher |
| Automatix | Priester | Laudanum | Gemeindevorsteher |
| Verleihnix | Diakon | Laudanum | Donnerstagsgottesdienste |

Troubadix ist kein Amtsträger. Er spielt jeden Sonntag im Gallischen Dorf die Orgel und ist als organisatorischer Dienst „Organist“ erfasst.

## 4. Entwürfe

Der Seed erzeugt die Gottesdienste über dieselbe Entwurfsgenerierung wie der Button **Entwürfe erzeugen** in der Matrix. Das sind sechs Gottesdienste pro Woche, insgesamt 36. Wer weitere Wochen braucht, wählt in der Matrix einen späteren Zeitraum und erzeugt dort die Entwürfe.

## 5. Dienstleiter zuweisen {#dienstleiter-zuweisen}

In der Regel leitet der Vorsteher den Sonntagsgottesdienst seiner Gemeinde. Die Matrix zeigt dann Woche für Woche folgende Beispiele (Woche 1 ist die laufende Woche):

| Woche | Was die Matrix zeigt | Regel |
|---|---|---|
| 2 | Miraculix leitet am Sonntag um 09:30 sowohl im Gallischen Dorf als auch in Babaorum. | Doppelbelegung, `no_double_booking` (blockierend) |
| 3 | Miraculix leitet um 09:30 im Gallischen Dorf und um 11:15 in Aquarium. Zwischen beiden liegen nur 15 statt der geforderten 30 Minuten. | Wechselzeit, `travel_time_check` (Warnung) |
| 4 | Obelix ist für Babaorum eingeteilt, hat aber von Freitag bis Montag Urlaub („Wildschweinjagd“). | Abwesenheit, `leader_available` (blockierend) |
| 5 | Automatix spielt um 09:30 in Babaorum die Orgel und soll um 10:00 in Laudanum leiten. | Doppelbelegung mit einem Dienst, `no_double_booking` |
| 5 | Aquarium hat am Sonntag keinen Dienstleiter. | Lücke |
| 6 | Laudanum am Sonntag und das Gallische Dorf am Mittwoch haben keinen Dienstleiter. | Lücken |

Ein Klick auf eine Zelle öffnet den Zuweisungsdialog. Dort meldet die Konfliktprüfung dieselben Regeln, bevor gespeichert wird. Ein blockierender Konflikt verhindert die Zuweisung. Eine Warnung lässt sich bestätigen. So lassen sich die Beispiele direkt auflösen, etwa indem Majestix in Woche 2 das Gallische Dorf wieder übernimmt. Die Regeln im Detail stehen unter [Konfliktregeln](/features/conflict-rules).

Den Konflikt mit dem Organistendienst sehen nur Personen ab der Rolle `PLANNER`, weil nur sie organisatorische Dienste lesen dürfen.

## 6. Planung freigeben

Die ersten zwei Wochen sind freigegeben (`CONFIRMED`), die übrigen geplant (`PLANNED`). Freigegeben wird monatsweise über **Freigabe** in der Matrix (siehe [Freigabe-Workflow](/features/approval-workflow)). Die Startseite zählt, wie viele Gottesdienste der nächsten vier Wochen schon freigegeben sind.

## 7. Kalender-Abo

Der Seed legt das öffentliche Abo „Demo: öffentliches Kalender-Abo“ an und gibt dessen Adresse einmal aus:

```text
Kalender-Abo des Demo-Bezirks: /api/v1/export/<token>/calendar.ics
```

Gespeichert wird nur der Hash des Tokens. Wer die Ausgabe verpasst hat, legt unter **Export** ein neues Abo an. Ein öffentliches Abo enthält nur freigegebene Gottesdienste und zeigt keine Namen der Dienstleiter. Ein internes Abo zeigt auch Entwürfe und volle Namen (siehe [UC-05](/features/use-cases#uc-05-export)).

## Feiertage

Die kirchlichen Festtage sind ohne Internetzugriff berechnet und erscheinen in der Matrix als Feiertagsspalten. Dazu gehören der Entschlafenen-Gottesdienst im November und die Adventssonntage. Gesetzliche Feiertage lädt ein Bezirksadmin unter **Kalender** mit „Deutsche Feiertage importieren“ nach (siehe [UC-06](/features/use-cases#uc-06-feiertags-import)).
