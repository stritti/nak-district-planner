## 1. Backend

- [x] 1.1 Provider-Refresh-Token aus Token-JSON entfernen und als HttpOnly-Cookie setzen.
- [x] 1.2 Refresh-Grant aus Cookie bedienen; Body enthaelt nur Koordinationsmarker.
- [x] 1.3 Refresh-Rotation serverseitig in Cookie uebernehmen.
- [x] 1.4 Revoke-Endpunkt fuer serverseitig gehaltene Credential ergaenzen.
- [x] 1.5 Token- und Revoke-POSTs durch CSRF schuetzen.

## 2. Frontend

- [x] 2.1 Pinia Auth-State nicht mehr in localStorage persistieren.
- [x] 2.2 Refresh-Koordination mit nicht sensitivem Marker beibehalten.
- [x] 2.3 Credential-bearing Receipts von localStorage auf sessionStorage umstellen.

## 3. Tests

- [x] 3.1 Authorization-Code-Exchange gibt echten Refresh-Token nicht aus.
- [x] 3.2 Refresh nutzt Cookie statt Body-Credential.
- [x] 3.3 Fehlender Refresh-Cookie wird mit 401 abgewiesen.
- [x] 3.4 Provider ohne Rotation behält Koordinationsmarker.
- [x] 3.5 Logout/Revoke verwendet Cookie und loescht ihn.
- [x] 3.6 Frontend-Receipts schreiben keine Credentials in localStorage.

## 4. Verifikation

- [ ] 4.1 Backend Tests und Coverage >80 % erfolgreich.
- [ ] 4.2 Frontend Unit/E2E Tests und Coverage >80 % erfolgreich.
- [ ] 4.3 CodeQL und Dependency Audits erfolgreich.