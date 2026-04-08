## Context

Der NAK District Planner verwendet bereits OIDC fuer Authentifizierung sowie Membership-basiertes RBAC fuer Authorisierung. Benutzer koennen sich selbst registrieren und durch Bezirksadministratoren freigegeben werden, aber der aktuelle Freigabeschritt erzeugt noch keinen konsistenten, durchgesetzten Benutzerzugriff auf Bezirk/Gemeinde-Ebene.

Aktuell sind drei Probleme relevant:
- Ein erfolgreicher IDP-Login ist nicht strikt an eine explizite fachliche Freigabe gekoppelt.
- Die Freigabeentscheidung enthaelt noch keine verbindliche Rollen- und Scope-Zuweisung fuer den Benutzerzugriff.
- Der optionale Token beim Self-Registration-Flow wird nur unvalidiert dekodiert, was fuer eine sichere `user_sub`-Zuordnung nicht ausreicht.

Stakeholder sind Bezirksadministratoren (Freigabe), registrierte Benutzer (Onboarding) und Betreiber (sichere Mandantentrennung).

## Goals / Non-Goals

**Goals:**
- Login ueber IDP bleibt moeglich, aber produktiver Zugriff wird erst nach interner Freigabe und Scope-Zuweisung aktiviert.
- Freigaben bilden die autoritative Quelle fuer effektive Memberships (Role, ScopeType, ScopeId).
- Alle geschuetzten Endpunkte erzwingen Membership-basierte Zugriffskontrolle, begrenzt auf Bezirk/Gemeinde.
- Die Zuordnung `registrierung -> user_sub -> memberships` wird sicher und auditierbar.

**Non-Goals:**
- Keine Ablage der Rollenlogik in IDP-Gruppen als Source-of-Truth.
- Keine Einfuehrung von ABAC oder Policy-Engine.
- Keine Multi-IDP-Federation in einer Instanz.

## Decisions

### Decision 1: Interne Freigabe ist Source-of-Truth fuer Zugriff
**Alternativen:**
1. IDP-Gruppen als fuehrende Rollenquelle
2. Hybrid mit gleichwertiger Autoritaet
3. Interne Freigabe als fuehrende Quelle

**Entscheidung:** Option 3.

**Rationale:**
- Bezirks-/Gemeindelogik ist fachlich intern und nicht stabil zwischen verschiedenen IDPs modelliert.
- OIDC bleibt provider-agnostisch; Rollen bleiben in der Domane und DB kontrollierbar.
- Admins koennen Freigaben und Entzuege ohne IDP-Adminrechte durchfuehren.

### Decision 2: Approval muss explizite Rollen- und Scope-Zuweisung enthalten
**Alternativen:**
1. Approval nur als Statuswechsel (ohne Membership-Zuweisung)
2. Automatische Default-Rolle fuer gesamten Bezirk
3. Pflichtfelder role + scope_type + scope_id im Approval

**Entscheidung:** Option 3.

**Rationale:**
- Verhindert unbeabsichtigte Ueberberechtigungen.
- Macht den Zugriff reproduzierbar und testbar.
- Erlaubt feinere Vergabe (nur Gemeinde statt ganzer Bezirk).

### Decision 3: Zugriffsgate vor Fachlogik
**Alternativen:**
1. Nur Endpunkt-spezifische Rollenpruefungen
2. Globaler Guard plus bestehende Rollenpruefungen

**Entscheidung:** Option 2.

**Rationale:**
- Benutzer ohne Membership werden frueh und einheitlich blockiert.
- Bestehende `assert_has_role_in_district`/`assert_has_role_in_congregation` bleiben fuer Feinpruefung aktiv.

### Decision 4: Optionales Bearer-Token bei Registrierung wird validiert
**Alternativen:**
1. Unvalidiertes JWT-Decoding
2. Token ignorieren
3. Token validieren und nur dann `user_sub` uebernehmen

**Entscheidung:** Option 3.

**Rationale:**
- Schuetzt vor Spoofing der Benutzeridentitaet.
- Erhaelt den oeffentlichen Registrierungspfad (weiterhin ohne Token moeglich).

## Risks / Trade-offs

- [Bestehende Benutzer ohne Membership verlieren Zugriff] -> Vor Aktivierung Guard Backfill-Skript/Runbook fuer Initial-Memberships ausrollen.
- [Admin-Workflow wird komplexer] -> UI mit klaren Defaults (z. B. VIEWER) und Validierung fuer Scope-Auswahl.
- [Fehlende `user_sub` bei Alt-Registrierungen] -> Definierte Linking-Strategie beim ersten Login, inkl. Konflikterkennung und manueller Klaerung.
- [Mehr API-Fehlerfaelle im Onboarding] -> Einheitliche Fehlercodes (`401` invalid token, `403` pending approval) und klare Frontend-Messages.

## Migration Plan

1. Registration-Datenmodell um Approval-Zuordnungsfelder erweitern (Migration).
2. Approval-Endpoint auf verpflichtende Rollen-/Scope-Zuweisung umstellen und Membership-Erzeugung integrieren.
3. Access-Guard fuer geschuetzte Endpunkte einfuehren (Feature-Flag optional waehrend Rollout).
4. Backfill bestehender Benutzer mit notwendigen Memberships.
5. Frontend fuer Freigabeauswahl und "Freigabe ausstehend" aktualisieren.
6. Nach erfolgreichem Monitoring Feature-Flag entfernen.

Rollback: Guard-Activation per Feature-Flag deaktivieren, neue Approval-Pflicht temporar lockern, Datenmigration bleibt rueckwaertskompatibel.

## Open Questions

1. Soll ein Approval mehrere Memberships in einem Schritt setzen koennen oder initial genau eine?
2. Welche Standardrolle soll im Admin-UI vorbelegt sein (VIEWER oder PLANNER)?
3. Soll ein vorhandener aber invalider Bearer-Token beim Registrieren hart mit `401` abgewiesen werden oder als "nicht vorhanden" behandelt werden?
