## Why

Der RC-1 validiert JWTs zunaechst korrekt, faellt nach jedem Validierungsfehler jedoch auf UserInfo und Introspection zurueck. Dadurch kann ein Token, das als JWT wegen falscher Audience, falschem Issuer, Ablauf oder Signaturfehler abgewiesen wurde, ueber einen anderen Provider-Endpunkt erneut akzeptiert werden.

## What Changes

- JWT-artige Access Tokens werden ausschliesslich als JWT validiert und schlagen bei jedem Validierungsfehler fehl.
- Nur opaque Access Tokens duerfen UserInfo und Introspection verwenden.
- Security-relevante Claims aus opaque Token-Validierung werden gegen Issuer, Client und Audience geprueft, sofern der Provider sie liefert.
- Der Default fuer JWT-Signaturalgorithmen wird auf `RS256` begrenzt.
- Regressionstests sichern die fail-closed Semantik ab.

## Capabilities

### Modified Capabilities
- `oidc-authentication`: Strikte Trennung zwischen JWT- und opaque-Token-Validierung.

## Impact

- Backend: `OIDCAdapter` und Auth-Tests.
- Security: Kein Rehabilitieren eines bereits abgewiesenen JWTs ueber UserInfo/Introspection.
- Kompatibilitaet: Opaque Tokens bleiben unterstuetzt; alternative JWT-Algorithmen muessen explizit konfiguriert werden.
