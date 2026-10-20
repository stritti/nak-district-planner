## Why

The SMTP adapter requires a verified STARTTLS connection before authenticating, but previous tests mock `smtplib` and do not exercise the real socket/TLS protocol. Issue #627 requires server-level verification and a release smoke procedure.

## What changes

- A local ephemeral SMTP server supporting STARTTLS with a test CA/certificate, with complete positive and negative cases.
- Assert actual command sequencing over the wire: LOGIN/AUTH never precedes successful TLS negotiation and certificate/hostname verification.
- A non-destructive staging smoke procedure against the configured real relay and clear runbook verification criteria.

## Non-goals

- Send mail to real recipients during CI.
- Embed SMTP credentials, CA private keys or production relay addresses in source.
- Disable certificate or hostname validation to make tests pass.

Issue: <https://github.com/stritti/nak-district-planner/issues/627>
