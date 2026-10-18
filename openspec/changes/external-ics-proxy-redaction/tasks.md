## 1. Document secure proxy choices
- [ ] 1.1 Add external Traefik/nginx/Caddy logging options with version checks and fail-safe suppression.
- [ ] 1.2 Document APM, tracing and central log path-redaction checks.
- [ ] 1.3 Add secret-safe canary and retention/rotation evidence template to the production runbook.

## 2. Live operational work (requires operator access)
- [ ] 2.1 Inspect actual external proxy configuration and apply verified redaction/suppression.
- [ ] 2.2 Check telemetry and historical log stores; revoke/reissue exposed credentials.
- [ ] 2.3 Perform end-to-end canary and record sign-off without exposing tokens.

## 3. Closure
- [ ] 3.1 Review runbook changes and CI, then check live evidence before closing issue #629.
