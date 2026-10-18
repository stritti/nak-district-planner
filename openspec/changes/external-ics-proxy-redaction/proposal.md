## Why

ICS bearer tokens are embedded in export URLs. Application and frontend nginx redact them, but an independently operated external TLS proxy and historic centralized logs may still retain full URLs. Issue #629 is an operational security gap outside this repository.

## What changes

- A production-runbook procedure covering Traefik, nginx and Caddy external proxy logging, telemetry labels and traces.
- A secret-safe canary verification that inspects every relevant log/trace path without disclosing the test token in the evidence record.
- An incident response workflow for retention, exposure assessment, revocation and reissue of leaked tokens.
- A documented operator sign-off gate. Repository CI can validate instructions, but cannot claim the deployed third-party proxy is secure.

## Non-goals

- Access or change an external TLS proxy without its actual configuration and operator permission.
- Treat redaction of application/nginx logs as sufficient proof for the external proxy.
- Include valid bearer tokens in issue comments, CI artifacts or source.

Issue: https://github.com/stritti/nak-district-planner/issues/629
