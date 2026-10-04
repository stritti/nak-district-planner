## Why

RC-1 persistiert den vollstaendigen OIDC-Tokenzustand inklusive Provider-Refresh-Token in JavaScript-zugaenglichem Browser-Speicher. Eine Same-Origin-XSS koennte damit eine langlebige Credential uebernehmen.

## What Changes

- Der Provider-Refresh-Token wird beim Authorization-Code-Exchange aus der JSON-Antwort entfernt und in einem HttpOnly-Cookie gespeichert.
- Refresh-Requests senden nur einen nicht sensitiven Koordinationsmarker; der Backend-Proxy liest die echte Credential aus dem Cookie.
- Rotierte Refresh-Tokens ersetzen das Cookie serverseitig und werden nie an Frontend-JavaScript ausgegeben.
- Logout widerruft die serverseitig gehaltene Credential best-effort beim Provider und loescht das Cookie immer lokal.
- Der Pinia-Auth-State wird nicht mehr persistent gespeichert.
- Kurzlebige Refresh-Koordinationsreceipts werden nur tabgebunden in `sessionStorage` gehalten.
- Token- und Revoke-POSTs bleiben durch CSRF geschuetzt.

## Capabilities

### Modified Capabilities
- `oidc-authentication`: Refresh-Credentials werden vom Backend kontrolliert und sind fuer JavaScript nicht lesbar.
- `csrf-protection`: Cookie-basierte Refresh- und Logout-Operationen sind CSRF-geschuetzt.

## Impact

- Nach einem kompletten Seiten-Reload ist der in-memory Access Token weg; ein erneuter interaktiver Login kann erforderlich sein, solange kein separater Session-Restore-Endpunkt existiert.
- Der Provider-Refresh-Token verlaesst nach dem initialen Provider-Response den Backend-Kontext nicht mehr.