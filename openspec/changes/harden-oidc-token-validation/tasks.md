## 1. Implementierung

- [x] 1.1 JWT-artige Tokens ohne Fallback validieren.
- [x] 1.2 Opaque Tokens ueber UserInfo/Introspection validieren.
- [x] 1.3 Vorhandene Issuer-, Client- und Audience-Claims bei opaque Tokens pruefen.
- [x] 1.4 Default-Algorithmen auf RS256 begrenzen.
- [x] 1.5 Erkannte Claim-Mismatches terminal behandeln und nicht ueber Fallback umgehen.
- [x] 1.6 Vorhandenes `aud` als Resource-Audience erzwingen; `azp` darf ein falsches `aud` nicht ersetzen.

## 2. Tests

- [x] 2.1 Regressionstest: falsche JWT-Audience darf keinen Fallback ausloesen.
- [x] 2.2 Regressionstest: opaque UserInfo mit falschem Issuer wird terminal abgewiesen.
- [x] 2.3 Regressionstest: Introspection mit falschem Client/Audience wird abgewiesen.
- [x] 2.4 Erfolgsfall fuer opaque UserInfo sichern.
- [x] 2.5 Regressionstest: falsches `aud` wird auch bei passendem `azp` abgewiesen.

## 3. Verifikation

- [ ] 3.1 Backend Unit Tests und Coverage in CI erfolgreich.
- [ ] 3.2 CodeQL und Dependency Audits erfolgreich.
