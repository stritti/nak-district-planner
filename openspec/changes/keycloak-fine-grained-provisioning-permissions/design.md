## Context

Stand nach `harden-keycloak-provisioning` (archiviert 2026-10-20): Confidential Client `nak-planner-provisioning` mit Service Account und `realm-management`-Rollen `manage-users`/`view-users`. Das Backend nutzt nur vier Admin-API-Aufrufe: Benutzer per E-Mail suchen, Benutzer anlegen, bei 409 erneut suchen, `execute-actions-email`. Der mitgelieferte Keycloak ist 26.8 (`docker-compose.prod.yml`, Tag ohne Patch-Version), FGAP v2 gibt es ab 26.2, den Scope `reset-password` ab 26.4. Bis einschließlich 26.8.0 ließ sich eine `reset-password`-Sperre über ein allgemeines Benutzer-Update mit `credentials` (CVE-2026-97177, keycloak/keycloak#53158) und über das Löschen von Credentials (CVE-2026-94001, #53057) umgehen; beides ist in 26.8.1 behoben. Motivation siehe `proposal.md`, Anforderung siehe `specs/approved-user-onboarding/spec.md`.

## Goals / Non-Goals

**Goals:**
- Der Service Account kann die vier Aufrufe ausführen, aber keine Passwörter setzen und keine Rollen, Gruppen, Impersonation oder Delegation nutzen.
- Reproduzierbar über das Setup-Skript, nachweisbar über einen Integrationstest gegen echten Keycloak.

**Non-Goals:**
- Keine Änderung am Backend-Code oder an der Konfiguration der App.
- Keine Einschränkung auf einzelne Gruppen oder Benutzerteilmengen (alle Benutzer des App-Realms bleiben Ziel).
- Keine Unterstützung für Keycloak < 26.8.1 in der dokumentierten Einrichtung; das Skript bricht dort ab.
- Keine Unterstützung für User-Federation ohne Import (z. B. LDAP mit `importEnabled=false`): FGAP-gesteuerte Suchen liefern solche Benutzer nicht; das Skript erkennt das und bricht vor dem Entzug von `view-users` ab.
- Kein Verbot von Löschen und Attributänderungen: Keycloak 26.8 bindet Anlegen und `execute-actions-email` an `manage`, das beides einschließt (siehe Risiken).

## Decisions

**FGAP v2 statt eigener Rollen.** Eigene Composite-Rollen können `manage-users` nicht feiner zerlegen, weil Keycloak die Admin-Rechte an die festen `realm-management`-Rollen bindet. FGAP v2 (Realm-Einstellung *Admin Permissions*, Resource Type *Users*) ist der vorgesehene Weg. Alternative: Webhook-Provider mit eigenem Provisioning-Dienst. Verworfen, weil das einen zusätzlichen Dienst mit denselben Rechteproblemen bedeutet.

**Scopes `view` und `manage`.** Laut Admin-Handbuch 26.8 decken `manage` Anlegen, Bearbeiten und Löschen ab, und `execute-actions-email` verlangt derzeit `manage`, nicht `reset-password` (keycloak/keycloak#51411). `view` wird für Suche und Lesen gebraucht. `map-roles`, `manage-group-membership`, `impersonate` und `delegate` bleiben ungesetzt. Der erste Task bestätigt das gegen die eingesetzte Version; ändert Keycloak die Zuordnung, wird die Spec angepasst.

**Role-Policy statt Client-Policy.** `view`-Permissions werden für Benutzerabfragen teilweise vorab ausgewertet und funktionieren laut Handbuch 26.8 nur mit User-, Group-, Role- oder unterstützten Aggregated-Policies. Eine Client-Policy würde die Suche per E-Mail nach dem Entzug von `view-users` brechen. Deshalb bekommt der Service Account eine eigene Realm-Rolle `nak-planner-provisioner`, und die Permission referenziert eine Role-Policy darauf. Die Rolle bleibt stabil, auch wenn der Service-Account-Benutzer neu angelegt wird; eine User-Policy müsste dann aktualisiert werden. Role-Policies berücksichtigen standardmäßig nur Rollen im Scope des anfragenden Clients; das Skript trägt `nak-planner-provisioner` deshalb idempotent in die Role-Scope-Mappings des Provisioning-Clients ein, damit es auch mit `Full Scope Allowed = false` funktioniert. Die Rolle selbst gewährt in Keycloak nichts außer über diese Policy.

**`reset-password` explizit sperren.** Ohne eigene `reset-password`-Permission fällt Keycloak 26.8 auf `manage` zurück; der Service Account könnte dann Passwörter beliebiger Benutzer setzen und Konten übernehmen. Das Skript legt deshalb eine Users-Permission mit Scope `reset-password` an, deren Role-Policy auf eine nie zugewiesene Realm-Rolle `nak-planner-password-reset` zeigt. Damit existiert die Permission und gewährt niemandem etwas. Existiert die Rolle bereits, prüft das Skript, dass sie weder direkt noch über Gruppen oder Composite-Rollen zugewiesen ist, und bricht sonst ab; eine zugewiesene Rolle würde aus der Sperre eine Freigabe machen. Weil Keycloak bei mehreren Permissions auf denselben Scope Deny-Overrides anwendet, würde diese Sperre auch andere Admins treffen, denen eine bestehende Permission `reset-password` für alle Benutzer gibt. Das Setup übernimmt den Scope deshalb exklusiv: Findet es eine fremde `reset-password`-Permission für alle Benutzer, bricht es ab. Die Doku nennt das; Passwort-Resets durch Helpdesk-Admins laufen weiter über `realm-management`-Rollen oder den Self-Service-Flow. Eine negative Policy auf `nak-planner-provisioner` wäre verworfen, weil sie allen anderen FGAP-ausgewerteten Admins das Recht gewähren würde. Der Spike prüft, dass `execute-actions-email` danach weiter funktioniert; verlangt Keycloak dafür künftig `reset-password` (keycloak/keycloak#51411), muss der Change neu bewertet werden.

**Nur alle Benutzer als Ziel, exklusives Modell.** Ressourcenspezifische Users-Permissions haben in FGAP v2 Vorrang vor der Permission für alle Benutzer. Existieren im Realm schon solche Permissions, könnten betroffene Benutzer für den Service Account unsichtbar werden. Außerdem müssen alle Permissions auf dieselbe Ressource und denselben Scope zustimmen; eine fremde Permission für alle Benutzer mit `view` oder `manage` würde den Provisioner sperren und umgekehrt. Das Skript sucht vor jeder Änderung nach fremden Users-Permissions mit konkreten Benutzern oder mit `view`, `manage` bzw. `reset-password` für alle Benutzer und bricht mit deren Namen ab. Die Doku nennt das exklusive Modell als Voraussetzung.

**Legacy-Rollen zuletzt entziehen.** Das Skript legt erst Policy und Permissions an und entzieht danach `manage-users`/`view-users`, damit ein Abbruch mittendrin nicht zu einem Service Account ohne jede Berechtigung führt. Weil Admin-Rollen auch über Gruppen oder Composite-Rollen geerbt werden können und FGAP dann umgehen, prüft das Skript danach die effektiven `realm-management`-Rollen und bricht mit Rolle und Quelle ab, statt Gruppenmitgliedschaften selbst zu ändern.

**Integrationstest mit Keycloak-Container.** Ein eigener pytest-Marker startet Keycloak in der Version aus `docker-compose.prod.yml` mit den Features `token-exchange-delegation` und `parameterized-scopes` (sonst würde die Delegationsprüfung vor der FGAP-Auswertung scheitern), führt das Setup-Skript aus und prüft die Szenarien der Spec mit dem Client-Credentials-Token. Läuft im CI als eigener Job, damit die Unit-Tests schnell bleiben.

## Risks / Trade-offs

- [`manage` umfasst auch Löschen und Attribut-Änderungen] → Bewusst akzeptiert und dokumentiert: Ein kompromittiertes Backend könnte Benutzer löschen oder ändern (Verfügbarkeit, Integrität), aber keine Passwörter direkt setzen und keine Rollen oder Gruppen vergeben.
- [Kontoübernahme über E-Mail-Änderung plus Einladung] → `manage` erlaubt, die E-Mail eines bestehenden Benutzers auf eine fremde Adresse zu ändern und danach `execute-actions-email` mit `UPDATE_PASSWORD` auszulösen. Bei Konten ohne zweiten Faktor kann ein Angreifer so ein Passwort setzen und sich als derselbe Keycloak-Benutzer mit dessen App-Memberships anmelden. Der Weg lässt sich mit FGAP nicht sperren, solange das Backend selbst Einladungen auslöst; mit den bisherigen `realm-management`-Rollen bestand er ebenfalls (zusätzlich zum direkten Passwort-Reset). Gegenmaßnahmen: OTP-Pflicht für Konten mit App-Rolle ab `DISTRICT_ADMIN` (ein Passwort allein reicht dann nicht; Credential-Löschung ist gesperrt), Keycloak-Admin-Events mit Alarm auf `UPDATE` von E-Mail-Adressen durch den Service Account, und der Integrationstest dokumentiert den Pfad als bekanntes Verhalten. Ob dieses Restrisiko akzeptiert wird, entscheidet der Projektverantwortliche vor dem Merge.
- [Delegation] → `delegate` wird nicht vergeben; der Integrationstest stellt eine Token-Exchange-Anfrage mit Delegation und prüft, dass weder Delegations-Scope noch `may_act` im Token stehen.
- [FGAP-v2-Fehler in Keycloak, z. B. unerwartete Denies bei überlappenden Permissions] → Genau eine Permission pro Scope-Set, Integrationstest auf der konkreten Version.
- [Externer Keycloak < 26.8.1] → Skript prüft die Serverversion und bricht ohne Änderungen ab; die Upgrade-Notiz nennt 26.8.1 als Mindestversion. Bis zum Keycloak-Update läuft der bisherige Rollen-Ansatz weiter, ohne die neue Anforderung zu erfüllen.

## Migration Plan

1. Keycloak auf mindestens 26.8.1; `docker-compose.prod.yml` pinnt `26.8.1` statt `26.8`.
2. Setup-Skript erneut gegen den Realm ausführen (Befehl wie in `production-compose.md`) oder Permissions laut Doku in der Admin-Konsole anlegen und danach die zwei Rollen entziehen.
3. Eine Testfreigabe durchführen; `idp_provision_status` muss wie bisher `CREATED_INVITED` bzw. `EXISTING…` sein.
4. Rollback: Rollen `manage-users`/`view-users` wieder zuweisen; Admin Permissions können aktiv bleiben.
