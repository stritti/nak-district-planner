# Rollenkonzept

Dieses Dokument beschreibt die verbindlichen fachlichen Rollengrenzen des NAK Bezirksplaners.
Der OpenSpec-Change [multi-unit-memberships-and-superadmin-management](../openspec/changes/multi-unit-memberships-and-superadmin-management/proposal.md)
erweitert das Modell um mehrere unabhängige Mitgliedschaften und die Ernennung weiterer
Superadmins. Er definiert ein **Zielmodell**; die Umsetzung ist noch nicht abgeschlossen.

::: info Implementierungsstand
Der Bestand nutzt `users.is_superadmin` und `memberships` mit
`(user_sub, role, scope_type, scope_id)` als Eindeutigkeits-Constraint.
Die Umstellung auf genau eine Rolle je Scope, sichere Delegation des Superadmin-Status und
die neuen Verwaltungsfunktionen sind offene OpenSpec-Aufgaben.
:::

## 1. Übersicht

Der NAK Bezirksplaner ist eine mandantenfähige Anwendung. Die Mandanten-Hierarchie ist:

```text
System (globaler Admin)
  └── Bezirk (District)
        ├── Gemeindegruppe (CongregationGroup)  [optional]
        │     └── Gemeinde (Congregation)
        └── Gemeinde (Congregation)
```

Eine Mitgliedschaft besitzt genau einen Scope (Bezirk oder Gemeinde) und eine Rolle.
Ein Benutzer kann **mehrere Mitgliedschaften über beliebig viele Bezirke und Gemeinden**
besitzen, auch gleichzeitig in unterschiedlichen Bezirken. Berechtigungen gelten nur innerhalb
des jeweiligen effektiven Scopes. Der in dieser Matrix historisch als `system_admin`
bezeichnete Systemzugriff wird technisch über den globalen Benutzerstatus
`users.is_superadmin` abgebildet und benötigt keine Mitgliedschaft.

**Überblick der Rollen:**

| Rolle | Geltungsbereich | Zweck |
|-------|----------------|-------|
| `system_admin` | Systemweit | Plattformbetrieb, mandantenübergreifend |
| `district_admin` | Ein Bezirk | Administrative Verantwortung für den Bezirk |
| `congregation_admin` | Eine Gemeinde | Administrative Verantwortung für die Gemeinde |
| `planner` | Ein Bezirk | Dienstplanung ohne Administrationsrechte |
| `viewer` | Bezirk oder Gemeinde | Nur-Lesen-Zugriff |

---

## 2. Rollen

### 2.1 `system_admin` – System-Administrator

**Geltungsbereich:** Systemweit (mandantenübergreifend)

**Beschreibung:** Technischer Administrator mit vollem Zugriff. Für den Betrieb der Plattform, nicht für die kirchliche Verwaltung gedacht.

**Berechtigungen:**
- Alle Bezirke anlegen, bearbeiten, löschen
- Alle Benutzer verwalten (anlegen, Rollen zuweisen, deaktivieren)
- Alle Systemeinstellungen verwalten
- Lesezugriff auf alle Daten aller Mandanten

---

### 2.2 `district_admin` – Bezirks-Administrator

**Geltungsbereich:** Ein bestimmter Bezirk

**Beschreibung:** Verantwortliche Person auf Bezirksebene (z. B. Bezirksältester oder Beauftragter). Verwaltet den Bezirk und alle dazugehörigen Gemeinden.

**Berechtigungen:**
- Bezirkseinstellungen bearbeiten (Name, Bundesland-Kürzel)
- Gemeinden anlegen, bearbeiten, löschen
- Gemeindegruppen verwalten
- Bezirks-Events erstellen, bearbeiten, veröffentlichen, löschen
- Dienstplanung: ServiceAssignments für alle Gemeinden des Bezirks erstellen und bearbeiten
- Kalender-Integrationen für den Bezirk und alle Gemeinden verwalten
- Export-Tokens (PUBLIC/INTERNAL) erstellen und löschen
- Feiertage manuell importieren
- Benutzer einladen und Rollen innerhalb des Bezirks zuweisen

---

