## 1. Tests (red)

- [x] 1.1 Unit-Tests fuer `extract_user_info`: `email_verified` nur bei Boolean `true` und echtem `email`-Claim; Username-Fallback nie verifiziert
- [x] 1.2 Unit-Tests fuer `get_current_user_with_memberships`: kein Link bei `email_verified` false/fehlend; positiver Link-Test bleibt
- [x] 1.3 Unit-Tests fuer Keycloak-Provisioner: unverifiziertes bestehendes Konto (auch 409-Race) wird nicht gebunden

## 2. Implementierung

- [x] 2.1 `email_verified` in `extract_user_info` ableiten und als transientes Feld an `User` weitergeben
- [x] 2.2 Auto-Link in `get_current_user_with_memberships` an `email_verified` koppeln
- [x] 2.3 Keycloak-Provisioner bindet nur bei `emailVerified=true`, sonst Status `EXISTING_UNVERIFIED[_INVITED]` ohne `user_sub`

## 3. Dokumentation

- [x] 3.1 `docs/approval-workflow.md`: IdP-Anforderung `email_verified`, Hinweise fuer Keycloak/Authentik, neue Status
