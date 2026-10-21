# External ICS Proxy and Telemetry Secret Redaction

## Known boundary

Export subscription URLs have the form `/api/v1/export/<token>/calendar.ics`; the path segment is a bearer secret. The backend and bundled frontend nginx already redact this path. Section 1.1a of `docs/operations/production-runbook.md` warns that an external TLS proxy is independent and may still capture the secret.

## Production controls

At the external proxy, choose one of the following *per deployed product and version*, not a generic unverified switch: suppress access logs for this path or log a rewrite to a literal stable path such as `/api/v1/export/[REDACTED]/calendar.ics`. Test the *logged value*, not just the HTTP target. For nginx use a map from the raw request target into a sanitized access-log variable; never log `$request` or an untouched `$request_uri` for that location. For Caddy configure a compatible per-path suppression/redaction policy and verify it in the concrete deployed build. For Traefik note that request-path redaction support depends on middleware/provider and version; `accessLog.filters` is primarily filtering, not a guarantee that arbitrary URL substrings are rewritten. Do not assert that a field-drop feature hides a token if an unredacted path remains in another field. If no robust redaction is possible, disable access logging for the sensitive path.

Also inspect gateway logs, WAF, ingress, request tracing, APM spans, URL query/path tags, exporters and central log aggregation. Retain request method, response status and an opaque static route label rather than bearer material. Ensure application diagnostics never print candidate request URLs during verification.

## Canary and historical remediation

Issue a temporary test feed credential in the operator environment; do not echo it in shell output, tickets or artifacts. Fetch the feed over the public TLS ingress, then search all relevant proxy and telemetry stores for the exact secret using an isolated local check that reports only presence/absence. Confirm that the ordinary route diagnostics still operate.

Audit retention policies and access ACLs for previously stored secret-bearing URLs. Revoke/reissue potentially exposed subscriptions through the application's normal credential rotation path; record affected scope, completion and verified retention outcome without storing the secret itself. Destroy canary credentials after the exercise. If central logs are inaccessible, document that verification is incomplete and leave the issue open.

## Evidence and release gate

Extend the runbook with product-specific configuration decision records, operator/date, proxy version, canary pass/fail, named telemetry stores checked, retention status, number of rotated tokens and follow-up owner. A GitHub change can deliver documentation and a safe local checklist but cannot complete live-environment sign-off. Do not close issue #629 until operators confirm the external changes and canary pass.
