## Why

RC-1 persistiert den vollstaendigen OIDC-Tokenzustand inklusive Provider-Refresh-Token in JavaScript-zugaenglichem Browser-Speicher. Eine Same-Origin-XSS koennte damit eine langlebige Credential uebernehmen.

## What Changes

- Der Provider-Refresh-Token wird beim Authorization-Code-Exchange aus der JSON-Antwort entfernt und in einem HttpOnly-Cookie gespeichert.
- Refresh-Requests senden nur den Grant-Typ; der Backend-Proxy liest die echte Credential ausschliesslich aus dem Cookie.
- Die SPA erhaelt mit `refresh_session: true` nur Metadaten darueber, dass eine serverseitige Refresh-Session existiert, aber keinen Refresh-Token oder Pseudo-Credential.
- Rotierte Refresh-Tokens ersetzen das Cookie serverseitig und werden nie an Frontend-JavaScript ausgegeben.
- Nach einem Reload kann die SPA ihren in-memory Access-Token ueber die serverseitige Refresh-Session wiederherstellen.
- Logout widerruft die serverseitig gehaltene Credential best-effort beim Provider, protokolliert Provider-Fehler und loescht das Cookie immer lokal.
- Der Pinia-Auth-State wird nicht mehr persistent gespeichert.
- Kurzlebige Refresh-Koordinationsreceipts werden nur tabgebunden in `sessionStorage` gehalten und enthalten keine Provider-Credential.
- Token- und Revoke-POSTs bleiben durch CSRF geschuetzt.

## Capabilities

### Modified Capabilities
- `oidc-authentication`: Refresh-Credentials werden vom Backend kontrolliert und sind fuer JavaScript nicht lesbar; die SPA arbeitet nur mit kurzlebigen Access-/ID-Tokens im Speicher.
- `csrf-protection`: Cookie-basierte Refresh- und Logout-Operationen sind CSRF-geschuetzt.

## Impact

- Ein kompletter Seiten-Reload kann die Browser-Session aus dem HttpOnly-Refresh-Cookie wiederherstellen, ohne langlebige Credentials in JavaScript-Speicher zu legen.
- Der Provider-Refresh-Token verlaesst nach dem initialen Provider-Response den Backend-Kontext nicht mehr.
