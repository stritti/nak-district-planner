## Context

Die Anwendung bietet bislang keine systematische, kontextuelle Hilfe direkt in den Arbeitsablaeufen. Dadurch muessen neue Nutzer Wissen extern suchen oder durch Trial-and-Error aufbauen. Gleichzeitig sollen erfahrene Nutzer nicht durch dauerhafte Hinweise gestoert werden. Das Projekt nutzt Vue 3 + Pinia im Frontend und rollenbasierte Sichtbarkeit (u. a. `viewer`, `planner`) als zentrales Nutzungsmuster. Die Hilfe muss deshalb rollenabhaengig, kontextnah und lokal steuerbar sein.

## Goals / Non-Goals

**Goals:**
- Rollenabhaengige Hilfeinhalte fuer Gast (nicht angemeldet), `viewer` und `planner` bereitstellen.
- Hilfe in den relevanten Views sichtbar machen, ohne primaere Aufgaben zu blockieren.
- Pro Hilfe-Modul ein Ausblenden/Einblenden ermoeglichen und den Zustand nutzerbezogen persistieren.
- Einheitliche Inhaltsstruktur etablieren, damit Hilfetexte konsistent gepflegt werden koennen.

**Non-Goals:**
- Kein vollwertiges Help-Center mit globaler Suche, Artikeldatenbank oder Ticketing.
- Keine serverseitige CMS-Redaktion in dieser Aenderung.
- Keine Rollen-/Rechte-Neudefinition; bestehende Rollen werden genutzt.

## Decisions

- **UI-Pattern: Kontextuelle Help Panels statt modaler Overlays.**
  - Entscheidung: Hilfe wird als kompakte, einklappbare Panel-/Callout-Komponente in den jeweiligen Views angezeigt.
  - Warum: Unaufdringlich, dauerhaft verfuegbar, geringer Kontextwechsel.
  - Alternative: Modale Onboarding-Dialoge. Verworfen, weil sie Arbeitsfluss unterbrechen und bei wiederholter Nutzung stoeren.

- **Rollen- und Kontextauflosung im Frontend mit klarer Prioritaet.**
  - Entscheidung: Sichtbare Hilfe wird aus (1) Auth-Status, (2) Rolle, (3) aktueller View/Workflow-Kontext bestimmt.
  - Warum: Existierende Session-/Store-Daten sind ausreichend; reduziert Backend-Kopplung fuer MVP.
  - Alternative: Vollstaendig serverseitige Inhaltsauslieferung pro Request. Verworfen, weil fuer initiale Einfuehrung unnnoetig komplex.

- **Inhalte als strukturierte Konfiguration mit stabilen IDs.**
  - Entscheidung: Hilfebloecke werden als strukturierte Inhalte (Titel, Kurztext, Schritte, Links, Rollen, Kontexte) mit eindeutiger `help_id` abgelegt.
  - Warum: Erleichtert Wiederverwendung, Tests, spaetere Internationalisierung und gezieltes Tracking der Sichtbarkeit.
  - Alternative: Freitext direkt in Komponenten. Verworfen, da schwer wartbar und schlecht testbar.

- **Persistenz fuer Ausblendestatus pro Nutzer und Hilfe-ID.**
  - Entscheidung: Ausblenden wird fuer angemeldete Nutzer persistent gespeichert (z. B. im Nutzerprofil/Preferences-Store); fuer Gaeste lokal im Browser.
  - Warum: Erwartbares Verhalten ueber Sessions hinweg.
  - Alternative: Rein fluechtiger Zustand. Verworfen, da Hinweise nach Reload wieder erscheinen und Friktion erzeugen.

- **Platzierungsstrategie: Hilfe am Point of Need.**
  - Entscheidung: Initiale Platzierungen in Registrierung/Login-Kontext (Gast), Event-Uebersicht (Viewer/Planner) und Matrix-Planungsansicht (Planner).
  - Warum: Deckt die vom Fachbereich genannten Kern-Workflows ab.
  - Alternative: Eine zentrale Hilfeseite. Verworfen, da geringer Kontextbezug.

## Risks / Trade-offs

- [Zu viele Hinweise fuehren zu visueller Ueberladung] -> Mitigation: Strikte Platzierungsregeln, kurze Texte, standardmaessig einklappbare Darstellungen.
- [Falsche Rollenzuordnung zeigt unpassende Hilfe] -> Mitigation: Zentrale Mapping-Funktion mit Tests fuer Rolle+Kontext.
- [Persistenzinkonsistenz zwischen Gast und angemeldet] -> Mitigation: Einheitliches Datenmodell fuer Hidden-State; Adapter fuer localStorage vs. Nutzer-Preferences.
- [Inhalte altern schnell] -> Mitigation: Klare Inhaltsverantwortung und Review bei Workflow-Aenderungen.
- [Mehr Frontend-Komplexitaet] -> Mitigation: Wiederverwendbare Basiskomponente statt View-spezifischer Einzelimplementierungen.

## Migration Plan

1. Basiskomponente und Inhaltsschema einfuehren.
2. Rollen-/Kontextauflosung sowie Hidden-State-Store implementieren.
3. Hilfe in priorisierten Views integrieren (Gast-Onboarding, Eventliste, Matrix-Planung).
4. Rollen- und Sichtbarkeitsszenarien testen (Guest/Viewer/Planner).
5. Rollout ohne Downtime; bei Problemen Help-Rendering ueber Feature-Flag deaktivieren (Fallback: bestehende Views ohne Hilfe).

## Open Questions

- Sollen Hilfebloecke initial als standardmaessig sichtbar oder teilweise eingeklappt ausgeliefert werden?
- Welche tieferen Links (z. B. zu Dokumentation) stehen fuer Viewer/Planner verbindlich zur Verfuegung?
- Wird spaeter eine redaktionelle Pflege ueber Backend/API benoetigt (Roadmap), oder bleibt Konfigurationsdatei ausreichend?
