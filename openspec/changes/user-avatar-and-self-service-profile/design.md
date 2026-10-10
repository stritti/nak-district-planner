## Context

- `services/frontend/src/components/AppNav.vue` rendert derzeit Name/E-Mail und ein Dropdown mit alleiniger Aktion „Abmelden“, mobil ein `UserIcon`.
- `services/frontend/src/composables/oidcTypes.ts` stellt im Browser `sub`, `name`, `email` und optional `picture` bereit, aber keine getrennten `given_name`/`family_name`-Felder.
- `GET /api/v1/auth/me` liefert bereits `given_name`, `family_name`, `name`, `email`, `username` und `is_superadmin`.
- `SqlUserRepository.save` aktualisiert `users.name`, `users.given_name` und `users.family_name` aus IdP-Daten. Die `users`-Tabelle und ihr `is_superadmin`-Flag haben sicherheitsrelevante, getrennte Verantwortlichkeiten.
- Die Anmeldung ist OIDC-providerunabhängig; Keycloak ist eine mögliche Konfiguration, keine fest verdrahtete Abhängigkeit.

## Goals / Non-Goals

**Goals:** Kompakte Navigation; Initialen ohne Bilder; eigene lokale Namensdaten pflegen; barrierefreie Tastaturbedienung; wirksame Trennung von Darstellung, IdP-Identität und Berechtigungen; Betrieb auch vor der Benutzerfreigabe.

**Non-Goals:** Eigenes Identity-Management, E-Mail-/Passwortänderung innerhalb der SPA, persistente Bilddaten, administrative Profilbearbeitung, Synchronisierung in Richtung IdP.

## Decisions

### 1. Avatar und Dropdown

- Ersetze den langen sichtbaren Benutzerblock rechts durch einen runden Avatar (visuell ca. 36–40 px; fokussierbare Schaltfläche mindestens 44 × 44 px). Das Dropdown behält den bisherigen Benutzerkopf mit Anzeigename und E-Mail.
- Initialen werden aus den **effektiven**, aus dem Profil-Endpoint geladenen Vor-/Nachnamen gebildet. Verwende Unicode-Grapheme und Locale-fähige Großschreibung; entferne führende/abschließende Leerzeichen. Wenn nur ein Teil vorhanden ist, ein Initial; ohne getrennte Felder darf der OIDC-`name` als reiner Anzeige-Fallback dienen (ohne unsichere Annahme, welcher Teil ein Nachname ist). Bei vollständig fehlendem Namen neutrales Benutzer-Symbol.
- Weder `OIDCUser.picture` noch Remote-URLs, Uploads oder Gravatar werden verarbeitet. Feste, kontrastreiche Theme-Farben statt personenbezogener Avatar-Generierung.
- Der Auslöser hat einen verständlichen zugänglichen Namen (z. B. „Benutzermenü für … öffnen“), `aria-expanded` und sichtbaren Fokus. Escape, Klick außerhalb, Logout, Navigation und Benutzerwechsel schließen das Popup; der Tastaturfokus kehrt sinnvoll zum Auslöser zurück. Mobil, Desktop, helles und dunkles Theme nutzen dieselbe Komponente.
- Dropdown-Aktionen: „Mein Profil“ (`/account`), optional „Anmeldekonto verwalten“ (siehe unten), „Abmelden“. Die bestehende Logout-Logik bleibt unverändert.

### 2. Datenhoheit und Lesevertrag

Die IdP-Claims bzw. der bisherige `users`-Datensatz bleiben Quelle für `sub`, E-Mail, Benutzername, E-Mail-Verifikation und Anmeldung. Sie sind **keine** anwendungsintern bearbeitbaren Felder.

Neue separate Tabelle `user_profile_overrides` mit eindeutigem `user_sub` (FK auf `users.sub`), `given_name_override` und `family_name_override` (jeweils nullable) sowie `updated_at`. Die bestehende Benutzer-Stammdatentabelle wird weder umgedeutet noch zur lokalen Namensspeicherung verwendet.

`GET /api/v1/profile/me` (für jeden authentifizierten OIDC-Subject, auch vor Freigabe) antwortet ausschließlich mit dem **eigenen** Profil:
```json
{
  "given_name": "Max",
  "family_name": "Beispiel",
  "name": "Max Beispiel",
  "email": "max@example.invalid",
  "username": "max",
  "given_name_override": null,
  "family_name_override": null
}
```
`given_name`/`family_name` sind die effektiven Werte: vorhandene lokale Überschreibung, sonst aktueller IdP-Wert. `name` ist ein für die Darstellung abgeleiteter Wert mit IdP-`name` als Fallback, wenn getrennte Namen fehlen. Fehlende Provider-Werte können `null` sein; nur `email`/`username` folgen ihrem bestehenden Backend-Vertrag. Die Override-Felder zeigen den editierbaren Zustand (nicht sensible Credential-Claims). Keine Autorisierungsentscheidungen nutzen diese Anzeige-Felder.

### 3. Schreiben und Zurücksetzen

