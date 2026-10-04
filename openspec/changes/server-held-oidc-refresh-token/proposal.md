## Why

RC-1 persistiert den vollstaendigen OIDC-Tokenzustand inklusive Provider-Refresh-Token in JavaScript-zugaenglichem Browser-Speicher. Eine Same-Origin-XSS koennte damit eine langlebige Credential uebernehmen.

## What Changes

- Der Provider-Refresh-Token wird beim Authorization-Code-Exchange aus der JSON-Antwort entfernt und in einem Secure/HttpOnly/SameSite-Cookie gespeichert.
- Refresh-Requests senden nur den Grant-Typ; der Backend-Proxy liest die echte Credential ausschliesslich aus dem Cookie.
- Die SPA erhaelt mit `refresh_session: true` nur Metadaten darueber, dass eine serverseitige Refresh-Session existiert, aber keinen Refresh-Token oder Pseudo-Credential.
- Rotierte Refresh-Tokens ersetzen das Cookie serverseitig und werden nie an Frontend-JavaScript ausgegeben.
- Nach einem Reload kann die SPA ihren in-memory Access-Token ueber die serverseitige Refresh-Session wiederherstellen.
- Logout widerruft die serverseitig gehaltene Credential best-effort beim Provider, protokolliert Provider-Fehler und loescht das Cookie immer lokal.
- Der Pinia-Auth-State wird nicht mehr persistent gespeichert.
- Refresh-Koordination zwischen Tabs erfolgt nur fluechtig ueber Web Locks und BroadcastChannel; es werden keine Refresh-Receipts in Browser-Storage persistiert.
- `sessionStorage` bleibt auf den kurzlebigen PKCE-Verifier und den OAuth-State waehrend des Login-Flows begrenzt.
- Token-, Refresh-, Restore- und Revoke-POSTs senden den aktuellen Double-Submit-CSRF-Header.

## Capabilities

### Modified Capabilities
- `oidc-authentication`: Refresh-Credentials werden vom Backend kontrolliert und sind fuer JavaScript nicht lesbar; die SPA arbeitet nur mit kurzlebigen Access-/ID-Tokens im Speicher und fluechtiger Cross-Tab-Koordination.
- `csrf-protection`: Cookie-basierte Token-/Refresh-/Restore-/Logout-Operationen bleiben durch den aktuellen CSRF-Cookie plus Request-Header geschuetzt.

## Impact

- Ein kompletter Seiten-Reload kann die Browser-Session aus dem HttpOnly-Refresh-Cookie wiederherstellen, ohne langlebige Credentials in JavaScript-Speicher zu legen.
- Der Provider-Refresh-Token verlaesst nach dem initialen Provider-Response den Backend-Kontext nicht mehr.
- Die bisherige Receipt-/Rotationskettenlogik im Browser entfaellt, weil der Browser die rotierende Provider-Credential nicht mehr besitzt.