### 2.3 `congregation_admin` – Gemeinde-Administrator

**Geltungsbereich:** Eine bestimmte Gemeinde

**Beschreibung:** Verantwortliche Person auf Gemeindeebene (z. B. Gemeindeleiter oder Beauftragter). Verwaltet die eigene Gemeinde.

**Berechtigungen:**
- Gemeindeeinstellungen bearbeiten (Name, Gottesdienstzeiten)
- Gemeinde-Events erstellen, bearbeiten, veröffentlichen, löschen
- Kalender-Integrationen für die eigene Gemeinde verwalten
- Dienstmatrix des Bezirks **lesen** (inkl. ServiceAssignments aller Gemeinden des Bezirks)
- ServiceAssignments der eigenen Gemeinde erstellen und bearbeiten
- Export-Tokens für die eigene Gemeinde erstellen und löschen
- Benutzer für die **eigene Gemeinde** einladen (delegiert durch `district_admin`)

**Keine Berechtigungen für:**
- Bezirkseinstellungen oder andere Gemeinden ändern
- ServiceAssignments für andere Gemeinden erstellen

---

### 2.4 `planner` – Planer / Dienstverantwortlicher

**Geltungsbereich:** Ein bestimmter Bezirk

**Beschreibung:** Unterstützt die Dienstplanung. Hat keinen administrativen Zugriff, aber darf Dienste zuweisen und bestätigen.

**Berechtigungen:**
- Dienstmatrix des Bezirks lesen
- ServiceAssignments für alle Gemeinden des Bezirks erstellen, bearbeiten und bestätigen
- Events aller Gemeinden des Bezirks lesen
- Export-Tokens für den eigenen Bezirk erstellen und löschen

**Keine Berechtigungen für:**
- Bezirks- oder Gemeindeeinstellungen ändern
- Events erstellen oder löschen
- Kalender-Integrationen verwalten

---

### 2.5 `viewer` – Betrachter (nur lesen)

**Geltungsbereich:** Ein Bezirk oder eine Gemeinde

**Beschreibung:** Lesezugriff auf Termine und Dienstpläne. Geeignet für Amtsträger, die den Planungsstand einsehen, aber nichts ändern sollen.

**Berechtigungen:**
- Events des zugeordneten Bezirks / der Gemeinde lesen
- ServiceAssignments lesen
- Dienstmatrix lesen
- Export-Tokens für den eigenen Zuständigkeitsbereich erstellen und löschen

**Keine Berechtigungen für:**
- Daten ändern (kein Schreibzugriff auf Events, ServiceAssignments)

---

### 2.6 Öffentlicher Zugang (Kalender-Abonnement, ohne Login)

**Geltungsbereich:** Keine Web-App-Authentifizierung – ausschließlich über Export-Token

**Beschreibung:** Externe Kalender-Apps (z. B. Google Calendar, Apple Calendar) können Termine über abonnierbare ICS-Links beziehen. Dies ersetzt **keinen** Login in die Web-App; der Zugang zur Planungsoberfläche erfordert stets ein Benutzerkonto.

**Token-Typen (bereits implementiert, siehe UC-05):**
| Token-Typ | Sichtbarkeit | Dienstleiter-Namen |
|-----------|-------------|-------------------|
| `PUBLIC`  | Nur `visibility=PUBLIC` und `status=PUBLISHED` | Anonymisiert (z. B. "Dienstleiter") |
| `INTERNAL` | Inkl. `visibility=INTERNAL` | Vollständige Namen |

---

## 3. Berechtigungsmatrix

Die folgende Tabelle gibt einen Überblick über die Berechtigungen je Ressource und Rolle.

**Legende:** ✅ erlaubt · 🔒 nur eigene Ressourcen (bei Benutzerverwaltung: nur wenn Delegation durch `district_admin` aktiviert wurde) · 👁️ nur lesen · ❌ nicht erlaubt

