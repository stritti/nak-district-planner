# Authentifizierung & Autorisierung mit Keycloak

Der NAK District Planner verwendet **Keycloak** für ein sicheres und zentralisiertes Identitäts- und Zugriffsmanagement (IAM).

## Überblick

Die Anwendung ist so konzipiert, dass sie mehrere Bezirke (Mandanten) unterstützt, die strikt voneinander getrennt sind. Die Authentifizierung erfolgt über das OpenID Connect (OIDC) Protokoll.

## Rollenkonzept

Es werden drei Hauptebenen der Berechtigung unterschieden:

1.  **Administrator (`admin`)**:
    *   Vollzugriff auf das gesamte System.
    *   Kann Bezirke anlegen und verwalten.
2.  **Bezirks-Administrator (`district-admin`)**:
    *   Verwaltet einen spezifischen Bezirk.
    *   Kann Gemeinden innerhalb des Bezirks anlegen.
    *   Kann alle Termine des Bezirks (einschließlich aller Gemeinden) sehen und bearbeiten.
3.  **Gemeinde-Editor (`congregation-editor`)**:
    *   Zugeordnet zu einer oder mehreren Gemeinden.
    *   Darf die Termine seiner zugeordneten Gemeinden bearbeiten.
    *   Darf Termine auf Bezirksebene (ohne Gemeinde-Zuordnung) desselben Bezirks sehen, aber nicht bearbeiten.

## Daten-Isolation (Multi-Tenancy)

Die Bezirke sind logisch komplett voneinander getrennt:
*   Ein Benutzer sieht nur die Daten (Bezirke, Gemeinden, Termine), für die er explizit berechtigt wurde.
*   Anfragen im Backend werden automatisch auf die erlaubten `district_id`s gefiltert.

## Gruppen-Struktur in Keycloak

Die Berechtigungen werden über eine hierarchische Gruppenstruktur in Keycloak abgebildet:

*   `/Bezirke/{District-ID}/Admins`
*   `/Bezirke/{District-ID}/Gemeinden/{Congregation-ID}/Editoren`

## Sichtbarkeiten

Innerhalb eines Bezirks gelten folgende Sichtbarkeitsregeln:

*   **Abwärts-Sichtbarkeit**: Ein Bezirks-Admin sieht alles in seinem Bezirk.
*   **Aufwärts-Sichtbarkeit**: Ein Gemeinde-Editor sieht zusätzlich zu seinen eigenen Terminen auch die allgemeinen Termine auf Bezirksebene (z.B. Bezirks-Gottesdienste), um Überschneidungen zu vermeiden.
*   **Horizontale Isolation**: Gemeinde-Editoren sehen standardmäßig keine Termine von *anderen* Gemeinden desselben Bezirks, es sei denn, dies wird über die Sichtbarkeitseinstellungen (öffentlich vs. intern) anders konfiguriert.

## Technischer Ablauf

1.  **Login**: Der Benutzer wird zum Keycloak-Login weitergeleitet.
2.  **JWT-Token**: Nach erfolgreichem Login erhält die Frontend-App ein JSON Web Token (JWT).
3.  **API-Anfragen**: Das JWT wird bei jeder Anfrage im `Authorization: Bearer <Token>` Header mitgesendet.
4.  **Validierung**: Das Backend validiert die Signatur des Tokens und prüft die enthaltenen Claims (Rollen/Gruppen) für die Autorisierung.