`PUT /api/v1/profile/me` erwartet **beide** Felder `given_name_override` und `family_name_override` als `string | null`, erlaubt ausschließlich diese Felder und liefert den aktualisierten GET-Vertrag zurück. `null` bedeutet **Override löschen und IdP-Wert übernehmen**. Eine leere bzw. ausschließlich aus Whitespace bestehende Zeichenfolge wird abgewiesen. Zulässig sind nach Trim 1–100 Unicode-Zeichen je Überschreibung; Kontrollzeichen, überlange Werte und falsche Datentypen führen zu `422`. Ausgabe wird als Text gerendert, nie als HTML interpretiert. Die Speicherung ist atomar.

Der Subject kommt **nur** aus der validierten aktuellen Authentifizierung und wird nicht aus Body, Query oder URL akzeptiert. Es gibt keine generische `PUT /users/{sub}`-Schnittstelle. Nicht angemeldet: `401`. RLS (`app.current_user_sub`) beschränkt `SELECT/INSERT/UPDATE/DELETE` auf das eigene Profil, mit schreibgeschütztem `user_sub` und `WITH CHECK` für neue Zeilen. Privilegien/FK werden so umgesetzt, dass die bestehende Freigabe von `users` nicht geändert wird. Existiert für einen authentifizierten Subject noch keine Benutzerzeile, wird der vorhandene kontrollierte OIDC-Benutzerabgleich verwendet; es gibt keinen clientgesteuerten Benutzer-Provisioning-Pfad.

Backend-Fehler bewirken keine optimistische dauerhafte UI-Anzeige. Während einer Anfrage ist Speichern gesperrt; bei `401` greifen die bestehenden Session-Regeln, bei `403` kein Berechtigungs-Bypass, bei `422` erscheint Feldfeedback, bei Serverfehlern ein Fehlerzustand. Erneuter Abruf nach Reload bestätigt gespeicherte Werte.

### 4. Identity-Provider-Kontoverwaltung

E-Mail, Benutzername und Passwort sind lokal **schreibgeschützt**. Ein optionaler, vom Betreiber geprüfter, absoluter `https`-Link auf das Self-Service-Konto des konfigurierten OIDC-Providers darf im Dropdown/Profil erscheinen. Er wird nicht aus Token-Claims oder Nutzereingaben konstruiert; für lokale Entwicklungsumgebungen kann ausdrücklich eine `http://localhost`-Ausnahme gelten. Nicht konfiguriert: Link **ausblenden**, niemals eine Keycloak-URL erraten. Externe Navigation öffnet ohne Zugangstoken in der URL und mit `rel="noopener noreferrer"`.

Ein dort geänderter Name wird bei erneuter Anmeldung über IdP-Claims sichtbar, **sofern** kein lokaler Override gesetzt ist. Lokale Änderungen lösen weder einen Keycloak-Admin-API-Aufruf noch eine Token-Änderung aus. Nur der echte OIDC-Subject darf Freigaben/Mitgliedschaften bestimmen.

### 5. Identitätswechsel und Betriebsqualität

- Profil-Caches werden anhand des Subjects getrennt und beim Logout/Identitätswechsel verworfen. Antworten von vorigen Sessions dürfen keine Oberfläche der nächsten Session aktualisieren.
- `PENDING_APPROVAL` darf das eigene Profil sehen und ändern; keine geschützte fachliche Ressource wird dadurch freigeschaltet.
- Profileinträge werden nicht in LocalStorage persistiert. Auf fehlgeschlagenen GET folgt ein sicherer OIDC-Anzeige-Fallback und sichtbarer Lade-/Fehlerzustand, nie Daten eines anderen Benutzers.
- Personenbezogene Namen/E-Mail dürfen nicht unnötig in Audit-Details, Log-Statements oder Fehlertexte gelangen. Server kann Änderung mit Subject, Zeitpunkt und Aktion auditieren, ohne Werte zu protokollieren.

## Alternatives Considered

- **Direkt `users.given_name`/`family_name` ändern:** verworfen, weil der IdP-Sync sie beim nächsten Login überschreibt und dieselbe Tabelle globale Zugriffsflags enthält.
- **Direkt Keycloak aktualisieren:** verworfen wegen Kopplung an einen Provider, benötigter privilegierter Credentials und verändertem Identitätsvertrauen.
- **Nur Link zur Keycloak Account Console:** erlaubt keine anwendungsinterne Anzeigepräferenz und funktioniert nicht für jeden OIDC-Provider.

## Rollout / Verification

1. Migration mit enger RLS und kontrollierten DML-Rechten für neues Profil-Aggregat.
2. Profile-Repository, Service, GET/PUT-Self-Service-API (kein Admin-Endpunkt).
3. Frontend-Profil-Store, Profilansicht, Initialen-Komponente, Dropdown-Verknüpfung.
4. Unit- und RLS-Integrationstests inklusive Cross-User-Versuchen, ungültigen Werten, unvollständigen IdP-Claims, konkurrierenden Anfragen, Fallback und Sessionwechsel.
5. E2E: Desktop/Mobil, Tastatur/Screenreader-Semantik, Pending-User, Änderung und Reload, Rücksetzung und erneute Anmeldung.
6. Vollständige Checks (OpenSpec, Lint, Build, Backend/Frontend-Tests, per-file Coverage >80 %, RLS, E2E). Bis alle Gates grün sind, ist eine spätere Implementierung nicht merge-ready.