| Ressource / Aktion                        | system_admin | district_admin | congregation_admin | planner | viewer |
|-------------------------------------------|:---:|:---:|:---:|:---:|:---:|
| **Bezirke**                               |     |     |     |     |     |
| Bezirk anlegen / löschen                  | ✅  | ❌  | ❌  | ❌  | ❌  |
| Bezirk bearbeiten                         | ✅  | ✅  | ❌  | ❌  | ❌  |
| Bezirk lesen                              | ✅  | ✅  | 👁️  | 👁️  | 👁️  |
| **Gemeinden**                             |     |     |     |     |     |
| Gemeinde anlegen / löschen               | ✅  | ✅  | ❌  | ❌  | ❌  |
| Gemeinde bearbeiten                       | ✅  | ✅  | 🔒  | ❌  | ❌  |
| Gemeinde lesen                            | ✅  | ✅  | ✅  | ✅  | ✅  |
| **Events**                                |     |     |     |     |     |
| Event erstellen (Bezirksebene)            | ✅  | ✅  | ❌  | ❌  | ❌  |
| Event erstellen (Gemeindeebene)           | ✅  | ✅  | 🔒  | ❌  | ❌  |
| Event bearbeiten / löschen               | ✅  | ✅  | 🔒  | ❌  | ❌  |
| Event veröffentlichen (`PUBLISHED`)      | ✅  | ✅  | 🔒  | ❌  | ❌  |
| Events lesen                              | ✅  | ✅  | ✅  | ✅  | ✅  |
| **Dienstplanung (ServiceAssignment)**     |     |     |     |     |     |
| Dienstmatrix lesen (alle Gemeinden)       | ✅  | ✅  | ✅  | ✅  | ✅  |
| Zuweisung erstellen / bearbeiten (eigene Gemeinde) | ✅ | ✅ | 🔒 | ✅ | ❌ |
| Zuweisung erstellen / bearbeiten (alle Gemeinden) | ✅ | ✅ | ❌ | ✅ | ❌ |
| Zuweisung bestätigen (`CONFIRMED`)       | ✅  | ✅  | 🔒  | ✅  | ❌  |
| **Kalender-Integrationen**               |     |     |     |     |     |
| Integration erstellen / löschen          | ✅  | ✅  | 🔒  | ❌  | ❌  |
| Integration bearbeiten / Sync auslösen  | ✅  | ✅  | 🔒  | ❌  | ❌  |
| **Export-Tokens**                         |     |     |     |     |     |
| `PUBLIC`-Token erstellen / löschen       | ✅  | ✅  | 🔒  | ✅  | ✅  |
| `INTERNAL`-Token erstellen / löschen     | ✅  | ✅  | 🔒  | ✅  | ✅  |
| Token auflisten                           | ✅  | ✅  | 🔒  | ✅  | ✅  |
| **Benutzerverwaltung**                    |     |     |     |     |     |
| Benutzer anlegen (systemweit)            | ✅  | ❌  | ❌  | ❌  | ❌  |
| Benutzer einladen (im Bezirk)            | ✅  | ✅  | ❌  | ❌  | ❌  |
| Benutzer einladen (eigene Gemeinde, delegiert) | ✅ | ✅ | 🔒 | ❌ | ❌ |
| Rollen zuweisen (im Bezirk)              | ✅  | ✅  | ❌  | ❌  | ❌  |
| Rollen zuweisen (eigene Gemeinde, delegiert) | ✅ | ✅ | 🔒 | ❌ | ❌ |
| **Feiertags-Import**                      |     |     |     |     |     |
| Manueller Import                          | ✅  | ✅  | ❌  | ❌  | ❌  |

---

## 4. Technische Umsetzungshinweise (Vorschlag)

::: info Hinweis
Dieser Abschnitt beschreibt Vorschläge für die technische Umsetzung. Er wird im Zuge von Phase 4 ausgearbeitet.
:::

### 4.1 Authentifizierung via Keycloak

Die Anwendung nutzt **Keycloak** als Identity Provider. Dies ermöglicht:
- Login über **Google**, **Microsoft** und weitere OAuth2-Provider (Social Login)
- Eigene Benutzernamen-/Passwort-Anmeldung über Keycloak selbst
- Einladungsworkflow via Keycloak (E-Mail-Einladung, Selbstregistrierung mit Freigabe, manuelle Anlage)
- Audit-Log für Login-Ereignisse bereits in Keycloak integriert

