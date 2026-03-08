# Rollenkonzept

Diese Seite beschreibt das geplante Rollenkonzept für den NAK Bezirksplaner. Es dient als Grundlage für den Review und die spätere Implementierung (Phase 4).

::: warning Status: Entwurf
Dieses Dokument ist ein Review-Entwurf. Noch keine Implementierung vorhanden. Offene Fragen sind am Ende des Dokuments aufgeführt.
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
- Dienstmatrix des Bezirks **lesen**
- ServiceAssignments der eigenen Gemeinde lesen
- Export-Tokens für die eigene Gemeinde erstellen und löschen

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

### 2.6 Öffentlicher Zugang (ohne Login)

**Geltungsbereich:** Keine Authentifizierung – über Export-Token

**Beschreibung:** Nicht-eingeloggte Personen (z. B. Gemeindemitglieder) erhalten Zugang zu kalendarischen Daten über abonnierbare ICS-Links.

**Token-Typen (bereits implementiert, siehe UC-05):**
| Token-Typ | Sichtbarkeit | Dienstleiter-Namen |
|-----------|-------------|-------------------|
| `PUBLIC`  | Nur `visibility=PUBLIC` und `status=PUBLISHED` | Anonymisiert (z. B. "Dienstleiter") |
| `INTERNAL` | Inkl. `visibility=INTERNAL` | Vollständige Namen |

---

## 3. Berechtigungsmatrix

Die folgende Tabelle gibt einen Überblick über die Berechtigungen je Ressource und Rolle.

**Legende:** ✅ erlaubt · 🔒 nur eigene Ressourcen · 👁️ nur lesen · ❌ nicht erlaubt

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
| Dienstmatrix lesen                        | ✅  | ✅  | ✅  | ✅  | ✅  |
| Zuweisung erstellen / bearbeiten         | ✅  | ✅  | 🔒  | ✅  | ❌  |
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
| Rollen zuweisen (im Bezirk)              | ✅  | ✅  | ❌  | ❌  | ❌  |
| **Feiertags-Import**                      |     |     |     |     |     |
| Manueller Import                          | ✅  | ✅  | ❌  | ❌  | ❌  |

---

## 4. Technische Umsetzungshinweise (Vorschlag)

::: info Hinweis
Dieser Abschnitt beschreibt Vorschläge für die technische Umsetzung. Er wird im Zuge von Phase 4 ausgearbeitet.
:::

### 4.1 Datenbankmodell

```
User
  id, email, display_name, hashed_password, is_active, created_at

UserRole
  id, user_id (FK), role (enum), district_id (FK, nullable), congregation_id (FK, nullable)
```

- Ein Benutzer kann mehrere Einträge in `UserRole` haben (z. B. `district_admin` in Bezirk A und `viewer` in Bezirk B).
- `district_id` und `congregation_id` sind optional und definieren den Geltungsbereich.
- `system_admin` hat keinen Bezirk/Gemeinde-Bezug (beide `NULL`).

### 4.2 JWT-Token-Inhalt (Claim-Vorschlag)

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "roles": [
    { "role": "district_admin", "district_id": "uuid-bezirk-1" },
    { "role": "viewer", "district_id": "uuid-bezirk-2" }
  ],
  "exp": 1234567890
}
```

### 4.3 Middleware / Permission-Guard

Die Berechtigungsprüfung soll als FastAPI-Dependency (ähnlich dem bestehenden `verify_api_key`) implementiert werden:

```python
# Beispiel (Pseudocode)
async def require_role(
    required_role: Role,
    district_id: UUID | None = None,
) -> User:
    ...
```

---

## 5. Offene Fragen

::: danger Klärungsbedarf
Die folgenden Fragen müssen vor der Implementierung geklärt werden.
:::

### Frage 1: Rollenvererbung und Hierarchie
Soll die Rolle `district_admin` automatisch `congregation_admin`-Rechte für alle Gemeinden des Bezirks umfassen? Oder werden Berechtigungen strikt getrennt und müssen explizit vergeben werden?

### Frage 2: Mehrmandantenfähigkeit für Benutzer
Kann ein Benutzer gleichzeitig in mehreren Bezirken Rollen innehaben (z. B. Leiter in zwei Bezirken)? Wenn ja: Wie wird die Oberfläche damit umgehen (Kontextwechsel, gemeinsames Dashboard)?

### Frage 3: Gemeindegruppen (`CongregationGroup`)
Wird eine eigene Rolle für die Gemeindegruppen-Ebene benötigt (z. B. `group_admin`)? Oder verwaltet der `district_admin` die Gruppen komplett, und Gruppenverantwortliche agieren als `planner`?

### Frage 4: Einladungsworkflow
Wie sollen neue Benutzer in das System eingeladen werden? Optionen:
- a) E-Mail-Einladung mit temporärem Token durch `district_admin`
- b) Selbstregistrierung mit anschließender Freigabe durch Admin
- c) Manuelle Anlage ausschließlich durch `system_admin`

### Frage 5: Sichtbarkeit von ServiceAssignments
Soll ein `congregation_admin` die Dienstleiter-Namen anderer Gemeinden im gleichen Bezirk sehen können? Dies ist für die Matrixansicht relevant.

### Frage 6: Datenschutz bei internen Export-Tokens
Ein `INTERNAL`-Token zeigt vollständige Dienstleiter-Namen. Wer darf solche Tokens erstellen? Soll es eine Einschränkung auf `district_admin` geben, oder reicht `congregation_admin` für die eigene Gemeinde?

### Frage 7: Passwortlose Authentifizierung / SSO
Soll die Anwendung eine eigene Passwort-Authentifizierung implementieren, oder wird eine externe Lösung bevorzugt (z. B. OAuth2 via Google / Microsoft, SAML, Magic Link)? Gibt es ein vorhandenes Identity-System der NAK, das genutzt werden könnte?

### Frage 8: Session-Dauer und Token-Ablauf
Wie lange sollen JWT-Tokens bzw. Sitzungen gültig sein? Wird ein Refresh-Token-Mechanismus benötigt?

### Frage 9: Audit-Log
Sollen sicherheitsrelevante Aktionen (Rollenvergabe, Login, Datenlöschung) in einem Audit-Log festgehalten werden?

### Frage 10: Rollendelegation
Soll ein `district_admin` die Möglichkeit haben, einem `congregation_admin` das Recht zu geben, Benutzer für die eigene Gemeinde einzuladen (begrenzte Delegation)?

### Frage 11: Deaktivierung vs. Löschung von Benutzern
Was passiert mit den zugewiesenen Diensten (`ServiceAssignment.leader_name`), wenn ein Benutzer deaktiviert oder gelöscht wird? Werden die historischen Einträge behalten?

### Frage 12: Zugriff ohne Konto (Gast)
Soll es möglich sein, die Anwendung ohne Anmeldung eingeschränkt zu nutzen (z. B. öffentliche Veranstaltungsübersicht), oder ist immer ein Login erforderlich?
