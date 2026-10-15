## Context

Der Pinia-Store `districts` verwaltet bereits `selectedDistrictId` und speichert die Auswahl tabbezogen unter dem Navigationskontext. Matrix und Eventliste beobachten diesen Wert und laden bei Änderungen Daten nach. Im Backend begrenzt `GET /api/v1/districts` die Liste auf autorisierte Bezirke; Superadmins erhalten alle.

## Goals / Non-Goals

**Goals**
- Bezirk nur einmal und auf allen geschützten Ansichten an zentraler Stelle anzeigen.
- Umschaltung ausschließlich bei mehr als einem tatsächlich zugänglichen Bezirk anbieten.
- Bei einem Bezirk immer den Namen ohne unnötiges Auswahlfeld zeigen.
- Keine veralteten tenantbezogenen Namen oder Auswahlwerte nach Logout/Benutzerwechsel.
- Keine Änderung der Bezirkszugriffskontrolle und der per-View-Filtersemantik.

**Non-Goals**
- Kein dauerhafter, serverseitiger Standardbezirk im Benutzerprofil.
- Keine Änderung der API, Rollen, Registrierung oder Datenmodellierung.
- Andere administrative, fachlich ausdrücklich mehrbezirkliche Filter werden nicht umgestaltet.

## Decisions

### Navigationskopf statt Untermenü

Die `DistrictContextSwitcher`-Komponente erscheint in der ersten Navigationszeile. Der gewählte Name bleibt dort sichtbar; bei `districts.length > 1` wird ein beschriftetes natives Select benutzt. Ein nur im Benutzermenü befindlicher Wechsel wäre auf der Arbeitsoberfläche schwerer als Mandantenkontext erkennbar. Das Select steht auch in mobilen Layouts zur Verfügung.

### Berechtigungen aus API statt Rolle ableiten

Umschaltbarkeit wird anhand der Anzahl tatsächlich ausgelieferter Bezirke berechnet, nicht anhand von `isSuperadmin`. Dadurch können auch Benutzer mit Berechtigungen in zwei Bezirken wechseln und Superadmins mit nur einem verfügbaren Bezirk sehen kein sinnloses Auswahlfeld.

### Eine Quelle für die gewählte Bezirks-ID

Die globale Navigation schreibt ausschließlich über `districts.setSelectedDistrict`; die Store-Auswahl wird gegen die geladene Bezirksliste geprüft. Matrix und Eventliste greifen weiterhin lesend auf `selectedDistrictId` zu; ihre bestehenden Watcher aktualisieren ihre Daten und Filter. Die View-Einstellungen bleiben im `useSessionViewSettings` nach Bezirkskontext isoliert.

### Fehler-, Widerrufs- und Identitätswechsel

Beim Nachladen wird die gespeicherte Auswahl gegen die freigegebene Liste geprüft. API-Fehler leeren die zugängliche Liste und die Auswahl, statt veraltete Mandanten weiterhin anzuzeigen. Bei Logout oder Identitätswechsel werden die Caches geleert und ausstehende Antworten durch einen Versionszähler verworfen. Backend-Permissions bleiben autoritativ.

## Risks / Trade-offs

- Parallel anlaufende Abrufe durch Navigation und Views: Der Store verwirft ältere Resultate; Views bekommen weiterhin ihren bestehenden Ladepfad.
- Wechsel während laufender Datenabrufe: bestehende View-Watcher prüfen die aktuelle Bezirks-ID. Darstellungs- und Query-Regressionen werden durch Unit- und E2E-Tests abgesichert.
- Bei Verbindungsfehlern erscheint vorübergehend kein Bezirksname: sicherer als eine ungesicherte, möglicherweise widerrufene Auswahl. Nach erneutem Laden wird der Kontext aufgelöst.

## Migration Plan

1. Neue globale Komponente einbauen; vorliegende bezirksbezogene Session-Einstellungen erhalten.
2. Redundante Selects aus Matrix und Eventliste entfernen.
3. Berechtigungs-, Identitätswechsel-, Fehler- und Wechseltests ergänzen.
4. CI und E2E prüfen; keine Datenmigration erforderlich.
