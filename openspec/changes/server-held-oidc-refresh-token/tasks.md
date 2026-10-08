## 1. Backend

- [x] 1.1 Provider-Refresh-Token aus Token-JSON entfernen und als HttpOnly-Cookie setzen.
- [x] 1.2 Refresh-Grant ausschliesslich aus Cookie bedienen; Body enthaelt nur den Grant-Typ.
- [x] 1.3 Refresh-Rotation serverseitig in Cookie uebernehmen.
- [x] 1.4 Revoke-Endpunkt fuer serverseitig gehaltene Credential ergaenzen und Provider-Fehler sichtbar loggen.
- [x] 1.5 Token- und Revoke-POSTs durch CSRF schuetzen.
- [x] 1.6 Erfolgreiche, aber ungueltige Provider-JSON-Antworten als 502 behandeln.

## 2. Frontend

- [x] 2.1 Pinia Auth-State nicht mehr in localStorage persistieren.
- [x] 2.2 Server-held Refresh-Session nur als nicht sensitive Metadaten modellieren.
- [x] 2.3 Refresh-Koordination ausschliesslich fluechtig ueber Web Locks und BroadcastChannel halten; keine Refresh-Receipts persistieren.
- [x] 2.4 Memory-only Session nach Reload aus HttpOnly-Refresh-Session wiederherstellen.
- [x] 2.5 Logout ohne Browser-Refresh-Credential ueber Cookie-Revoke ausfuehren.
- [x] 2.6 Token-, Refresh-, Restore- und Revoke-POSTs mit dem aktuellen CSRF-Cookie im Request-Header senden.
- [x] 2.7 Geschuetzte Navigation wartet auf einen deduplizierten Session-Restore und laedt danach Rollen-/Scope-Fakten.
- [x] 2.8 Restore bootstrapt Discovery/CSRF vor dem cookie-basierten POST und faellt bei Bootstrap-Fehlern geschlossen aus.

## 3. Tests

- [x] 3.1 Authorization-Code-Exchange gibt echten Refresh-Token nicht aus.
- [x] 3.2 Refresh nutzt Cookie statt Body-Credential.
- [x] 3.3 Fehlender Refresh-Cookie wird mit 401 abgewiesen.
- [x] 3.4 Provider ohne Rotation behaelt die serverseitige Refresh-Session.
- [x] 3.5 Logout/Revoke verwendet Cookie, loggt Provider-Fehler und loescht ihn lokal.
- [x] 3.6 Frontend-Refresh schreibt weder Credentials noch Receipts in localStorage/sessionStorage.
- [x] 3.7 Reload-Restore installiert nur vollstaendige, validierte Memory-Sessions.
- [x] 3.8 Ungueltige Provider-JSON-Antwort wird mit 502 abgewiesen.
- [x] 3.9 Cross-Tab-Races, stale Sessions, fehlende Web Locks und Rate-Limit-Ausnahmefaelle sind abgedeckt.
- [x] 3.10 CSRF-Header werden aus dem aktuellen Cookie gelesen und fuer direkte OIDC-POSTs verwendet.
- [x] 3.11 Discovery-/CSRF-Bootstrap und deduplizierter Restore sind als Unit-Tests abgedeckt.
- [x] 3.12 E2E-Auth-Fixtures verwenden den produktiven HttpOnly-Restore-Vertrag statt persistierter Auth-Credentials.
- [x] 3.13 Direkte Reloads geschuetzter Routen werden durch die Restore-basierten E2E-Flows abgedeckt.
- [x] 3.14 Backend akzeptiert CSRF-Token nur aus dem Header; Cookie-Fallback entfernt, Regressionstests ueber HTTPS-Testclient (#458).

## 4. Verifikation

- [x] 4.1 Backend Tests und Coverage >80 % erfolgreich.
- [x] 4.2 Frontend Unit/E2E Tests und Coverage >80 % erfolgreich.
- [x] 4.3 CodeQL und Dependency Audits erfolgreich.