Das Backend verifiziert ausschließlich JWT-Access-Tokens, die von Keycloak ausgestellt wurden (JWKS-Validierung). Passwörter werden **nicht** im Backend gespeichert.

**Empfohlene Token-Laufzeiten (Keycloak-Realm-Einstellungen):**

| Token-Typ | Empfohlene Dauer | Begründung |
|-----------|-----------------|-----------|
| Access Token | 15 Minuten | Kurze Lebensdauer reduziert das Risiko bei Diebstahl |
| Refresh Token | 8 Stunden (SSO-Session: 8 h) | Entspricht einem Arbeitstag; automatische Verlängerung solange aktiv |
| Offline Token | Optional, 30 Tage | Für API-Clients ohne interaktiven Login |

### 4.2 Datenbankmodell

Das vorhandene Datenmodell speichert OIDC-Identitäten und Scope-Berechtigungen getrennt:

```text
users
  id, sub (UNIQUE), email, username, name, is_superadmin, created_at, updated_at

memberships
  id, user_sub (FK -> users.sub), role, scope_type, scope_id,
  created_at, updated_at
  -- scope_type = DISTRICT     -> scope_id referenziert einen Bezirk
  -- scope_type = CONGREGATION -> scope_id referenziert eine Gemeinde
```

Eine Benutzeridentität kann beliebig viele Mitgliedschaften in unterschiedlichen Bezirken
und Gemeinden besitzen. Die Bezirkszuordnung steht **nicht** als einzelnes `district_id`
auf dem Benutzer. Der Superadmin-Status ist ein globales Attribut von `users` und
keine zusätzliche Rolle innerhalb einer Mitgliedschaft.

**Migration im OpenSpec-Change:**
Die aktuelle Unique-Constraint `(user_sub, role, scope_type, scope_id)` lässt
verschiedene Rollen desselben Benutzers im gleichen Scope zu. Das Zielmodell hat
genau **eine** effektive Rollen-Zuordnung je Kombination aus
`(user_sub, scope_type, scope_id)`. Eine Migration konsolidiert vorhandene
Dubletten deterministisch auf die höchste effektive Rolle und sichert die
entfallenden Datensätze für Audit und Downgrade. Anschließend erzwingt eine
Datenbank-Unique-Constraint diese Eindeutigkeit. Gleichzeitige Zuweisungen
müssen transaktional und idempotent sein.

### 4.3 Rollen-Speicherung und JWT-Token-Inhalt

Die OIDC-Authentifizierung liefert eine verifizierte Benutzeridentität (`sub`).
Die Autorisierung basiert auf den aktuellen Datenbankwerten in `users` und
`memberships`, **nicht** auf frei eingebrachten Rollen-/Superadmin-Claims
oder der von der Clientoberfläche ausgewählten Einheit.

Bei jeder relevanten Request-Autorisierung müssen Rollen und Superadmin-Status
aus vertrauenswürdigen aktuellen Daten stammen. Insbesondere darf ein Entzug
des Superadmin-Status nicht durch veraltete Cache-Einträge, laufende Sessions
oder die Bootstrap-Funktion rückgängig gemacht werden.

Die Benutzerverwaltung bearbeitet Zuordnungen pro Scope; neue Zuordnungen
ersetzen keine vorhandenen in anderen Einheiten. Ein bestehender Superadmin
kann den globalen Status eines sicher verknüpften Kontos vergeben und entziehen;
der letzte verbleibende Superadmin bleibt geschützt. Die Runtime-Datenbankrolle
erhält dafür keine uneingeschränkten Schreibrechte auf `users.is_superadmin`.
Details und Negativszenarien stehen in den verlinkten OpenSpec-Anforderungen.

### 4.4 Middleware / Permission-Guard

Die Berechtigungsprüfung soll als FastAPI-Dependency (ähnlich dem bestehenden `verify_api_key`) implementiert werden:

```python
# Beispiel (Pseudocode)
async def require_role(
    required_role: Role,
    district_id: UUID | None = None,
) -> User:
    ...
```

### 4.5 Audit-Log

Sicherheitsrelevante Aktionen werden in einer `AuditLog`-Tabelle festgehalten:

