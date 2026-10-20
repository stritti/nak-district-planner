## Context

Stand nach `harden-keycloak-provisioning` (archiviert 2026-10-20): Confidential Client `nak-planner-provisioning` mit Service Account und `realm-management`-Rollen `manage-users`/`view-users`. Das Backend nutzt nur vier Admin-API-Aufrufe: Benutzer per E-Mail suchen, Benutzer anlegen, bei 409 erneut suchen, `execute-actions-email`. Der mitgelieferte Keycloak ist 26.8 (`docker-compose.prod.yml`), FGAP v2 gibt es ab 26.2. Motivation siehe `proposal.md`, Anforderung siehe `specs/approved-user-onboarding/spec.md`.

## Goals / Non-Goals

**Goals:**
- Der Service Account kann genau die vier Aufrufe ausführen und sonst nichts im Realm verändern.
- Reproduzierbar über das Setup-Skript, nachweisbar über einen Integrationstest gegen echten Keycloak.

**Non-Goals:**
- Keine Änderung am Backend-Code oder an der Konfiguration der App.
- Keine Einschränkung auf einzelne Gruppen oder Benutzerteilmengen (alle Benutzer des App-Realms bleiben Ziel).
- Kein Ersatz für FGAP v1; ältere Keycloak-Versionen behalten den Rollen-Ansatz.

## Decisions

**FGAP v2 statt eigener Rollen.** Eigene Composite-Rollen können `manage-users` nicht feiner zerlegen, weil Keycloak die Admin-Rechte an die festen `realm-management`-Rollen bindet. FGAP v2 (Realm-Einstellung *Admin Permissions*, Resource Type *Users*) ist der vorgesehene Weg. Alternative: Webhook-Provider mit eigenem Provisioning-Dienst. Verworfen, weil das einen zusätzlichen Dienst mit denselben Rechteproblemen bedeutet.

**Scopes empirisch festlegen.** Die Scope-Liste für *Users* hat sich zwischen Releases geändert (u. a. `reset-password` in 26.4, `delegate` in 26.8). Ausgangspunkt ist `view` plus `manage`; ob `execute-actions-email` `manage` oder `reset-password` verlangt und ob Anlegen ohne `manage-users`-Rolle möglich ist, klärt der erste Task gegen den Endpunkt `admin-permissions` der eingesetzten Version. Ergebnis wird im Design nachgetragen, bevor Skript und Doku geschrieben werden.

**Policy über den Client, nicht über den Benutzer.** Eine Client-Policy auf `nak-planner-provisioning` bleibt stabil, auch wenn der Service-Account-Benutzer neu angelegt wird.

**Legacy-Rollen zuletzt entziehen.** Das Skript legt erst Policy und Permissions an und entzieht danach `manage-users`/`view-users`, damit ein Abbruch mittendrin nicht zu einem Service Account ohne jede Berechtigung führt.

**Integrationstest mit Keycloak-Container.** Ein eigener pytest-Marker startet Keycloak in der Version aus `docker-compose.prod.yml`, führt das Setup-Skript aus und prüft die Szenarien der Spec mit dem Client-Credentials-Token. Läuft im CI als eigener Job, damit die Unit-Tests schnell bleiben.

## Risks / Trade-offs

- [`manage` umfasst auch Löschen und Attribut-Änderungen] → Wenn die eingesetzte Version keinen engeren Scope für Anlegen bietet, bleibt Löschen erlaubt; die Spec-Szenarien werden dann im ersten Task angepasst und der Rest-Risiko dokumentiert. Rollen- und Gruppenzuordnung bleiben in jedem Fall ausgeschlossen.
- [FGAP-v2-Fehler in Keycloak, z. B. unerwartete Denies bei überlappenden Permissions] → Genau eine Permission pro Scope-Set, Integrationstest auf der konkreten Version.
- [Externer Keycloak < 26.2] → Skript erkennt fehlendes FGAP v2 und bricht mit klarer Meldung ab; Doku beschreibt den bisherigen Rollen-Ansatz als Fallback.

## Migration Plan

1. Keycloak auf mindestens 26.2 (mitgeliefert: 26.8).
2. Setup-Skript erneut gegen den Realm ausführen (Befehl wie in `production-compose.md`) oder Permissions laut Doku in der Admin-Konsole anlegen und danach die zwei Rollen entziehen.
3. Eine Testfreigabe durchführen; `idp_provision_status` muss wie bisher `CREATED_INVITED` bzw. `EXISTING…` sein.
4. Rollback: Rollen `manage-users`/`view-users` wieder zuweisen; Admin Permissions können aktiv bleiben.
