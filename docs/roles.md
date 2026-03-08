# Rollenkonzept

Diese Seite beschreibt das geplante Rollenkonzept für den NAK Bezirksplaner. Es dient als Grundlage für den Review und die spätere Implementierung (Phase 4).

::: warning Status: Entwurf (überarbeitet)
Dieses Dokument ist ein Review-Entwurf. Noch keine Implementierung vorhanden. Klärungsbedarf und getroffene Entscheidungen sind am Ende des Dokuments aufgeführt.
:::

## 1. Übersicht

Der NAK Bezirksplaner ist eine mandantenfähige Anwendung. Die Mandanten-Hierarchie ist:

```
System (globaler Admin)
  └── Bezirk (District)
        ├── Gemeindegruppe (CongregationGroup)  [optional]
        │     └── Gemeinde (Congregation)
        └── Gemeinde (Congregation)
```

Das Rollenkonzept muss diese Hierarchie widerspiegeln. Eine Rolle ist immer an einen Mandanten (Bezirk oder Gemeinde) gebunden – mit Ausnahme der systemweiten Rollen.

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

**Keine Berechtigungen für:**
- Bezirks- oder Gemeindeeinstellungen ändern
- Events erstellen oder löschen
- Kalender-Integrationen verwalten
- Export-Tokens verwalten

---

### 2.5 `viewer` – Betrachter (nur lesen)

**Geltungsbereich:** Ein Bezirk oder eine Gemeinde

**Beschreibung:** Lesezugriff auf Termine und Dienstpläne. Geeignet für Amtsträger, die den Planungsstand einsehen, aber nichts ändern sollen.

**Berechtigungen:**
- Events des zugeordneten Bezirks / der Gemeinde lesen
- ServiceAssignments lesen
- Dienstmatrix lesen

**Keine Berechtigungen für:**
- Daten ändern (kein Schreibzugriff)

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
| Token erstellen / löschen                | ✅  | ✅  | 🔒  | ❌  | ❌  |
| Token auflisten                           | ✅  | ✅  | 🔒  | ❌  | ❌  |
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

```
User
  id, keycloak_sub (UNIQUE, eindeutige Keycloak-UUID), email, display_name, is_active, created_at

UserRole
  id, user_id (FK), role (enum), district_id (FK, nullable), congregation_id (FK, nullable)
  UNIQUE(user_id, district_id, congregation_id)
```

- Ein Benutzer kann mehrere Einträge in `UserRole` haben (z. B. `district_admin` in Bezirk A und `viewer` in Bezirk B).
- Innerhalb eines Bezirks oder einer Gemeinde hat ein Benutzer genau **eine** Rolle (`UNIQUE` auf `user_id + district_id + congregation_id`).
- `district_id` und `congregation_id` sind optional und definieren den Geltungsbereich.
- `system_admin` hat keinen Bezirk/Gemeinde-Bezug (beide `NULL`).
- `keycloak_sub` ersetzt `hashed_password` — Passwort-Management liegt vollständig bei Keycloak.

### 4.3 JWT-Token-Inhalt (Claim-Vorschlag)

Das Backend liest die Keycloak-Rollen aus dem JWT-Claim und reichert sie bei Bedarf mit DB-Daten an:

```json
{
  "sub": "keycloak-user-uuid",
  "email": "user@example.com",
  "exp": 1234567890
}
```

Die Rollen werden **nicht** im JWT gespeichert, sondern bei jeder Anfrage aus der `UserRole`-Tabelle geladen (authoritative source of truth im Backend). Dies ermöglicht sofortige Wirksamkeit von Rollenänderungen ohne Token-Refresh.

::: tip Performance
Um die Datenbanklast zu minimieren, werden die geladenen Rollen pro Request im Keycloak-Session-Cache (oder alternativ in Redis mit einer kurzen TTL von ~60 Sekunden) zwischengespeichert. Rollenänderungen wirken sich nach Ablauf des Cache-Fensters aus.
:::

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

```
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

## 5. Getroffene Entscheidungen

::: tip Status
Die folgenden Fragen wurden im Review geklärt.
:::

| # | Frage | Entscheidung |
|---|-------|-------------|
| 1 | Rollenvererbung | Rollen sind **strikt getrennt**. `district_admin` erbt keine `congregation_admin`-Rechte automatisch. Ein Benutzer kann aber mehrere Rollen haben (z. B. `district_admin` im Bezirk **und** `congregation_admin` in einer Gemeinde). |
| 2 | Mehrmandantenfähigkeit | Ein Benutzer hat **genau eine Rolle pro Mandant** (Bezirk oder Gemeinde). Mehrere Mandate sind über separate `UserRole`-Einträge möglich. |
| 3 | Gemeindegruppen | Keine eigene Berechtigungsstufe für Gruppen. Gruppen dienen der Kooperation (gemeinsame Gottesdienste, gegenseitige Unterstützung) und werden vollständig durch `district_admin` verwaltet. |
| 4 | Einladungsworkflow | **Alle drei Varianten** werden unterstützt: E-Mail-Einladung (durch `district_admin`), Selbstregistrierung mit Freigabe, manuelle Anlage durch `system_admin`. Technisch über Keycloak abgebildet. |
| 5 | Sichtbarkeit ServiceAssignments | **Ja.** `congregation_admin` kann die Dienstleiter-Namen aller Gemeinden im gleichen Bezirk in der Matrixansicht sehen. |
| 7 | Authentifizierung / SSO | **Keycloak** wird als Identity Provider eingebunden. Google- und Microsoft-Login werden über Keycloak aktiviert. |
| 8 | Session-Dauer | **Empfehlung:** Access Token 15 min, Refresh Token / SSO-Session 8 h. Konfiguration über Keycloak Realm-Einstellungen (siehe Abschnitt 4.1). |
| 9 | Audit-Log | **Ja.** Sicherheitsrelevante Aktionen werden in einer `AuditLog`-Tabelle festgehalten (siehe Abschnitt 4.5). |
| 10 | Rollendelegation | **Ja.** Ein `district_admin` kann einem `congregation_admin` das Recht delegieren, Benutzer für die eigene Gemeinde einzuladen und deren Rollen zu verwalten. |
| 11 | Benutzer deaktivieren | Bestehende `ServiceAssignment`-Einträge werden **beibehalten**. Neue Zuweisungen an deaktivierte Benutzer sind nicht mehr möglich (siehe Abschnitt 4.6). |
| 12 | Gast-Zugang | **Immer ein Login erforderlich.** Die Web-App hat keinen anonymen Gastmodus. Kalender-Abonnements laufen weiterhin über Export-Tokens (ICS, kein Web-Login nötig). |

---

## 6. Offene Fragen

::: danger Klärungsbedarf
Die folgenden Fragen müssen noch vor der Implementierung geklärt werden.
:::

### Frage 6: Datenschutz bei internen Export-Tokens

Ein `INTERNAL`-Token zeigt vollständige Dienstleiter-Namen. Wer darf solche Tokens erstellen? Soll es eine Einschränkung auf `district_admin` geben, oder reicht `congregation_admin` für die eigene Gemeinde?

*Status: Noch offen.*