```bash
AuditLog
  id, timestamp, user_id (FK), action (enum), resource_type, resource_id,
  district_id (nullable), congregation_id (nullable), details (JSON)
```

Relevante Aktionen: Login, Logout, Rollenvergabe/-entzug, Benutzer deaktiviert, Event gelöscht, ServiceAssignment geändert.

### 4.6 Benutzer deaktivieren

Wird ein Benutzer deaktiviert (`is_active = false`):
- Bestehende `ServiceAssignment`-Einträge bleiben erhalten (historische Daten).
- Neue Zuweisungen an diesen Benutzer sind nicht mehr möglich.
- Keycloak-Account wird ebenfalls deaktiviert (kein Login mehr möglich).

---

## 6. Implementierungsstatus

Dieser Abschnitt dokumentiert, welche Permission-Guards in den einzelnen API-Routern aktiv sind (Stand: Phase 1 P0-Blitzer).

:   **Legende:** ✅ Vollständig · ◐ Teilweise (congregation-fallback ergänzt) · 🔷 Abweichendes Auth-Modell · ❌ Nicht geschützt

| Router | Guard-Status | Anmerkungen |
|--------|-------------|-------------|
| `events.py` | ◐ | `assert_has_role_in_congregation`-Fallback für `create_event`/`update_event` ergänzt. Lesen-Dienste bleiben öffentlich innerhalb des Bezirks. |
| `districts.py` | ◐ | `update_congregation` hat `assert_has_role_in_congregation`-Fallback. |
| `calendar_integrations.py` | ◐ | `create`/`update`/`delete` haben `assert_has_role_in_congregation`-Fallback. |
| `leaders.py` | ✅ | Vollständige Guards via `assert_has_role_in_district`/`assert_has_role_in_congregation`. |
| `service_assignments.py` | ✅ | Vollständige Guards via `assert_has_role_in_district`/`assert_has_role_in_congregation`. |
| `invitations.py` | ✅ | Vollständige Guards via `assert_has_role_in_district`/`assert_has_role_in_congregation`. |
| `registrations.py` | ✅ | `assert_has_role_in_district` für listen/delete (selbst-registrierte User). |
| `system.py` | ✅ | `system_admin`-Guard für alle administrativen Endpoints. |
| `export.py` | 🔷 | Token-basiertes Auth-Modell (kein Rollen-Guard nötig; Berechtigung ergibt sich aus Token-Typ PUBLIC/INTERNAL). |
| `auth.py` | 🔷 | Verwendet `get_current_user` direkt; Rollenprüfung erfolgt nachgelagert in den aufgerufenen Endpoints. |

### 6.1 Cross-Tenant-Isolation

Die Mandantentrennung wird auf Permission-Ebene durchgesetzt:

- **`has_role_in_district(district_id, …)`** — prüft, ob der User eine Rolle im angegebenen Bezirk besitzt
- **`assert_has_role_in_district(district_id, …)`** — wie oben, löst aber `HTTPException(403)` bei Fehlschlag
- **`has_role_in_congregation(congregation_id, …)`** — prüft Gemeinde-Scope innerhalb des Bezirks
- **`assert_has_role_in_congregation(congregation_id, …)`** — wie oben, mit 403 bei Fehlschlag
- **Sonderfall `system_admin`** — überspringt alle Mandantenprüfungen (volle Zugriffe)

Die Permissions-Schicht ist als reine Python-Domainlogik implementiert (keine DB-Anfragen für Rollenabfragen; erwartet `AuthContext` mit vorab geladenen `Membership`-Objekten).

### 6.2 Router-Abdeckung nach Rolle

Die folgende Tabelle zeigt, welche Rollen in welchen Endpoints aktiv geprüft werden:

| Rolle | Router mit aktivem Guard |
|-------|-------------------------|
| `system_admin` | `system.py`, alle `*_admin`-Endpoints in anderen Routern (als Fallback) |
| `district_admin` | `districts.py`, `events.py`, `leaders.py`, `service_assignments.py`, `calendar_integrations.py`, `invitations.py`, `registrations.py` |
| `congregation_admin` | `events.py` (create/update), `districts.py` (update_congregation), `calendar_integrations.py` (CRUD), `leaders.py` (eigene Gemeinde), `service_assignments.py` (eigene Gemeinde) |
| `planner` | `service_assignments.py`, `events.py` (lesen), `leaders.py` (lesen) |
| `viewer` | Lesende Endpoints in allen Routern |

> **Hinweis:** Die tatsächliche Berechtigungsprüfung erfolgt stets über die `assert_has_role_in_*`-Familie. Ein Endpoint, der z. B. `assert_has_role_in_district(…, [DISTRICT_ADMIN, PLANNER])` aufruft, prüft beide Rollen — unabhängig von der konkreten Router-Zuordnung.

## 5. Design-Entscheidungen

Die folgenden Entscheidungen wurden im Rahmen der Konzeptentwicklung getroffen und sind verbindlich für die Implementierung.

| # | Frage | Entscheidung |
|---|-------|-------------|
| 1 | Rollenvererbung | Die maßgebliche RBAC-Hierarchie lautet `DISTRICT_ADMIN > CONGREGATION_ADMIN > PLANNER > VIEWER`. Höhere Rollen schließen niedrigere Berechtigungen nur innerhalb des nach den Scope-Regeln wirksamen Bereichs ein; Rechte übertragen sich nicht auf fremde Einheiten. |
| 2 | Bezirkszuordnung | Ein Benutzer kann mehrere Bezirks- und Gemeindemitgliedschaften besitzen, auch über Bezirksgrenzen hinweg. Jede Mitgliedschaft speichert Scope und Rolle in `memberships`. `users.is_superadmin` ist davon unabhängig. Die neue Ein-Rolle-pro-Scope-Constraint wird im zugehörigen OpenSpec-Change eingeführt. |
| 3 | Gemeindegruppen | Keine eigene Berechtigungsstufe für Gruppen. Gruppen dienen der Kooperation (gemeinsame Gottesdienste, gegenseitige Unterstützung) und werden vollständig durch `district_admin` verwaltet. |
| 4 | Einladungsworkflow | **Alle drei Varianten** werden unterstützt: E-Mail-Einladung (durch `district_admin`), Selbstregistrierung mit Freigabe, manuelle Anlage durch `system_admin`. Technisch über Keycloak abgebildet. |
| 5 | Sichtbarkeit ServiceAssignments | **Ja.** `congregation_admin` kann die Dienstleiter-Namen aller Gemeinden im gleichen Bezirk in der Matrixansicht sehen. |
| 6 | Datenschutz bei Export-Tokens | **Jeder** angemeldete Benutzer darf Export-Tokens für den eigenen Zuständigkeitsbereich erstellen (PUBLIC und INTERNAL). Die Sichtbarkeit ergibt sich aus den Datenzugriffsrechten der jeweiligen Rolle. |
| 7 | Authentifizierung / SSO | **Keycloak** wird als Identity Provider eingebunden. Google- und Microsoft-Login werden über Keycloak aktiviert. |
| 8 | Session-Dauer | **Empfehlung:** Access Token 15 min, Refresh Token / SSO-Session 8 h. Konfiguration über Keycloak Realm-Einstellungen (siehe Abschnitt 4.1). |
| 9 | Audit-Log | **Ja.** Sicherheitsrelevante Aktionen werden in einer `AuditLog`-Tabelle festgehalten (siehe Abschnitt 4.5). |
| 10 | Rollendelegation | **Ja.** Ein `district_admin` kann einem `congregation_admin` das Recht delegieren, Benutzer für die eigene Gemeinde einzuladen und deren Rollen zu verwalten. |
| 11 | Benutzer deaktivieren | Bestehende `ServiceAssignment`-Einträge werden **beibehalten**. Neue Zuweisungen an deaktivierte Benutzer sind nicht mehr möglich (siehe Abschnitt 4.6). |
| 12 | Gast-Zugang | **Immer ein Login erforderlich.** Die Web-App hat keinen anonymen Gastmodus. Kalender-Abonnements laufen weiterhin über Export-Tokens (ICS, kein Web-Login nötig). |
